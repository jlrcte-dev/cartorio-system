# Roadmap

## Etapas concluídas

### Etapa 0 — Fundação FastAPI ✅
Estrutura base do projeto: `app/{core,db,modules,interfaces}`, FastAPI com
lifespan, settings via pydantic-settings, logging estruturado, handlers de
erro, healthcheck `GET /api/v1/health`, primeiros testes.

### Etapa 0.1 — Pin Python 3.12 ✅
`requires-python = ">=3.12,<3.13"` no `pyproject.toml`, `.python-version`
com `3.12`, venv recriado.

### Etapa 1 — Finance Core v1 ✅
- Alembic configurado.
- `FinancialEntry` e `FinancialCategory` (esta como catálogo, não exposta).
- Enums `EntryType`, `EntryStatus`, `ServiceArea`.
- Endpoints CRUD em `/api/v1/finance/entries` + `GET /monthly-summary`.
- 17 testes.

### Etapa 1.1 — Finance Core Hardening ✅
- Adicionados `EntryDirection` (INFLOW/OUTFLOW) e `EntrySource` (enum).
- Auditoria mínima: `created_by` / `updated_by` (default `gestor`).
- Regra status × tipo (mapa `ALLOWED_STATUS_BY_TYPE`).
- Migration reversível com backfill de `direction` por `entry_type`.
- 31 testes.

### Etapa 1.2 — Hardening pós-audit ✅
- `Base.metadata.create_all` removido do lifespan; Alembic é a única fonte
  de DDL.
- Handler 500 passou a logar traceback.
- `httpx`/`httpcore` silenciados nos logs.
- `CheckConstraint` GLOB de `competence_month` removida (portabilidade
  Postgres).
- `entry_type` e `competence_month` agora são imutáveis no PATCH
  (`extra="forbid"` em `FinancialEntryUpdate`).
- Regra `payment_date × status` aplicada em create e update.
- Regras movidas para `app/modules/finance/rules.py`.
- `amount: null` rejeitado no PATCH.
- Teste de isolamento garante que `pytest` não cria/toca `cartorio.db`.
- **48 testes passando.**

## Próxima etapa

### Etapa 2 — Monthly Closing 🟡 (planejada)
Persistir o fechamento mensal como artefato auditável, transformando o
`MonthlySummary` calculado em snapshot armazenado e travando alterações no
mês fechado.

Escopo previsto:
- Modelo `MonthlyClosing` (id, `competence_month` único, `closed_at`,
  `closed_by`, `status` open/closed/reopened, snapshot do `MonthlySummary`).
- Endpoint para fechar/reabrir mês.
- Lock: lançamentos em mês fechado bloqueiam create/update — exceção para
  ajustes "post-closing" sinalizados explicitamente.
- Distinção formal entre `realized_result` e `projected_result`.
- Reaproveitar `compute_monthly_summary` como cálculo do snapshot.

## Etapas seguintes (ordem indicativa)

### Etapa 3 — Obligations / Reports
Modelagem de obrigações periódicas e seus prazos:
- `ObligationType` (CNJ, SEDI, ISS, CRC, ONR, Sioreg, FIC RC/RTD/SREI,
  Arpen, Cori…).
- Ocorrências mensais derivadas com `due_date`, `competence`, `status`.
- Vínculo opcional com `FinancialEntry` (REPASSE/DESPESA correspondente).
- Painel de prazos.

### Etapa 4 — Exports
- CSV e JSON do mês.
- Resumo para contabilidade.
- Estrutura de exports para o Atlas (`exports/atlas/`).
- Sem ZIP de comprovantes ainda — depende da Etapa 5.

### Etapa 5 — Anexos / Comprovantes
- Modelo `EntryAttachment` (path local, hash, mime, tamanho).
- Endpoint de upload + download.
- Sem GED próprio nesta etapa — apenas anexar arquivo a lançamento.

### Etapa 6 — Importação de planilhas históricas
- Importador das planilhas em `docs/Gerenciamento_financeiro/2025` e
  `2026`.
- `EntrySource = IMPORT_XLSX`.
- Idempotência por hash + competência.
- Hidratação dos dados reais para alimentar relatórios e fechamentos.

### Etapa 7 — Categorias financeiras (CRUD)
- Expor `FinancialCategory` via API.
- Seed inicial com categorias visíveis nos dados (energia, internet,
  Engegraph, ARPEN, FIC, ISS, INSS, FGTS, e-notariado, taxa judiciária,
  emolumentos por área).
- FK opcional `FinancialEntry.category_id`.

## Etapas que ficam para *muito* depois

- Autenticação multiusuário (perfis, sessões).
- Integração direta com Engegraph (consumir API/exports).
- Integração com bancos (open finance / extratos automáticos).
- Automação tributária (cálculo IR completo).
- Dashboard interativo.
- Mobile / cliente externo.

## Princípios de evolução

1. Adicionar módulos sem mexer nos existentes — `app/modules/<novo>/`
   espelha o layout de `finance`.
2. Toda regra cruzada nova mora em `rules.py` do módulo.
3. Toda mudança de schema passa por migration Alembic reversível, com
   backfill explícito quando colunas NOT NULL forem adicionadas.
4. Etapa nova só começa quando a anterior está com ruff limpo e testes
   passando.
