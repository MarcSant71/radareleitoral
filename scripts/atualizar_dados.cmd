@echo off
cls
setlocal enabledelayedexpansion
title Atualizacao da Base de Dados Eleitoral e Deploy em Producao

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
echo            ATUALIZACAO E CONSOLIDACAO DE DADOS - RADAR ELEITORAL
echo            Escopo: Territorio Nacional Completo (27 UFs)
echo            Destino dos Dados Brutos: dados_brutos\arquivos_urna\
echo ===============================================================================
echo [*] Ambiente detectado: %PYTHON_VERSION%
echo [*] Diretorio do projeto: %CD%
echo.

REM ===============================================================================
REM 4. Execucao do Pipeline de Dados (Download do que existe de novo e processamento)
REM    - Verifica pacotes na CDN do TSE (baixa apenas arquivos novos/incompletos)
REM    - Salva os arquivos brutos em dados_brutos\arquivos_urna\
REM    - Audita logs, decodifica BUs e consolida bases SQLite e Parquet
REM ===============================================================================
echo ===============================================================================
echo [*] ETAPA 1/2: Baixando novos dados e consolidando bases locais...
echo ===============================================================================
echo.

python -u -m pipeline update --forcar %*

set PIPELINE_EXIT=%ERRORLEVEL%
if %PIPELINE_EXIT% NEQ 0 (
    echo.
    echo ===============================================================================
    echo [!] FALHA NO PIPELINE: O processamento foi encerrado com codigo: %PIPELINE_EXIT%
    echo [!] O deploy para producao foi abortado por seguranca.
    echo ===============================================================================
    echo.
    pause
    exit /b %PIPELINE_EXIT%
)

REM ===============================================================================
REM 5. Verificacao Inteligente de Deploy:
REM    Se nenhuma UF foi atualizada no TSE e nenhum BU novo foi processado, dispensa deploy.
REM ===============================================================================
set FORCAR_DEPLOY=0
for %%a in (%*) do (
    if /i "%%a"=="--forcar-deploy" set FORCAR_DEPLOY=1
)

if not exist "db\.novos_dados_consolidados" (
    if !FORCAR_DEPLOY! EQU 0 (
        echo.
        echo ===============================================================================
        echo [i] Nenhuma novidade detectada na CDN do TSE.
        echo [i] Todas as secoes ja estao 100%% consolidadas e identicas a versao oficial.
        echo [i] O deploy para producao foi dispensado (nenhum dado novo a transmitir).
        echo ===============================================================================
        echo Dica: Para forcar o deploy na VPS mesmo sem alteracoes de dados, execute:
        echo      scripts\atualizar_dados.cmd --forcar-deploy
        echo ===============================================================================
        echo.
        pause
        exit /b 0
    ) else (
        echo [*] Parametro --forcar-deploy detectado. Prosseguindo com o envio para producao...
    )
)

REM ===============================================================================
REM 6. Upload dos Dados Consolidados para o Servidor de Producao (Hetzner VPS)
REM    - Empacota codigo, Parquets analiticos e banco SQLite (-IncludeDatabase)
REM    - Envia via SCP e recria os conteineres Docker na nuvem
REM ===============================================================================
echo.
echo ===============================================================================
echo [*] ETAPA 2/2: Enviando bases atualizadas para producao (Hetzner VPS)...
echo ===============================================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0\subirproducao.ps1" -IncludeDatabase

set DEPLOY_EXIT=%ERRORLEVEL%
if %DEPLOY_EXIT% NEQ 0 (
    echo.
    echo ===============================================================================
    echo [!] AVISO: O pipeline local concluiu com sucesso, mas o deploy falhou (codigo: %DEPLOY_EXIT%).
    echo [!] Verifique a conectividade SSH com a VPS e tente novamente via scripts\subirproducao.ps1.
    echo ===============================================================================
    echo.
    pause
    exit /b %DEPLOY_EXIT%
)

if exist "db\.novos_dados_consolidados" del "db\.novos_dados_consolidados" >nul 2>nul

echo.
echo ===============================================================================
echo [OK] PROCESSO COMPLETO FINALIZADO COM SUCESSO!
echo      - Dados brutos verificados/baixados em dados_brutos\arquivos_urna
echo      - Bases SQLite e Parquet consolidadas localmente
echo      - Producao atualizada em: https://radareleitoral.dominiodigital.dev.br
echo ===============================================================================
echo.
pause
exit /b 0
