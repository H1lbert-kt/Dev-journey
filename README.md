# DevJourney

Sistema web para acompanhar sua evolucao apos conseguir o primeiro estagio como desenvolvedor.

## Tecnologias

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, Alembic
- **Frontend:** HTML, CSS, JavaScript, Jinja2 Templates

## Funcionalidades

- Dashboard com progresso geral
- Roadmap de estudos com fases e metas
- Sistema de projetos
- Habitos diarios
- Calendario de estudos
- Estatisticas
- Sistema de conquistas

## Como Executar

1. Criar banco de dados PostgreSQL:
```sql
CREATE DATABASE devjourney;
```

2. Configurar variaveis de ambiente:
```bash
cp .env.example .env
# Editar .env com suas credenciais
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Criar tabelas:
```bash
python -c "from app.database.connection import engine, Base; Base.metadata.create_all(bind=engine)"
```

5. Executar o servidor:
```bash
python main.py
```

6. Acesse: http://localhost:8000

## Estrutura do Projeto

```
dev-journey/
├── app/
│   ├── config/
│   ├── database/
│   ├── models/
│   ├── repositories/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
├── alembic/
├── alembic.ini
├── main.py
└── requirements.txt
```
