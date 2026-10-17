@echo off
setlocal enabledelayedexpansion
title Atualizacao da Base de Dados Eleitoral (Territorio Nacional)

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ===============================================================================
    echo [ERRO CRITICO] O Python nao foi encontrado no sistema ou nao esta no PATH!
    echo ===============================================================================
    echo Esta aplicacao requer Python 3.10 ou superior para executar o pipeline.
    echo ===============================================================================
    pause
    exit /b 1
)

cd /d "%~dp0\.."

echo ===============================================================================
echo            ATUALIZACAO E CONSOLIDACAO DE DADOS - ELEICOES 2026
echo            Abrangencia Mandatoria: Territorio Nacional (27 UFs)
echo ===============================================================================
echo.

python -u -m pipeline --forcar %*

set EXIT_CODE=%ERRORLEVEL%
if %EXIT_CODE% NEQ 0 (
    echo.
    echo [!] O processo de atualizacao foi encerrado ou falhou com codigo: %EXIT_CODE%
)

echo.
pause
exit /b %EXIT_CODE%
