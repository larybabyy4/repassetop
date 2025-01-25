import TelegramBot from 'node-telegram-bot-api';
import fs from 'fs/promises';

// Configurações do bot
const TOKEN = '7501724321:AAEO-j8G56NbKDt1hi9cCf89MFZd4R79cmQ';
const CANAL_PRINCIPAL = -1002380458312; // ID do canal principal
const ARQUIVO_GRUPOS = 'grupos_destino.json';
const DELAY_ENTRE_MENSAGENS = 50000; // 50 segundos entre cada envio

// Criação da instância do bot
const bot = new TelegramBot(TOKEN, { polling: true });

// Carrega a lista de grupos de destino
async function carregarGrupos() {
  try {
    const dados = await fs.readFile(ARQUIVO_GRUPOS, 'utf8');
    return new Set(JSON.parse(dados));
  } catch (error) {
    console.log('Arquivo de grupos não encontrado. Criando nova lista...');
    return new Set();
  }
}

// Salva a lista de grupos de destino
async function salvarGrupos(grupos) {
  try {
    await fs.writeFile(ARQUIVO_GRUPOS, JSON.stringify([...grupos]));
    console.log('Lista de grupos salva com sucesso!');
  } catch (error) {
    console.error('Erro ao salvar lista de grupos:', error);
  }
}

// Verifica se um usuário é administrador
async function verificarAdmin(chatId, userId) {
  try {
    const admins = await bot.getChatAdministrators(chatId);
    return admins.some(admin => admin.user.id === userId);
  } catch {
    return false;
  }
}

// Comando /start
bot.onText(/\/start/, async (msg) => {
  const mensagem = `
🤖 *Bot de Gerenciamento de Conteúdo*

Comandos disponíveis:
/start - Mostra esta mensagem
/add - Adiciona o grupo/canal atual à lista de destinos
/remove - Remove o grupo/canal da lista de destinos
/status - Mostra informações sobre o bot

⚠️ *Observação*: O bot precisa ser administrador em todos os grupos!
  `;

  await bot.sendMessage(msg.chat.id, mensagem, { parse_mode: 'Markdown' });
});

// Comando /add
bot.onText(/\/add/, async (msg) => {
  const chatId = msg.chat.id;

  if (!['group', 'supergroup', 'channel'].includes(msg.chat.type)) {
    await bot.sendMessage(chatId, '❌ Este comando só funciona em grupos ou canais!');
    return;
  }

  try {
    // Verifica se quem executou o comando é admin
    if (!await verificarAdmin(chatId, msg.from.id)) {
      await bot.sendMessage(chatId, '❌ Apenas administradores podem usar este comando!');
      return;
    }

    const grupos = await carregarGrupos();
    
    if (grupos.has(chatId)) {
      await bot.sendMessage(chatId, '⚠️ Este grupo/canal já está na lista de destinos!');
      return;
    }

    grupos.add(chatId);
    await salvarGrupos(grupos);
    await bot.sendMessage(chatId, `✅ Grupo/canal adicionado com sucesso!\nTotal de destinos: ${grupos.size}`);
    
  } catch (error) {
    console.error('Erro ao adicionar grupo:', error);
    await bot.sendMessage(chatId, '❌ Ocorreu um erro ao adicionar o grupo/canal.');
  }
});

// Comando /remove
bot.onText(/\/remove/, async (msg) => {
  const chatId = msg.chat.id;

  if (!['group', 'supergroup', 'channel'].includes(msg.chat.type)) {
    await bot.sendMessage(chatId, '❌ Este comando só funciona em grupos ou canais!');
    return;
  }

  try {
    // Verifica se quem executou o comando é admin
    if (!await verificarAdmin(chatId, msg.from.id)) {
      await bot.sendMessage(chatId, '❌ Apenas administradores podem usar este comando!');
      return;
    }

    const grupos = await carregarGrupos();
    
    if (!grupos.has(chatId)) {
      await bot.sendMessage(chatId, '⚠️ Este grupo/canal não está na lista de destinos!');
      return;
    }

    grupos.delete(chatId);
    await salvarGrupos(grupos);
    await bot.sendMessage(chatId, `✅ Grupo/canal removido com sucesso!\nTotal de destinos: ${grupos.size}`);
    
  } catch (error) {
    console.error('Erro ao remover grupo:', error);
    await bot.sendMessage(chatId, '❌ Ocorreu um erro ao remover o grupo/canal.');
  }
});

