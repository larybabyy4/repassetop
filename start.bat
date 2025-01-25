@echo off
chcp 65001 > nul
title Bot do Telegram

echo Verificando Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Erro: Python nao encontrado!
    echo Por favor, instale o Python 3.8 ou superior do site oficial:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANTE: Durante a instalacao, marque a opcao "Add Python to PATH"
    pause
    exit /b 1
)

echo.
echo Instalando/Atualizando pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao atualizar pip
    pause
    exit /b 1
)

echo.
echo Instalando dependencias...
pip install -r "%~dp0requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao instalar dependencias
    pause
    exit /b 1
)

echo.
echo Iniciando o bot...
python "%~dp0bot.py"

pause