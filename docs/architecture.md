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
│   │   ├── finance/             # Finance Core v1.2 — REST; backlog futuro
│   │   │   ├── enums.py         # 5 enums + 3 mapas de regra
│   │   │   ├── models.py        # FinancialEntry, FinancialCategory
│   │   │   ├── rules.py         # regras cruzadas (single source of truth)
│   │   │   ├── schemas.py       # Pydantic Create/Update/Read + Summary
│   │   │   ├── service.py       # CRUD + compute_monthly_summary
│   │   │   └── router.py        # endpoints /api/v1/finance/*
│   │   ├── audit/               # auditoria interna — três submódulos
│   │   │   ├── scanner/         # inventário read-only de arquivos (CLI)
│   │   │   ├── diagnosis/       # DocumentDiagnosis, regras DIAG-*/TEMP-* (CLI)
│   │   │   └── findings/        # AuditFinding — REST
│   │   ├── compliance/          # Matriz INOVA V1, evidências, status — REST
│   │   ├── lgpd/                # ações do plano LGPD — REST
│   │   ├── retention/           # temporalidade documental — sem router;
│   │   │                        # consumido por audit/diagnosis
│   │   ├── notas/               # atos notariais
│   │   │   └── inventarios/     # minuta-base de inventário (CLI) — layout
│   │   │       ├── domain/      # hexagonal, ver "Camadas > Modules"
│   │   │       ├── application/ # calculator · validator · renderer
│   │   │       ├── infrastructure/  # loaders · exportador ODT · output_dir
│   │   │       └── interfaces/  # schemas Pydantic + CLI
│   │   └── (clients/, protocols/, documents/, tasks/, reports/, exports/)
│   │                              # placeholders para etapas futuras
│   ├── interfaces/
│   │   └── api/v1/router.py     # router raiz da v1; inclui finance, audit,
│   │                            # lgpd e compliance
│   └── main.py                  # FastAPI app + lifespan + handlers
├── scripts/
│   ├── local_tools/             # pipeline do Registro de Imóveis (7 ferramentas)
│   └── gerar_relatorio_pdf.py   # gerador one-off do relatório da diretoria
├── tests/
│   ├── conftest.py              # fixtures: test_engine, db_session, client
│   ├── golden/notas_inventarios/  # golden files comparados byte a byte
│   ├── test_isolation.py        # garante que pytest não toca cartorio.db
│   └── ...                      # um arquivo por área de domínio
├── docs/                        # esta documentação
├── exports/atlas/               # exports estruturados (ainda não usados)
├── .github/workflows/ci.yml     # quality gate: format, lint, testes, migrations
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

Cada módulo de domínio é autocontido. **Sete módulos estão implementados:**
`finance`, `audit` (scanner, diagnosis, findings), `lgpd`, `retention`,
`compliance` e `notas/inventarios`. As pastas `clients/`, `protocols/`,
`documents/`, `tasks/`, `reports/` e `exports/` seguem como placeholders
intencionais para evolução posterior.

**Dois padrões de layout coexistem** — a escolha entre eles ainda não é
governada por ADR:

- **Flat** (`finance`, `lgpd`, `retention`, `compliance`, `audit/findings`):
  `enums`, `models`, `rules`, `schemas`, `service`, `router` no mesmo nível.
- **Hexagonal** (`notas/inventarios`): `domain/`, `application/`,
  `infrastructure/`, `interfaces/`, com o domínio livre de framework, banco e
  rede.

**Nem todo módulo expõe HTTP.** `audit/scanner`, `audit/diagnosis` e
`notas/inventarios` são CLIs que produzem artefatos em arquivo;
`retention` não tem router e é consumido por `audit/diagnosis`.

**Isolamento.** Módulos não se referenciam por FK cruzada — o vínculo é feito
por referência fraca (`source_module` + `source_type` + `source_ref`), conforme
[ADR-002](decisions/ADR-002-weak-references-between-regulatory-modules.md).
Existe hoje **uma única** dependência direta entre módulos:
`audit/diagnosis → retention`, para emitir os findings TEMP-*. Ela é a exceção
ao princípio e ainda não está registrada em ADR.

### Interfaces (`app/interfaces/api/v1/`)

Roteador raiz da API v1. Expõe `/api/v1/health` e inclui os routers de
`finance`, `audit/findings`, `lgpd` e `compliance` — 37 rotas de negócio ao
todo. Novos módulos devem ser plugados aqui.

**A API não tem autenticação.** A autoria é registrada por defaults literais
(`created_by`/`updated_by` = `"gestor"`), conforme a decisão D-08 da fase MVP
monousuário. Autenticação individualizada e trilha de auditoria transversal são
exigências do Provimento CNJ 213/2026 ainda **não iniciadas** — ver
[roadmap.md](roadmap.md), Horizonte C.

### Ferramentas fora de `app/` (`scripts/local_tools/`)

O **pipeline do Registro de Imóveis** — sete ferramentas de CLI que extraem,
classificam, reconciliam e consolidam o inventário de matrículas de forma
sanitizada (contratos anti-PII, sem nomes, CPF ou CNPJ) — vive em
`scripts/local_tools/`, **não** em `app/modules/`. É o maior bolsão de lógica
e de testes do repositório e produziu a base do dossiê PROAD/IERI.

Registro honesto do status arquitetural: **essa localização é um fato, não uma
decisão registrada.** A promoção a `app/modules/registro_imoveis/` está em
aberto e depende de decisão humana (DH-1) — ver
[`docs/audits/repository_rebaseline_2026_07/05_BLUEPRINT_REPOSITORIO_ALVO.md`](audits/repository_rebaseline_2026_07/05_BLUEPRINT_REPOSITORIO_ALVO.md).
Até que essa decisão seja tomada, o pipeline deve ser tratado como **camada de
ferramentas locais**, sem router, sem migration e sem acoplamento com `app/`.

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

O diagnóstico técnico de Maio/2026 identificou riscos críticos na infraestrutura
da serventia — incluindo backup sem dump consistente do banco do Engegraph e
ausência de plano de contingência documentado. Por isso, o módulo de auditoria
interna (`app/modules/audit/`) precede a expansão de novos módulos operacionais.

O contexto técnico e as pendências do Engegraph estão distribuídos entre:

| Documento | O que traz |
|---|---|
| [`infrastructure/infrastructure_roadmap.md`](infrastructure/infrastructure_roadmap.md) | Situação do ERP e do seu banco, política de dump e backup, contingência |
| [`infrastructure/target_infrastructure.md`](infrastructure/target_infrastructure.md) | VMs `VM-Engegraph-App` e `VM-Engegraph-DB` na arquitetura-alvo |
| [`modules/audit.md`](modules/audit.md) | Riscos identificados no diagnóstico de Maio/2026 |

> **Nota:** versões anteriores desta documentação apontavam para um
> `docs/operations/engegraph.md` que **nunca existiu** no repositório. A
> referência foi substituída pelos documentos acima em vez de criar um arquivo
> apenas para satisfazer o link.
