# Diretrizes do Projeto Eleições 2026

## 1. Fluxo Obrigatório de Homologação e Deploy (Local-First)

> [!IMPORTANT]
> **PROIBIDO FAZER DEPLOY DIRETO NA VPS SEM APROVAÇÃO PRÉVIA.**
> Toda e qualquer modificação na plataforma deve passar pelo ciclo de homologação local antes de ser promovida para produção.

### Ciclo de Desenvolvimento:
1. **Desenvolvimento Local:**
   - Todas as alterações (layout, CSS, textos, metodologia, novas análises ou correções de bugs) são feitas exclusivamente no ambiente local.
2. **Homologação pelo Usuário:**
   - O usuário valida e testa a aplicação localmente em `http://localhost:8501` através do script `scripts\painel.cmd`.
   - O Streamlit recarrega automaticamente as mudanças (*Hot Reload / Rerun*).
   - Enquanto o usuário não der o sinal verde explícito (ex: *"OK", "pode subir", "aprovado"*), nenhum arquivo é enviado para o servidor de produção (VPS Hetzner) e nenhum commit de release é gerado.
3. **Versionamento Semântico (SemVer 2.0.0):**
   - **PATCH (`x.y.Z`):** Correções de bugs, ajustes visuais, CSS, polimento de contrastes e manutenção.
   - **MINOR (`x.Y.z`):** Novas funcionalidades retrocompatíveis, novas telas, novos filtros ou grandes marcos consolidados de produto.
   - **MAJOR (`X.y.z`):** Mudanças estruturais que quebrem contratos ou bancos de dados.
4. **Deploy Único em Produção:**
   - Com o OK do usuário:
     1. Atualizar versionamento e changelog em `web\painel.py` e `README.md`.
     2. Executar deploy limpo para a VPS (`2.29.110.124`) e reiniciar o container `eleicoes2026_painel`.
     3. Validar health check `200 OK`.
     4. Gerar commit único e push para `origin/main`.

## 2. Ambiente Operacional
- O sistema operacional local é **Windows**.
- Utilizar exclusivamente comandos nativos do **PowerShell** (ex: `Select-String`, `Get-Content`, `scp.exe`, `ssh.exe`).
- Não utilizar comandos de Linux no shell local.
