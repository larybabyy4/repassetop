# atualizado em 150525

import json
import asyncio
import sys
import os
import random
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

print("Verificando ambiente Python...")
print(f"Versão do Python: {sys.version}")

# Token do seu bot
TOKEN = '7501724321:AAHk6NlmQ95qPP4yQvLGnfwy0m3t0z4GS8U'

# ID do grupo/canal 'MIDIAS'
MIDIAS_CHAT_ID = -1002270265757

# Arquivo para salvar os IDs dos grupos/canais de destino
TARGET_GROUPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grupos.json')

# Fila para armazenar mídias a serem enviadas
message_queue = asyncio.Queue()

# Delay entre o envio de mídias diferentes (em segundos)
DELAY_BETWEEN_MEDIAS = 50  # 50 segundos

# Variável para armazenar o horário da última mídia processada
last_media_time = None

# Número máximo de envios simultâneos
MAX_CONCURRENT_SENDS = 25  # Ajuste conforme necessário, 25 é seguro para bots comuns

def load_captions():
    try:
        with open('captions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def load_target_groups():
    """Carrega os IDs dos grupos/canais de destino do arquivo JSON."""
    try:
        if os.path.exists(TARGET_GROUPS_FILE):
            with open(TARGET_GROUPS_FILE, 'r', encoding='utf-8') as file:
                return set(json.load(file))
        return set()
    except Exception as e:
        print(f"Erro ao carregar grupos: {e}")
        return set()

def save_target_groups(target_groups):
    """Salva os IDs dos grupos/canais de destino no arquivo JSON."""
    try:
        with open(TARGET_GROUPS_FILE, 'w', encoding='utf-8') as file:
            json.dump(list(target_groups), file)
    except Exception as e:
        print(f"Erro ao salvar grupos: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /start."""
    try:
        mensagem = """
🤖 *Bot de Encaminhamento*

Comandos disponíveis:
/start - Mostra esta mensagem
/add - Adiciona o grupo atual à lista
/status - Mostra estatísticas do bot

ℹ️ Para funcionar, o bot precisa:
1. Ser admin nos grupos
2. Ter permissão para enviar mensagens
"""
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    except Exception as e:
        print(f"Erro no comando start: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o status do bot."""
    try:
        grupos = load_target_groups()
        mensagem = f"""
📊 *Status do Bot*

• Grupos cadastrados: {len(grupos)}
• Delay entre mídias: {DELAY_BETWEEN_MEDIAS} segundos
• Status: Ativo ✅
"""
        await update.message.reply_text(mensagem, parse_mode='Markdown')
    except Exception as e:
        print(f"Erro no comando status: {e}")

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adiciona o grupo/canal atual à lista de destinos."""
    try:
        chat_id = update.message.chat_id
        print(f"Comando /add recebido no chat {chat_id}")

        if update.message.chat.type in ['group', 'supergroup', 'channel']:
            try:
                user_id = update.message.from_user.id
                admins = await context.bot.get_chat_administrators(chat_id)
                if user_id not in [admin.user.id for admin in admins]:
                    await update.message.reply_text('❌ Apenas administradores podem usar este comando!')
                    return

                target_groups = load_target_groups()
                if chat_id not in target_groups:
                    target_groups.add(chat_id)
                    save_target_groups(target_groups)
                    print(f"Chat {chat_id} adicionado à lista de destinos.")
                    await update.message.reply_text(f'✅ Grupo adicionado com sucesso!\nTotal de grupos: {len(target_groups)}')
                else:
                    await update.message.reply_text('⚠️ Este grupo já está na lista!')
            except Exception as e:
                print(f"Erro ao adicionar grupo: {e}")
                await update.message.reply_text('❌ Erro ao adicionar o grupo.')
        else:
            await update.message.reply_text('❌ Este comando só funciona em grupos!')
    except Exception as e:
        print(f"Erro geral no add_group: {e}")

async def send_and_pin(context, chat_id, from_chat_id, message_id, caption):
    try:
        sent_message = await context.bot.copy_message(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_id=message_id,
            caption=caption
        )
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=sent_message.message_id)
        print(f"✅ Mídia enviada e fixada para: {chat_id}")
    except Exception as e:
        print(f"❌ Erro ao enviar para {chat_id}: {e}")
        if "Forbidden" in str(e):
            return chat_id  # Para remoção posterior
    return None

async def process_queue(context: ContextTypes.DEFAULT_TYPE):
    """Processa a fila de mídias com delays baseados no horário de recebimento."""
    global last_media_time
    while True:
        try:
            if not message_queue.empty():
                # Verifica o tempo decorrido desde a última mídia
                if last_media_time is not None:
                    elapsed_time = time.time() - last_media_time
                    remaining_delay = max(0, DELAY_BETWEEN_MEDIAS - elapsed_time)
                    if remaining_delay > 0:
                        print(f"⏳ Aguardando {remaining_delay:.2f} segundos antes de enviar a próxima mídia...")
                        await asyncio.sleep(remaining_delay)

                # Atualiza o horário da última mídia
                last_media_time = time.time()

                from_chat_id, message_id = await message_queue.get()
                target_groups = load_target_groups()
                print(f"📨 Processando mídia {message_id} para {len(target_groups)} grupos...")

                # Envio em lotes para respeitar limites
                chat_ids = list(target_groups)
                to_remove = set()
                for i in range(0, len(chat_ids), MAX_CONCURRENT_SENDS):
                    batch = chat_ids[i:i+MAX_CONCURRENT_SENDS]
                    caption = random.choice(load_captions())
                    tasks = [
                        send_and_pin(context, chat_id, from_chat_id, message_id, caption)
                        for chat_id in batch
                    ]
                    results = await asyncio.gather(*tasks)
                    # Remove grupos com erro Forbidden
                    for res in results:
                        if res:
                            to_remove.add(res)
                    await asyncio.sleep(1.2)  # Pequeno delay entre lotes para evitar flood

                # Remove grupos bloqueados
                if to_remove:
                    target_groups -= to_remove
                    save_target_groups(target_groups)
                    print(f"🗑️ Grupos removidos por erro de permissão: {to_remove}")
            else:
                await asyncio.sleep(1)  # Espera 1 segundo se a fila estiver vazia
        except Exception as e:
            print(f"❌ Erro no processamento da fila: {e}")
            await asyncio.sleep(5)  # Espera 5 segundos antes de tentar novamente

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com as mídias enviadas no grupo/canal principal."""
    try:
        if not update.message:
            return

        if update.message.chat_id == MIDIAS_CHAT_ID:
            await message_queue.put((update.message.chat_id, update.message.message_id))
            print(f"📨 Nova mídia recebida. Adicionada à fila para envio.")
    except Exception as e:
        print(f"Erro geral no handle_media: {e}")

async def restrict_non_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restringe mensagens de não administradores em grupos."""
    try:
        if update.message and update.message.chat.type in ['group', 'supergroup']:
            admins = await context.bot.get_chat_administrators(update.message.chat_id)
            admin_ids = [admin.user.id for admin in admins]

            if update.message.from_user.id not in admin_ids:
                await update.message.delete()
                print(f"🗑️ Mensagem de não-admin apagada")
    except Exception as e:
        print(f"Erro ao verificar permissões: {e}")

async def delete_welcome_farewell_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apaga mensagens de entrada e saída de membros."""
    try:
        if update.message and (update.message.new_chat_members or update.message.left_chat_member):
            await update.message.delete()
            print("🗑️ Mensagem de entrada/saída apagada")
    except Exception as e:
        print(f"Erro ao apagar mensagem: {e}")

async def welcome_with_random_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia uma mídia aleatória do canal principal com caption aleatório e fixa a mensagem."""
    try:
        if update.message and update.message.new_chat_members:
            await update.message.delete()
            print("🗑️ Mensagem de entrada apagada")

            # Busca as últimas 100 mensagens do canal principal
            history = await context.bot.get_chat_history(MIDIAS_CHAT_ID, limit=100)
            midias = [msg for msg in history if msg.photo or msg.video]
            if not midias:
                sent = await context.bot.send_message(chat_id=update.message.chat_id, text="Bem-vindo! Aproveite o grupo.")
                await context.bot.pin_chat_message(chat_id=update.message.chat_id, message_id=sent.message_id)
                return

            msg = random.choice(midias)
            captions = load_captions()
            caption = random.choice(captions) if captions else ""

            sent = await context.bot.copy_message(
                chat_id=update.message.chat_id,
                from_chat_id=MIDIAS_CHAT_ID,
                message_id=msg.message_id,
                caption=caption
            )
            await context.bot.pin_chat_message(chat_id=update.message.chat_id, message_id=sent.message_id)
            print("🚀 Mídia de boas-vindas enviada e fixada")
    except Exception as e:
        print(f"Erro ao enviar mídia de boas-vindas: {e}")

def main():
    try:
        print("\nIniciando bot do Telegram...")
        print(f"Python: {sys.version}")
        print(f"Sistema: {sys.platform}")
        print(f"Diretório atual: {os.getcwd()}")

        application = Application.builder().token(TOKEN).build()

        print("\nRegistrando handlers...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add", add_group))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_media))
        application.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL, restrict_non_admin_messages))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_welcome_farewell_messages))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_with_random_media))

        # Inicia o processamento da fila
        loop = asyncio.get_event_loop()
        loop.create_task(process_queue(application))

        print("\n✨ Bot iniciado e pronto para uso!")
        print("📝 Use /start para ver os comandos disponíveis")

        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"\n❌ Erro fatal ao iniciar o bot: {e}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

if __name__ == '__main__':
    main()