// Comando /status
bot.onText(/\/status/, async (msg) => {
  try {
    const grupos = await carregarGrupos();
    const mensagem = `
📊 *Status do Bot*

• Total de grupos/canais: ${grupos.size}
• Delay entre envios: ${DELAY_ENTRE_MENSAGENS/1000} segundos
• Bot ativo e funcionando normalmente
    `;
    
    await bot.sendMessage(msg.chat.id, mensagem, { parse_mode: 'Markdown' });
  } catch (error) {
    console.error('Erro ao mostrar status:', error);
    await bot.sendMessage(msg.chat.id, '❌ Erro ao obter status do bot.');
  }
});

// Gerenciador de mensagens
bot.on('message', async (msg) => {
  // Ignora comandos
  if (msg.text?.startsWith('/')) return;

  const chatId = msg.chat.id;

  // Se a mensagem vier do canal principal
  if (chatId === CANAL_PRINCIPAL) {
    try {
      const grupos = await carregarGrupos();
      console.log(`📨 Nova mídia recebida. Enviando para ${grupos.size} destinos...`);

      const legenda = '🔔 Fica de Fora Não! Acesse @DraLarissa_aBot - Se Grátis É Assim, Imagina Sendo VIP! 🌟';

      for (const grupoId of grupos) {
        try {
          await bot.copyMessage(grupoId, chatId, msg.message_id, {
            caption: legenda
          });
          console.log(`✅ Mídia enviada para: ${grupoId}`);
          
          // Aguarda o delay antes de enviar para o próximo grupo
          await new Promise(resolve => setTimeout(resolve, DELAY_ENTRE_MENSAGENS));
        } catch (error) {
          console.error(`❌ Erro ao enviar para ${grupoId}:`, error.message);
          
          // Se o erro for de permissão ou grupo não encontrado, remove o grupo da lista
          if (['ETELEGRAM: 403 Forbidden', 'ETELEGRAM: 400 Bad Request'].includes(error.message)) {
            grupos.delete(grupoId);
            await salvarGrupos(grupos);
            console.log(`🗑️ Grupo ${grupoId} removido da lista por erro de permissão/acesso`);
          }
        }
      }
    } catch (error) {
      console.error('Erro ao processar mensagem do canal principal:', error);
    }
    return;
  }

  // Gerencia mensagens em grupos
  if (['group', 'supergroup'].includes(msg.chat.type)) {
    try {
      // Se não for admin, apaga a mensagem
      if (!await verificarAdmin(chatId, msg.from.id)) {
        await bot.deleteMessage(chatId, msg.message_id);
        console.log(`🗑️ Mensagem de não-admin apagada em ${chatId}`);
      }
    } catch (error) {
      console.error('Erro ao gerenciar mensagem em grupo:', error);
    }
  }
});

// Gerencia mensagens de entrada/saída
bot.on('new_chat_members', async (msg) => {
  try {
    await bot.deleteMessage(msg.chat.id, msg.message_id);
    console.log(`🗑️ Mensagem de entrada apagada em ${msg.chat.id}`);
  } catch (error) {
    console.error('Erro ao apagar mensagem de entrada:', error);
  }
});

bot.on('left_chat_member', async (msg) => {
  try {
    await bot.deleteMessage(msg.chat.id, msg.message_id);
    console.log(`🗑️ Mensagem de saída apagada em ${msg.chat.id}`);
  } catch (error) {
    console.error('Erro ao apagar mensagem de saída:', error);
  }
});

// Tratamento de erros global
bot.on('polling_error', (error) => {
  console.error('Erro de polling:', error);
});

console.log('✨ Bot iniciado e pronto para uso!');
console.log('📝 Use /start para ver os comandos disponíveis.');