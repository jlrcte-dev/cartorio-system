# Como rodar

## Pré-requisitos

- **Python 3.12.x** (obrigatório). O `pyproject.toml` rejeita 3.13+.
- `pip` (ou `uv`).
- Em Windows, use Git Bash ou PowerShell. Este guia mostra os dois.

Verifique a versão:

```bash
python --version
# Python 3.12.x
```

## 1. Setup inicial (uma vez)

### Bash / Git Bash / Linux / macOS

```bash
# Criar e ativar venv
python -m venv .venv
source .venv/bin/activate

# Instalar dependências (produção + dev)
pip install -e ".[dev]"

# Configurar variáveis de ambiente
cp .env.example .env
```

### PowerShell (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

## 2. Banco de dados

Aplicar todas as migrations:

```bash
alembic upgrade head
```

Isso cria/atualiza `cartorio.db` (SQLite, default). O esquema é gerenciado
**exclusivamente** pelo Alembic — a aplicação não cria tabelas no startup.

Comandos úteis:

```bash
alembic current              # revisão atual
alembic history              # histórico
alembic downgrade -1         # reverter última migration
alembic downgrade base       # reverter tudo
alembic upgrade head         # aplicar tudo

# Após alterar models, gerar nova migration:
alembic revision --autogenerate -m "descrição da mudança"
```

## 3. Rodar o servidor

```bash
uvicorn app.main:app --reload
```

- API: <http://localhost:8000>
- Documentação interativa (Swagger UI): <http://localhost:8000/docs>
- Healthcheck: <http://localhost:8000/api/v1/health>

## 4. Rodar testes

```bash
# Todos os testes
pytest tests/ -v

# Apenas finance
pytest tests/test_finance_entries.py -v

# Apenas isolamento
pytest tests/test_isolation.py -v
```

## 5. Lint e formatação

```bash
ruff check .            # estática
ruff format --check .   # checagem de formatação
ruff format .           # aplica formatação
```

Pyproject já configura: `target-version = "py312"`, `line-length = 100`,
seleções `E,F,I,UP,B,SIM,ANN`, ignores específicos para `tests/*` e
`alembic/versions/*`.

## 6. Bloco completo de validação

Use antes de commit/push para garantir que tudo está saudável:

```bash
# 1. Lint
ruff check .
ruff format --check .

# 2. Testes
pytest tests/ -v

# 3. Round-trip de migrations
rm -f cartorio.db
alembic upgrade head
alembic downgrade base
alembic upgrade head

# 4. Isolamento de DB
rm -f cartorio.db
pytest tests/ -v
test ! -f cartorio.db && echo "OK: testes não tocaram cartorio.db"
```

Saída esperada (resumo):

```
ruff check .             → All checks passed!
ruff format --check .    → 36+ files already formatted
pytest tests/ -v         → 48 passed
alembic upgrade head     → ok
test ! -f cartorio.db    → OK: testes não tocaram cartorio.db
```

## 7. Variáveis de ambiente (`.env`)

| Variável        | Default                        | Descrição                          |
|-----------------|--------------------------------|------------------------------------|
| `APP_NAME`      | `Sistema do Cartório`          | Nome exibido em `/health`          |
| `APP_VERSION`   | `0.1.0`                        | Versão do app                      |
| `DEBUG`         | `false`                        | Modo debug (echo SQL etc.)         |
| `LOG_LEVEL`     | `INFO`                         | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `DATABASE_URL`  | `sqlite:///./cartorio.db`      | URL do banco                       |
| `API_PREFIX`    | `/api/v1`                      | Prefixo das rotas                  |

## 8. Solução de problemas

### `pytest` cria `cartorio.db`
Não deveria mais. Se acontecer, verifique se algum código voltou a chamar
`Base.metadata.create_all` no lifespan ou no nível de módulo do app. O
teste `test_lifespan_does_not_touch_production_db` em
`tests/test_isolation.py` deveria capturar isso.

### `alembic` falha em "Can't locate timezone: UTC"
`alembic.ini` não declara `timezone` (Windows costuma falhar sem o pacote
`tzdata`). Se voltar, remova qualquer linha `timezone = ...` de
`alembic.ini`.

### Erro de Pydantic com `date | None`
Não use `from __future__ import annotations` em `schemas.py`. O nome do
campo `date` sombreia o tipo. A solução é `import datetime as _dt` e usar
`_dt.date` nos type hints.

### `pip install -e ".[dev]"` falha com Python 3.13
O projeto está pinado em `>=3.12,<3.13`. Use Python 3.12 (o `.python-version`
direciona pyenv/mise para a versão correta).
