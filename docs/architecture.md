# Arquitetura

## Visão geral

O **Sistema do Cartório** é o backend independente da serventia. Não compartilha
código, banco, credenciais ou dependências com outros sistemas. A integração
futura (ex.: Atlas) ocorre **exclusivamente** por dados estruturados (JSON/CSV)
em `exports/atlas/` ou por chamadas explícitas a APIs.

O sistema **coexiste** com o **Engegraph** (ERP cartorial existente, núcleo
operacional para atos, livros e selos). Esta fase do MVP **não substitui** o
Engegraph — preenche a camada que o Engegraph não cobre: gestão financeira,
fiscal, contábil e gerencial do gestor.

## Stack

- **Python** 3.12.x (pinado em `pyproject.toml` e `.python-version`)
- **FastAPI** — API HTTP
- **SQLAlchemy 2** — ORM
- **Alembic** — migrations (única fonte de DDL; nunca `create_all` em runtime)
- **Pydantic v2 + pydantic-settings** — validação e configuração
- **Pytest** — testes
- **Ruff** — lint + format
- **SQLite** em desenvolvimento (`cartorio.db`); **Postgres** previsto para
  produção

## Estrutura de diretórios

```text
cartorio-system/
├── alembic/
│   ├── env.py                   # carrega settings + Base.metadata
│   ├── script.py.mako
│   └── versions/                # migrations versionadas
├── alembic.ini
├── app/
│   ├── core/                    # configuração transversal
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── errors.py            # CartorioException + handlers HTTP
│   │   └── logging.py           # setup_logging + get_logger
│   ├── db/
│   │   ├── base.py              # DeclarativeBase + registro de modelos
│   │   └── session.py           # engine + SessionLocal + get_db
│   ├── modules/
│   │   ├── finance/             # único módulo ativo
│   │   │   ├── enums.py         # 5 enums + 3 mapas de regra
│   │   │   ├── models.py        # FinancialEntry, FinancialCategory
│   │   │   ├── rules.py         # regras cruzadas (single source of truth)
│   │   │   ├── schemas.py       # Pydantic Create/Update/Read + Summary
│   │   │   ├── service.py       # CRUD + compute_monthly_summary
│   │   │   └── router.py        # endpoints /api/v1/finance/*
│   │   └── (clients/, protocols/, documents/, tasks/, reports/, exports/)
│   │                              # placeholders para etapas futuras
│   ├── interfaces/
│   │   └── api/v1/router.py     # router raiz da v1; inclui finance
│   └── main.py                  # FastAPI app + lifespan + handlers
├── tests/
│   ├── conftest.py              # fixtures: test_engine, db_session, client
│   ├── test_finance_entries.py
│   ├── test_health.py
│   └── test_isolation.py        # garante que pytest não toca cartorio.db
├── docs/                        # esta documentação
├── exports/atlas/               # exports estruturados (ainda não usados)
└── pyproject.toml
```

## Camadas

### Core (`app/core/`)
Configuração transversal: `Settings` carregadas de `.env` via
`pydantic-settings`; logging em `stdout`; classe de exceção
`CartorioException` com `status_code`; handler 500 que **loga traceback**
antes de devolver `{"detail": "Erro interno do servidor."}`.

### DB (`app/db/`)
- `Base` (DeclarativeBase) registra modelos automaticamente via
  `_register_models()` no import.
- `engine` é construído a partir de `settings.database_url` (lazy connect).
- `get_db()` é a dependency injection do FastAPI (yield + close).

### Modules (`app/modules/`)
Cada módulo de domínio é autocontido: `enums`, `models`, `rules`, `schemas`,
`service`, `router`. Hoje apenas `finance` está implementado. As pastas
`clients`, `protocols`, `documents`, `tasks`, `reports`, `exports` são
placeholders intencionais para a evolução posterior.

### Interfaces (`app/interfaces/api/v1/`)
Roteador raiz da API v1. Expõe `/api/v1/health` e inclui o router de
`finance`. Novos módulos devem ser plugados aqui.

### Main (`app/main.py`)
Compõe a aplicação: chama `setup_logging()` no nível de módulo (antes do
`FastAPI(...)`), instala os handlers de exceção e o lifespan (que
**não** executa DDL — apenas log de start/stop).

## Princípios de design

1. **Alembic é a única fonte de DDL.** O lifespan não chama
   `Base.metadata.create_all`. Setup de DB para dev/CI/prod = `alembic upgrade
   head`. Para tests = `Base.metadata.create_all` em fixture sobre engine
   in-memory.
2. **Regras de domínio centralizadas.** Validações cruzadas (status × tipo,
   direction × tipo, payment_date × status) ficam em `rules.py`. Schemas e
   service importam de lá.
3. **Imutabilidade contábil.** `entry_type` e `competence_month` não mudam
   após criação (FinancialEntryUpdate usa `extra="forbid"` e não declara
   esses campos). Para corrigir: cancelar e recriar.
4. **Auditoria mínima sem autenticação.** Cada entry guarda `created_by` e
   `updated_by` (default `"gestor"`). Autenticação real é etapa futura.
5. **Validação primeiro no Pydantic.** Constraints de banco (CHECK) ficam
   apenas para invariantes universais (ex.: `amount > 0`); regras de formato
   e cruzadas ficam em Pydantic/`rules.py` — facilita migração para Postgres.

## Compatibilidade futura com Postgres

- Enums usam `Enum(..., native_enum=False)` → armazenados como `VARCHAR`. Não
  dependem de tipos nativos do SQLite ou do Postgres.
- Não há mais `CHECK ... GLOB ...` no schema (removido na Etapa 1.2).
- `Numeric(14, 2)` para valores monetários é portável.
- `DateTime(timezone=True)` é portável.
- Migrations usam `batch_alter_table` que é tolerante a SQLite e operacional
  em Postgres.

A migração para Postgres consistirá em mudar `DATABASE_URL` e rodar
`alembic upgrade head`.

## Independência do Atlas

Decisão estrutural: o Sistema do Cartório **não importa nada do Atlas** e
**nada do Atlas é deployado junto**. A integração planejada é unidirecional
e assíncrona: o Sistema do Cartório gera arquivos em `exports/atlas/` (CSV
ou JSON) que o Atlas consome em outro processo.

## Coexistência com Engegraph

O Engegraph é a fonte da verdade para atos, livros, folhas e selos. O Sistema
do Cartório **não duplica** essas entidades. O escopo atual cobre apenas
gestão financeira; a integração com o Engegraph (ex.: importar emolumentos
diários) é uma etapa futura via `EntrySource = ENGEGRAPH_EXPORT`.
