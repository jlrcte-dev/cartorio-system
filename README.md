# Sistema do Cartório

Backend independente do **Cartório Costa Teixeira**. O MVP atual está focado
em apoio direto ao gestor da serventia: registro de receitas, despesas,
repasses e ajustes, com regras de domínio suficientes para fundamentar
fechamento mensal, relatórios obrigatórios e exports para a contabilidade
nas etapas seguintes.

O sistema **não substitui** o Engegraph (ERP cartorial existente) e **não**
compartilha código, banco ou credenciais com outros projetos. Integrações
futuras ocorrem por exports estruturados.

## Documentação

Documentação técnica detalhada em [`docs/`](docs/):

- [`docs/architecture.md`](docs/architecture.md) — visão geral, stack,
  layout e princípios de design.
- [`docs/finance.md`](docs/finance.md) — Finance Core v1.2: entidades,
  enums, regras, endpoints, cálculo do `monthly-summary` e limitações.
- [`docs/roadmap.md`](docs/roadmap.md) — etapas concluídas e próximas.
- [`docs/decisions.md`](docs/decisions.md) — decisões técnicas (D-01 a
  D-20).
- [`docs/how_to_run.md`](docs/how_to_run.md) — instalação, banco, servidor,
  testes, troubleshooting.
- [`docs/testing.md`](docs/testing.md) — fixtures, isolamento e cobertura
  por área.

## Requisitos

- **Python 3.12.x** (obrigatório — `pyproject.toml` exige `>=3.12,<3.13`).
- `pip` ou `uv`.

> **Atenção:** o `.python-version` direciona `pyenv`/`mise` para a versão
> correta.

## Setup rápido

```bash
# 1. Venv
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 2. Dependências
pip install -e ".[dev]"

# 3. Variáveis de ambiente
cp .env.example .env

# 4. Banco (Alembic é a única fonte de DDL)
alembic upgrade head

# 5. Servidor
uvicorn app.main:app --reload
```

API: <http://localhost:8000> · Swagger: <http://localhost:8000/docs> ·
Healthcheck: <http://localhost:8000/api/v1/health>

## Validação

```bash
ruff check .
ruff format --check .
pytest tests/ -v
```

Detalhes completos (incluindo round-trip Alembic e check de isolamento de
DB) em [`docs/how_to_run.md`](docs/how_to_run.md).

## Estrutura do projeto

```text
cartorio-system/
├── alembic/                 # migrations
├── app/
│   ├── core/                # config, logging, errors
│   ├── db/                  # session, base
│   ├── modules/finance/     # único módulo ativo (Finance Core v1.2)
│   ├── interfaces/api/v1/   # router HTTP
│   └── main.py
├── tests/
├── docs/                    # documentação técnica + operacional
├── exports/atlas/           # exports estruturados (futuros)
├── .env.example
├── pyproject.toml
└── README.md
```

## Integração com sistemas externos

A integração com outros sistemas (ex.: Atlas) ocorre **exclusivamente** por
dados estruturados (JSON/CSV) depositados em `exports/atlas/` ou por
chamadas explícitas a APIs. Nenhum banco, credencial ou código é
compartilhado diretamente.
