@echo off
title Painel de Auditoria - Eleicoes 2026
cd /d "%~dp0\.."

echo ===============================================================================
echo            PAINEL INTERATIVO DE AUDITORIA ELEITORAL 2026
echo ===============================================================================
echo Banco de Dados: db\eleicoes2026.db (497.895 secoes)
echo Abrindo navegador em http://localhost:8501 ...
echo ===============================================================================
echo.

start "" http://localhost:8501
python -m streamlit run web\painel.py

pause
