# Política de Segurança - DevJourney

## Reportando Vulnerabilidades

Se você descobrir uma vulnerabilidade de segurança, por favor reporte de forma responsável:

1. **NÃO** abra um issue público no GitHub
2. Envie um email para os mantenedores com detalhes da vulnerabilidade
3. Inclua passos para reproduzir o problema
4. Aguarde um tempo razoável para uma correção antes da divulgação pública

## Medidas de Segurança Implementadas

### Autenticação
- Senhas hasheadas com Argon2id (memory-hard, com salt)
- Hashes SHA-256 legados são migrados automaticamente para Argon2 no login
- Tokens de sessão: 256-bit aleatório, armazenados em cookies HttpOnly/Secure/SameSite=Lax
- Sessões expiram após 24 horas
- Sessões expiradas são limpas no startup e a cada hora

### Autorização
- Todos os endpoints de modificação de dados requerem autenticação
- Todas as queries são filtradas por `user_id` para prevenir IDOR
- Tokens de sessão são validados em cada requisição

### Headers de Segurança HTTP
- `Content-Security-Policy`: restringe fontes de script/style/connect/frame
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Cross-Origin-Opener-Policy: same-origin`
- `Cross-Origin-Resource-Policy: same-origin`
- `Strict-Transport-Security` (apenas em produção): max-age=31536000; includeSubDomains; preload

### Proteção CSRF
- Middleware CSRF ativo que bloqueia requisições sem token válido
- Tokens gerados via `secrets.token_hex(32)`
- Validação via cookie, header X-CSRF-Token, ou campo de formulário
- Paths isentos: `/timer/ping`, `/health`, `/timer/save-state`, `/timer/clear-state`, `/timer/get-state`

### Rate Limiting
- Login: 10 tentativas por 15 minutos por IP
- Registro: 5 tentativas por hora por IP
- Geral: 120 requisições por minuto por IP

### Validação de Entrada
- Username: validado via regex (3-30 chars, alfanumérico + underscore)
- Email: validado via regex
- Senha: mínimo 6 caracteres
- Uploads de arquivo: máximo 1 MB, máximo 500 linhas para importações
- Inputs numéricos: verificados com limites
- Campos enum: validados com whitelist

### Banco de Dados
- SQLAlchemy ORM (queries parametrizadas)
- Foreign keys com CASCADE/SET NULL
- Constraints de unicidade em campos críticos
- Usuário do banco deve ter permissões de mínimo necessário

### Segurança de Cookies
- `HttpOnly`: impede acesso via JavaScript
- `Secure`: apenas HTTPS (em produção)
- `SameSite=Lax`: proteção CSRF para a maioria dos ataques
- `Max-Age`: 86400 segundos (24 horas)

### Rate Limiting
- Login: 10 tentativas por 15 minutos por IP
- Registro: 5 tentativas por hora por IP
- Geral: 120 requisições por minuto por IP

### Segurança do Banco de Dados
- Queries parametrizadas via SQLAlchemy ORM
- Foreign keys com CASCADE/SET NULL
- Constraints de unicidade em campos críticos
- Usuário do banco deve ter permissões de mínimo necessário

### Validação de SQL
- Validação de nomes de tabelas e colunas contra lista permitida
- Validação de tipos de colunas contra lista permitida
- Verificação de identificadores válidos

## Variáveis de Ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SECRET_KEY` | Sim (produção) | Chave secreta aleatória para assinatura de sessões (mínimo 32 bytes hex) |
| `DATABASE_URL` | Sim (produção) | String de conexão PostgreSQL |
| `PORT` | Não | Porta do servidor (padrão: 8000) |
| `RENDER` | Automático | Definido pela plataforma Render.com |

**NUNCA versione arquivos `.env`.**

## Checklist de Produção

- [ ] Configure `SECRET_KEY` forte (gere com `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Configure `DATABASE_URL` para PostgreSQL
- [ ] Habilite HTTPS (via proxy reverso ou plataforma)
- [ ] Desabilite modo debug
- [ ] Remova endpoints `/docs` e `/redoc` (desabilitados automaticamente em produção)
- [ ] Configure políticas CORS seguras se necessário
- [ ] Configure backup do banco de dados
- [] Monitore logs para atividades suspeitas

## Desenvolvimento

- SQLite usado para desenvolvimento local (dados efêmeros)
- Endpoints de debug disponíveis em `/docs` e `/redoc`
- Rate limits também se aplicam em desenvolvimento

## Dependências

Audite dependências regularmente:
```bash
pip-audit
# ou
safety check
```

## Limitações Conhecidas

- Sem bloqueio de conta após senhas incorretas (rate limiting mitiga)
- Sem verificação de email no registro
- Sem funcionalidade de redefinição de senha
- Sem 2FA/MFA
- Sem log de auditoria de ações do usuário
- Proteção CSRF depende de cookies SameSite (não usa tokens CSRF tradicionais)
- CSP usa `'unsafe-inline'` para scripts (necessário para templates Jinja2 com JavaScript inline)

## Status das Correções

| Data | Correção | Status |
|------|----------|--------|
| 2026-09-05 | CSRF middleware agora bloqueia requisições | ✅ |
| 2026-09-05 | IS_PRODUCTION importado de settings centralizado | ✅ |
| 2026-09-05 | Erros detalhados não expostos em desenvolvimento | ✅ |
| 2026-09-05 | Screenshot pessoal removido do repositório | ✅ |
| 2026-09-05 | .gitignore atualizado com entradas faltantes | ✅ |
| 2026-09-05 | Schemas não utilizados removidos | ✅ |
| 2026-09-05 | Migration órfã removida | ✅ |
| 2026-09-05 | initialize_default_achievements() agora cria conquistas padrão | ✅ |
| 2026-09-05 | docker-compose.yml exige senhas configuradas | ✅ |
| 2026-09-05 | .env.example atualizado com instruções claras | ✅ |
| 2026-09-05 | requirements-dev.txt criado | ✅ |
| 2026-09-05 | datetime.now() com timezone UTC nos models | ✅ |
| 2026-09-05 | Validação de SQL em _add_missing_columns | ✅ |