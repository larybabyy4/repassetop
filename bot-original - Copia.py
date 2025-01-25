import json
import asyncio
import sys
import os
import tempfile
import atexit
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Arquivo de lock para garantir instância única
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'telegram_bot.lock')

def check_single_instance():
    """Verifica se já existe uma instância do bot rodando"""
    try:
        if os.path.exists(LOCK_FILE):
            # Verifica se o processo ainda está rodando
            with open(LOCK_FILE, 'r') as f:
                pid = int(f.read().strip())
                try:
                    # Tenta enviar sinal 0 para verificar se o processo existe
                    os.kill(pid, 0)
                    print(f"\n❌ Erro: Bot já está rodando (PID: {pid})")
                    return False
                except OSError:
                    # Processo não existe mais, podemos continuar
                    pass
        
        # Cria arquivo de lock
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        # Registra função para remover arquivo de lock ao fechar
        atexit.register(lambda: os.remove(LOCK_FILE) if os.path.exists(LOCK_FILE) else None)
        return True
    except Exception as e:
        print(f"Erro ao verificar instância: {e}")
        return False

print("Verificando ambiente Python...")
print(f"Versão do Python: {sys.version}")

# Token do seu bot
TOKEN = '7501724321:AAHZBNO_kYpumT-3_RnOfFe1yq4DEySbFMw'

# ID do grupo/canal 'MIDIAS'
MIDIAS_CHAT_ID = -1002270265757

# Arquivo para salvar os IDs dos grupos/canais de destino
TARGET_GROUPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grupos.json')

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
• Delay entre envios: 50 segundos
• Status: Ativo ✅
• PID: {os.getpid()}
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

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lida com as mídias enviadas no grupo/canal principal."""
    try:
        if not update.message:
            return

        if update.message.chat_id == MIDIAS_CHAT_ID:
            target_groups = load_target_groups()
            print(f"📨 Nova mídia recebida. Enviando para {len(target_groups)} grupos...")

            caption = " https://t.me/DraLarissa_aBot Desbloqueie Videos Exclusivos."

            # Envio para todos os grupos com um pequeno delay entre as mensagens
            tasks = []
            for chat_id in target_groups.copy():
                try:
                    tasks.append(
                        context.bot.copy_message(
                            chat_id=chat_id,
                            from_chat_id=update.message.chat_id,
                            message_id=update.message.message_id,
                            caption=caption
                        )
                    )
                    print(f"✅ Mídia para: {chat_id}")
                except Exception as e:
                    print(f"❌ Erro ao enviar para {chat_id}: {e}")
                    if "Forbidden" in str(e):
                        target_groups.discard(chat_id)
                        save_target_groups(target_groups)
                        print(f"🗑️ Grupo {chat_id} removido por erro de permissão")

            # Aguarda todas as tarefas de envio serem completadas (enviando praticamente simultaneamente)
            if tasks:
                await asyncio.gather(*tasks)
            await asyncio.sleep(1)  # Pequeno delay entre o envio das mensagens de mídia para diferentes grupos
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

def main():
    try:
        # Verifica se já existe uma instância rodando
        if not check_single_instance():
            print("Bot já está em execução! Fechando...")
            input("\nPressione Enter para sair...")
            sys.exit(1)

        print("\nIniciando bot do Telegram...")
        print(f"Python: {sys.version}")
        print(f"Sistema: {sys.platform}")
        print(f"Diretório atual: {os.getcwd()}")
        print(f"PID: {os.getpid()}")
        
        application = Application.builder().token(TOKEN).build()

        print("\nRegistrando handlers...")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add", add_group))
        application.add_handler(CommandHandler("status", status))
        application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_media))
        application.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL, restrict_non_admin_messages))
        application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS | filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_welcome_farewell_messages))

        print("\n✨ Bot iniciado e pronto para uso!")
        print("📝 Use /start para ver os comandos disponíveis")
        
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"\n❌ Erro fatal ao iniciar o bot: {e}")
        input("\nPressione Enter para sair...")
        sys.exit(1)

if __name__ == '__main__':
    main()