@echo off
title Atualizar Dados - Eleicoes 2026
cd /d "%~dp0\.."
if exist "W:\Apps\Eleicoes2026" set DADOS_DIR=W:\Apps\Eleicoes2026

echo ===============================================================================
echo            ATUALIZACAO E CONSOLIDACAO DE DADOS - ELEICOES 2026
echo ===============================================================================
echo.
echo [1/2] Verificando pacotes na CDN do TSE...
echo       (Arquivos ja baixados e integros sao pulados automaticamente)
echo ===============================================================================
echo.

python -u pipeline\baixar_pacote.py --todas

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo AVISO: Falha de rede ao checar algum estado. Prosseguindo com dados locais...
)

echo.
echo ===============================================================================
echo [2/3] Auditando e consolidando secoes no SQLite (db\eleicoes2026.db)...
echo       (Secoes ja consolidadas sao puladas em fracao de segundo)
echo ===============================================================================
echo.

python -u pipeline\auditar.py --threads 16

echo.
echo ===============================================================================
echo [3/4] Consolidando resultados dos Boletins de Urna (BU)...
echo       (Apuração por candidato e partido extraída dos pacotes oficiais)
echo ===============================================================================
echo.

python -u pipeline\consolidar_bu.py --threads 16

echo.
echo ===============================================================================
echo [4/4] Consolidando dados de abstenção e comparecimento (TSE)...
echo ===============================================================================
echo.

if exist "dados_brutos\detalhe_votacao_secao_2022.zip" (
    python -u pipeline\abstencao\consolidar_abstencao.py --arquivo dados_brutos\detalhe_votacao_secao_2022.zip
)

echo.
echo ===============================================================================
echo CONCLUIDO COM SUCESSO!
echo Todos os dados estao atualizados e prontos para visualizacao no painel.
echo ===============================================================================
echo.
pause
