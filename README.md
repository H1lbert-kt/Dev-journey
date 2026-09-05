# DevJourney

Um sistema web pensado para quem acabou conseguiu o primeiro estágio como desenvolvedor e quer organizar e acompanhar sua evolução profissional e de estudos.

Resumindo: é um painel pessoal para você não se perder no caminho entre "eu sou estagiário" e "eu sou um dev que sabe o que está fazendo".

---

## O que isso aqui faz?

O DevJourney reúne várias ferramentas que ajudam no dia a dia de quem está começando:

- **Dashboard** – Visão geral do seu progresso, com resumo de estudos do dia, streak de consistência e recomendações do que fazer agora.

- **Roadmap de estudos** – Crie fases e metas para organizar o que você quer aprender. Pense em "fases" como grandes blocos (ex: "Fundamentos", "Frameworks", "Banco de Dados") e "metas" como tarefas dentro de cada fase.

- **Projetos** – Registre os projetos que você está criando ou quer criar. Anote tecnologias usadas, link do GitHub, status e notas.

- **Hábitos diários** – Acompanhe se você está mantendo os hábitos que se propôs (como "estudar 30 min por dia", "ler documentação", etc).

- **Calendário de estudos** – Visualize seus dias de estudo, streaks e consistência ao longo do tempo.

- **Timer de estudos** – Cronômetro para medir o tempo de estudo, com registro automático de sessões.

- **Flashcards com SRS** – Sistema de repetição espaçada para fixar conceitos. Suporta importação de arquivos texto e revisão inteligente.

- **Simulados** – Crie e faça simulados para testar seus conhecimentos.

- **Revisões** – Sistema de revisão periódica para não esquecer o que já estudou.

- **Disciplinas/Matérias** – Organize seus estudos por disciplinas, com metas e acompanamento individual.

- **Conquistas** – Sistema de achievements que gamifica seu progresso e mantém a motivação.

- **Estatísticas** – Gráficos e métricas sobre seu tempo de estudo, disciplinas mais estudadas, evolução ao longo do tempo.

- **Diário/Journal** – Espaço para anotar reflexões, dificuldades e aprendizados do dia.

- **Plano do dia** – Monte uma lista do que você quer fazer hoje e acompanhe o progresso.

- **Skills** – Registre e acompanhe as habilidades que está desenvolvendo.

- **Grade de horários** – Organize sua semana com horários de estudo.

---

## Como funciona na prática?

1. Você cria uma conta e faz login.
2. Escolhe seu "modo de estudo" (programação, concursos ou vestibulares) — o sistema adapta as funcionalidades ao modo escolhido.
3. Preenche o roadmap com suas fases e metas de estudo.
4. Usa o timer para registrar suas sessões de estudo.
5. Acompanha tudo no dashboard, que mostra seu progresso, streaks e o que fazer a seguir.
6. Usa flashcards e revisões para não esquecer o que já aprendeu.
7. Ganha conquistas ao completar metas e manter consistência.

---

## Stack do projeto

**Backend:**
- Python 3.11+
- FastAPI (framework web assíncrono)
- SQLAlchemy (ORM para banco de dados)
- Alembic (migrações do banco)
- SQLite (desenvolvimento local) / PostgreSQL (produção)

**Frontend:**
- HTML, CSS, JavaScript puro
- Jinja2 templates (server-side rendering)

**Infraestrutura:**
- Docker + Docker Compose
- Gunicorn + Uvicorn (servidor em produção)
- Sentry (monitoramento de erros, opcional)
- Telegram (notificações de erro, opcional)
- Render.com (deploy)

---

## Como rodar

### Opção 1: Docker (recomendado)

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/dev-journey.git
cd dev-journey
```

2. Copie o arquivo de exemplo de variáveis de ambiente:
```bash
cp .env.example .env
```

3. Edite o `.env` se quiser mudar alguma configuração (padrão já funciona para teste local).

4. Suba com Docker Compose:
```bash
docker-compose up --build
```

5. Acesse: `http://localhost:8001`

