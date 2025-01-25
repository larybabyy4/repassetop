import os
import asyncio
from telethon import TelegramClient
import logging
import uuid
import shutil
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Telegram Configuration
API_ID = "YOUR_API_ID"  # Replace with your API ID
API_HASH = "YOUR_API_HASH"  # Replace with your API Hash
PHONE_NUMBER = "YOUR_PHONE_NUMBER"  # Replace with your phone number

# Target chat IDs (can be channel, group, or user IDs)
DESTINATION_CHATS = [-1002462947693]  # Replace with your target chat IDs

# Custom caption for media
CAPTION_TEXT = """Linha 1
Linha 2"""

class TelegramMediaBot:
    def __init__(self):
        self.client = None
        self.media_queue = asyncio.Queue(maxsize=100)
        self.download_semaphore = asyncio.Semaphore(5)  # Limit concurrent downloads
        self.send_semaphore = asyncio.Semaphore(1)  # Rate limit sending
        self.processed_urls = set()
        
    async def initialize(self):
        """Initialize the Telegram client"""
        try:
            self.client = TelegramClient('session_name', API_ID, API_HASH)
            await self.client.start(phone=PHONE_NUMBER)
            logger.info("Telegram client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram client: {e}")
            raise

    async def download_with_gallery_dl(self, url, download_dir):
        """Download media using gallery-dl"""
        async with self.download_semaphore:
            try:
                process = await asyncio.create_subprocess_exec(
                    'gallery-dl',
                    '--destination', download_dir,
                    url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    logger.info(f"Successfully downloaded from URL: {url}")
                    return True
                else:
                    logger.error(f"Failed to download from URL: {url}\nError: {stderr.decode()}")
                    return False
            except Exception as e:
                logger.error(f"Error downloading with gallery-dl: {e}")
                return False

    async def process_with_ffmpeg(self, input_path, output_path):
        """Process media with ffmpeg to add caption"""
        try:
            command = [
                'ffmpeg', '-i', input_path,
                '-vf', f"drawtext=text='{CAPTION_TEXT}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
                '-y', output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully processed media with ffmpeg: {output_path}")
                return True
            else:
                logger.error(f"Failed to process with ffmpeg: {stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"Error processing with ffmpeg: {e}")
            return False

    def list_downloaded_files(self, directory):
        """List all files in directory and subdirectories"""
        file_paths = []
        for root, _, files in os.walk(directory):
            for file in files:
                file_paths.append(os.path.join(root, file))
        return file_paths

    async def send_media(self, chat_id, media_path):
        """Send media to a specific chat"""
        async with self.send_semaphore:
            try:
                entity = await self.client.get_entity(chat_id)
                await self.client.send_file(
                    entity,
                    media_path,
                    caption=CAPTION_TEXT
                )
                logger.info(f"Successfully sent media to chat {chat_id}: {media_path}")
                await asyncio.sleep(30)  # Rate limiting
                return True
            except Exception as e:
                logger.error(f"Error sending media to {chat_id}: {e}")
                return False

    async def process_url(self, url):
        """Process a single URL"""
        if url in self.processed_urls:
            logger.info(f"URL already processed: {url}")
            return

        try:
            # Create temporary directory for downloads
            download_dir = os.path.join(os.getcwd(), f"temp_{uuid.uuid4().hex}")
            os.makedirs(download_dir, exist_ok=True)
            logger.info(f"Created temporary directory: {download_dir}")

            # Download media
            if await self.download_with_gallery_dl(url, download_dir):
                # Get list of downloaded files
                files = self.list_downloaded_files(download_dir)
                
                for file_path in files:
                    # Create output path for processed file
                    output_path = os.path.join(
                        download_dir,
                        f"processed_{os.path.basename(file_path)}"
                    )
                    
                    # Process with ffmpeg
                    if await self.process_with_ffmpeg(file_path, output_path):
                        # Add to queue for sending
                        await self.media_queue.put((output_path, download_dir))
                    
                    # Remove original file
                    os.remove(file_path)
            
            # Add URL to processed set
            self.processed_urls.add(url)
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
        finally:
            # Cleanup will be done after sending

    async def monitor_links_file(self):
        """Monitor links.txt file for new URLs"""
        while True:
            try:
                if os.path.exists('links.txt'):
                    with open('links.txt', 'r') as f:
                        urls = [line.strip() for line in f.readlines() if line.strip()]
                        
                    for url in urls:
                        if url not in self.processed_urls:
                            await self.process_url(url)
                            
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring links file: {e}")
                await asyncio.sleep(5)

    async def media_sender(self):
        """Process media queue and send to all destination chats"""
        while True:
            try:
                media_path, download_dir = await self.media_queue.get()
                
                try:
                    for chat_id in DESTINATION_CHATS:
                        success = await self.send_media(chat_id, media_path)
                        if not success:
                            logger.error(f"Failed to send media to chat {chat_id}")
                finally:
                    # Cleanup
                    try:
                        os.remove(media_path)
                        if os.path.exists(download_dir) and not os.listdir(download_dir):
                            shutil.rmtree(download_dir)
                            logger.info(f"Cleaned up directory: {download_dir}")
                    except Exception as e:
                        logger.error(f"Error during cleanup: {e}")
                
                self.media_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in media sender: {e}")
                await asyncio.sleep(5)

    async def run(self):
        """Main run method"""
        await self.initialize()
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self.monitor_links_file()),
            asyncio.create_task(self.media_sender())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            for task in tasks:
                task.cancel()
            
            if self.client:
                await self.client.disconnect()

async def main():
    bot = TelegramMediaBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())