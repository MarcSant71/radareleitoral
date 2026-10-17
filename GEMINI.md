# Diretrizes do Projeto Eleições 2026

## 1. Fluxo Obrigatório de Homologação e Deploy (Local-First)

> [!IMPORTANT]
> **PROIBIDO FAZER DEPLOY DIRETO NA VPS SEM APROVAÇÃO PRÉVIA.**
> Toda e qualquer modificação na plataforma deve passar pelo ciclo de homologação local antes de ser promovida para produção.

### Ciclo de Desenvolvimento:
1. **Desenvolvimento Local:**
   - Todas as alterações (layout, CSS, textos, metodologia, novas análises ou correções de bugs) são feitas exclusivamente no ambiente local.
2. **Homologação pelo Usuário:**
   - O usuário valida e testa a aplicação localmente em `http://localhost:8501` através do script `scripts\rodarlocal.cmd`.
   - O Streamlit recarrega automaticamente as mudanças (*Hot Reload / Rerun*).
   - Enquanto o usuário não der o sinal verde explícito, nenhum arquivo é enviado para o servidor de produção (VPS Hetzner) e nenhum commit de release é gerado.
   - **Gatilho de Autorização Automática (`aprovadopd`):** A palavra-chave **`aprovadopd`** enviada pelo usuário é a autorização formal e definitiva para executar o ciclo completo de commit e deploy em produção.
3. **Versionamento Semântico (SemVer 2.0.0):**
   - **PATCH (`x.y.Z`):** Correções de bugs, ajustes visuais, CSS, polimento de contrastes e manutenção.
   - **MINOR (`x.Y.z`):** Novas funcionalidades retrocompatíveis, novas telas, novos filtros ou grandes marcos consolidados de produto.
   - **MAJOR (`X.y.z`):** Mudanças estruturais que quebrem contratos ou bancos de dados.
4. **Deploy Único em Produção (Disparado por `aprovadopd` ou OK explícito):**
   - Ao receber `aprovadopd`:
     1. Garantir sincronização de versionamento e changelog (`CHANGELOG.md`, `web/version.json`, `web/modulos/governanca.py`, `README.md`).
     2. Executar `git add -A` e `git commit -m "feat/fix/refactor: ... [vX.Y.Z]"`.
     3. Executar `git push origin main`.
     4. Executar deploy para a VPS Hetzner via script oficial: `powershell -ExecutionPolicy Bypass -File scripts\subirproducao.ps1`.
     5. Validar health check `200 OK` na URL oficial (`https://eleicao.dominiodigital.dev.br`).
5. **OpSec em Changelogs e Páginas Públicas:**
   - NUNCA divulgar detalhes técnicos de infraestrutura, portas internas, configurações de firewall ou dados sensíveis em changelogs públicos ou rodapés.

## 2. Isolamento de Rede e Contêineres (Docker)
- **Armadilha do Docker Bypass:** O Docker insere regras no `iptables` que contornam o firewall UFW do Linux. Portanto:
  - **JAMAIS expor portas de aplicações internas** (Streamlit 8501, APIs, etc.) diretamente no host (`0.0.0.0:porta`).
  - As aplicações devem rodar **estritamente em redes internas do Docker** (`networks:`), comunicando-se apenas com o Proxy Reverso (Caddy).
  - Apenas as portas `80` (HTTP) e `443` (HTTPS) do Caddy devem ser publicadas externamente.

## 3. Proxy Reverso (Caddy) & Cabeçalhos de Segurança
- **Ocultação de Topologia:** Sempre remover cabeçalhos que revelem tecnologia ou versões internas (`Server`, `Via`).
- **Security Headers Obrigatórios (OWASP):**
  - `X-Frame-Options: SAMEORIGIN` (bloqueia Clickjacking).
  - `X-Content-Type-Options: nosniff`.
  - `Referrer-Policy: strict-origin-when-cross-origin`.
  - `Permissions-Policy: geolocation=(), microphone=(), camera=()`.
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS estrito).
- **Proteção do IP de Origem:** Requisições diretas por IP na porta 80 devem SEMPRE redirecionar (301) para o domínio oficial HTTPS (`https://eleicao2026.dominiodigital.dev.br`), impedindo que scanners (Shodan, Censys) contornem o Cloudflare.

## 4. Segurança de Borda (Cloudflare / WAF)
- **HSTS Ativo:** Forçar HTTPS na borda da CDN.
- **Rate Limiting no WAF:** Regra ativa em `/_stcore/` para mitigar abusos de WebSocket e DoS.

## 5. Blindagem do Sistema Operacional (VPS Hetzner)
- **SSH Estrito:** `PasswordAuthentication no` (permitir exclusivamente chaves criptográficas SSH ED25519).
- **Defesa Ativa (Fail2ban):** `fail2ban` ativo monitorando o `sshd` para banir tentativas de força bruta.
- **Higiene Operacional:** Limpeza periódica de contêineres órfãos.

## 6. Ambiente Operacional
- O sistema operacional local é **Windows**.
- Utilizar exclusivamente comandos nativos do **PowerShell** (ex: `Select-String`, `Get-Content`, `scp.exe`, `ssh.exe`).
- Não utilizar comandos de Linux no shell local.

## 7. Playbook Operacional de Referência
- Para arquitetura de referência, modelos de configuração (`Caddyfile`, `docker-compose.yml`), comandos de auditoria e automação de deploy, consulte o playbook padrão em [DEPLOY-VPS.md](file:///W:/OneDrive/Projetos/Pessoal/DEPLOY-VPS.md).
