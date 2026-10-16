@echo off
setlocal enabledelayedexpansion
title Inicializacao da Base de Dados Eleitoral

REM 1. Validacao de presenca do Python no sistema
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ===============================================================================
    echo [ERRO CRITICO] O Python nao foi encontrado no sistema ou nao esta no PATH!
    echo ===============================================================================
    echo Esta aplicacao requer Python 3.10 ou superior para executar o pipeline.
    echo.
    echo Solucao:
    echo 1. Instale o Python pelo site oficial: https://www.python.org/downloads/
    echo 2. Marque a opcao "Add Python to PATH" durante a instalacao.
    echo ===============================================================================
    echo.
    pause
    exit /b 1
)

REM 2. Captura versao do Python para exibicao
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v

REM 3. Posiciona na raiz do projeto (um nivel acima da pasta scripts)
cd /d "%~dp0\.."

REM 4. Executa o orquestrador modular do pipeline repassando eventuais argumentos (%*)
echo [*] Ambiente detectado: %PYTHON_VERSION%
echo [*] Diretorio do projeto: %CD%
echo.

python -u -m pipeline %*

set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% NEQ 0 (
    echo.
    echo [!] O processo foi encerrado ou falhou com codigo de retorno: %EXIT_CODE%
)

echo.
pause
exit /b %EXIT_CODE%
