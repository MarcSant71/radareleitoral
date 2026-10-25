@echo off
setlocal enabledelayedexpansion
title Inicializacao da Base de Dados Eleitoral - Radar Eleitoral

REM ===============================================================================
REM 1. Validacao de presenca do Python no sistema
REM ===============================================================================
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

REM ===============================================================================
REM 2. Captura versao do Python e ambiente para exibicao
REM ===============================================================================
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v

REM ===============================================================================
REM 3. Posiciona na raiz do projeto (um nivel acima da pasta scripts)
REM ===============================================================================
cd /d "%~dp0\.."

echo ===============================================================================
echo            INICIALIZACAO DA BASE DE DADOS ELEITORAL - RADAR ELEITORAL
echo            Escopo: Territorio Nacional Completo (27 UFs)
echo            Destino dos Dados Brutos: dados_brutos\arquivos_urna\
echo ===============================================================================
echo [*] Ambiente detectado: %PYTHON_VERSION%
echo [*] Diretorio do projeto: %CD%
echo.

REM ===============================================================================
REM 4. Execucao do Pipeline de Dados
REM    - Verifica pacotes na CDN do TSE (baixa apenas arquivos novos/atualizados)
REM    - Salva os arquivos brutos em dados_brutos\arquivos_urna\
REM    - Audita logs, decodifica BUs e consolida bases SQLite e Parquet
REM ===============================================================================
python -u -m pipeline %*

set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% NEQ 0 (
    echo.
    echo ===============================================================================
    echo [!] O processo foi encerrado ou falhou com codigo de retorno: %EXIT_CODE%
    echo ===============================================================================
) else (
    echo.
    echo ===============================================================================
    echo [OK] BASE DE DADOS LOCAL INICIALIZADA COM SUCESSO!
    echo      - Dados brutos verificados/salvos em dados_brutos\arquivos_urna
    echo      - Bases SQLite e Parquet consolidadas localmente
    echo ===============================================================================
)

echo.
pause
exit /b %EXIT_CODE%
