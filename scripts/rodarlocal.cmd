@echo off
title Radar Eleitoral - Inteligencia de Dados e Auditoria
cd /d "%~dp0\.."

echo ===============================================================================
echo            RADAR ELEITORAL - AUDITORIA E INTELIGENCIA DE DADOS
echo ===============================================================================
echo Banco de Dados: db\eleicoes.db
echo Abrindo navegador em http://localhost:8501 ...
echo ===============================================================================
echo.

start "" http://localhost:8501
python -m streamlit run web\app.py

pause