### Opção 2: Sem Docker

1. Clone e entre na pasta:
```bash
git clone https://github.com/seu-usuario/dev-journey.git
cd dev-journey
```

2. Crie um ambiente virtual e instale dependências:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o .env se necessário
```

4. Suba o servidor:
```bash
python main.py
```

5. Acesse: `http://localhost:8000`

---

## Estrutura do projeto

```
dev-journey/
├── app/
│   ├── config/          # Configurações e settings
│   ├── database/        # Conexão com o banco e configurações
│   ├── models/          # Modelos SQLAlchemy (tabelas do banco)
│   ├── repositories/    # Camada de acesso a dados
│   ├── routers/         # Rotas da aplicação (endpoints)
│   ├── schemas/         # Schemas Pydantic (validação)
│   ├── services/        # Lógica de negócio
│   ├── static/          # Arquivos estáticos (CSS, JS, imagens)
│   ├── templates/       # Templates HTML (Jinja2)
│   └── utils/           # Utilitários diversos
├── alembic/             # Migrações do banco de dados
├── tests/               # Testes automatizados
├── main.py              # Ponto de entrada da aplicação
├── docker-compose.yml   # Configuração do Docker
├── Dockerfile           # Imagem Docker
├── requirements.txt     # Dependências Python
└── .env.example         # Exemplo de variáveis de ambiente
```

---

## Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `SECRET_KEY` | Sim (produção) | Chave secreta para assinatura de sessões (mínimo 32 bytes hex) |
| `DATABASE_URL` | Sim (produção) | String de conexão com PostgreSQL |
| `POSTGRES_DB` | Não | Nome do banco PostgreSQL (padrão: devjourney) |
| `POSTGRES_USER` | Não | Usuário PostgreSQL (padrão: devjourney) |
| `POSTGRES_PASSWORD` | Não | Senha PostgreSQL |
| `APP_PORT` | Não | Porta da aplicação (padrão: 8000) |
| `SENTRY_DSN` | Não | DSN do Sentry para monitoramento de erros |
| `TELEGRAM_BOT_TOKEN` | Não | Token do bot Telegram para notificações |
| `TELEGRAM_CHAT_ID` | Não | ID do chat Telegram para notificações |
| `LOG_LEVEL` | Não | Nível de log (padrão: INFO) |

---

## Segurança

O projeto tem várias camadas de segurança:

- **Senhas** – Hasheadas com Argon2id (algoritmo memory-hard)
- **Sessões** – Tokens de 256-bit, armazenados em cookies HttpOnly/Secure/SameSite=Lax
- **Rate limiting** – Limite de tentativas de login (10/15min), registro (5/hora) e requisições gerais (120/min)
- **Headers HTTP** – CSP, X-Frame-Options, HSTS e outros headers de segurança
- **CSRF** – Proteção via SameSite cookies
- **Validação de entrada** – Username, email, senha e uploads validados
- **Banco de dados** – Queries parametrizadas via SQLAlchemy ORM

---

## Deploy

O projeto está configurado para deploy fácil:

- **Render.com** – Arquivo `render.yaml` incluído para deploy automático
- **Docker** – `docker-compose.yml` pronto para subir em qualquer ambiente
- **Procfile** – Para plataformas que usam Heroku-style

Para deploy no Render, basta conectar o repositório e ele detecta automaticamente a configuração.

---

## Desenvolvimento

Se quiser contribuir ou modificar:

1. Roda localmente com SQLite (já configurado por padrão)
2. Acesse `/docs` ou `/redoc` para ver a documentação da API (só em desenvolvimento)
3. Testes estão na pasta `tests/`
4. Migrações com Alembic: `alembic upgrade head`

---

## Licença

Esse é um projeto pessoal, mas se quiser usar como referência, fique à vontade.