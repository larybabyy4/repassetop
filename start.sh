#!/data/data/com.termux/files/usr/bin/bash

# Atualiza o pip
pip install --upgrade pip

# Instala as dependências
pip install -r requirements.txt

# Inicia o bot
python bot.py