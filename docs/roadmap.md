# Roadmap

> Para o roadmap estratégico completo de adequação ao Provimento CNJ nº 213/2026
> (Classe 3), ver [`docs/regulatory/cnj_213/roadmap.md`](regulatory/cnj_213/roadmap.md).
>
> Para o roadmap detalhado do Módulo de Auditoria (12 fases + Sprint 1),
> ver [`docs/audit/module_roadmap.md`](audit/module_roadmap.md).

---

## Mudança estratégica — Maio/2026

### O que mudou

O foco principal de desenvolvimento passou a ser o **Módulo de Auditoria da Serventia**.

| Item | Status |
| ------ | -------- |
| Finance Core v1.2 | Preservado; **backlog futuro — não expandir agora** |
| Monthly Closing (Etapa 2) | Rebaixado para backlog futuro |
| Módulo de Auditoria | **Prioridade principal de desenvolvimento** |
| Sprint 1 — Scanner Read-Only | ✅ **Implementado e testado** |

### Por que

A serventia foi classificada como **Classe 3** (Provimento CNJ 213/2026) e será
vistoriada em breve. O risco imediato é a ausência de inventário, diagnóstico,
evidências e rastreabilidade — não a ausência de módulo financeiro expandido.

O Scanner Read-Only entrega valor utilizável em horas de uso. O módulo financeiro
expandido pode esperar.

**Metas mínimas Classe 3:** RPO ≤ 4h | RTO ≤ 8h | Prazo global: 24 meses

---

## Módulo de Auditoria — Próximas sprints

### Sprint 1 — Scanner Read-Only de Arquivos ✅ (concluída)

Implementado em `app/modules/audit/scanner/`. **72 testes passando.**

```bash
python -m app.modules.audit.scanner.cli \
    --root "D:\Dados" \
    --output-dir "exports\audit\scan-servidor-2026-05-04" \
    --run-name "scan-servidor-2026-05-04"
```

Gera: `file_inventory.json`, `file_inventory.csv`, `scan_summary.md`,
`scan_manifest.json` (com `read_only: true` e hashes SHA-256).

Ver guia completo em [`docs/modules/audit_file_scanner.md`](modules/audit_file_scanner.md).

### Sprint 2 — AuditFinding CRUD ✅ (concluída)

108 testes passando. Endpoints: `POST`, `GET`, `GET/{id}`, `PATCH/{id}`,
`POST/{id}/status`, `POST/{id}/archive`. Sem `DELETE` físico.
Ver [`docs/modules/audit_findings.md`](modules/audit_findings.md).

### Sprint 3 — Diagnóstico Documental Inicial 🟡 (próxima)

Analisa o `file_inventory.json` coletado na Sprint 1 para identificar
padrões problemáticos. **Entrada: artefatos do scanner — não o servidor diretamente.**
(Ver decisão D-23 em [`docs/decisions/technical_decisions.md`](decisions/technical_decisions.md).)

- Módulo `app/modules/audit/diagnosis/`
- `DocumentDiagnosis.from_inventory(path)` — recebe inventory, valida hash
- Detecta: nomes genéricos, arquivos antigos, extensões suspeitas, prováveis duplicatas
- Saídas: `diagnosis_report.md`, CSVs por categoria, `manifest.json`
- Testes com inventories sintéticos em memória — sem caminhos reais

Pré-requisito: executar scanner no acervo real da serventia ao menos uma vez
antes de iniciar a sprint. Ver procedimento em
[`docs/audit/deployment_and_operation.md`](audit/deployment_and_operation.md).

### Sprints futuras (Fases 2-10)

Ver [`docs/audit/module_roadmap.md`](audit/module_roadmap.md) para todas as 12 fases.

---

## Eixo regulatório — Provimento CNJ nº 213/2026 (Classe 3)

A serventia foi classificada como **Classe 3**. Certas funcionalidades do Cartório
System são antecipadas em função das exigências do Provimento:

- Autenticação multiusuário: pré-requisito para uso por colaboradores (não "muito depois")
- Trilha de auditoria: requisito estrutural
- Exports: precisam de checksum, timestamp e identificação do usuário

---

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

- `Base.metadata.create_all` removido do lifespan; Alembic é a única fonte de DDL.
- Handler 500 passou a logar traceback.
- `httpx`/`httpcore` silenciados nos logs.
- `CheckConstraint` GLOB de `competence_month` removida (portabilidade Postgres).
- `entry_type` e `competence_month` agora são imutáveis no PATCH.
- Regra `payment_date × status` aplicada em create e update.
- Regras movidas para `app/modules/finance/rules.py`.
- `amount: null` rejeitado no PATCH.
- Teste de isolamento garante que `pytest` não cria/toca `cartorio.db`.
- **48 testes passando.**

### Etapa A — Documentação e visão do módulo de auditoria ✅

- Contexto técnico do Engegraph documentado
- Riscos e pendências de infraestrutura registrados
- Documentação inicial do módulo criada
- Roadmap estratégico CNJ 213/2026 criado
- Módulo de auditoria posicionado como prioridade principal

---

## Inteligência normativa — preparação documental

A Sprint **KNOWLEDGE-BASE-0** (2026-05-23) entregou apenas documentação
conceitual da futura base de conhecimento normativo. Não há código,
banco, migration, endpoint, embeddings, RAG, MCP, agentes nem integração
com IA externa. Ver
[`docs/knowledge_base/`](knowledge_base/) — em especial
[`KNOWLEDGE_BASE_BLUEPRINT.md`](knowledge_base/KNOWLEDGE_BASE_BLUEPRINT.md)
e [`IMPLEMENTATION_ROADMAP.md`](knowledge_base/IMPLEMENTATION_ROADMAP.md).

A implementação efetiva (KB-1 em diante) depende de aprovação humana
formal e de ADRs específicas por fase (ADRs 004–008).

---

## Backlog futuro — módulo financeiro

O módulo financeiro é preservado integralmente. Estas etapas voltam ao roadmap
ativo quando o módulo de auditoria estiver em uso operacional real.

### Etapa 2 — Monthly Closing

Persistir fechamento mensal como artefato auditável com snapshot de `MonthlySummary`,
lock de mês fechado e distinção entre `realized_result` e `projected_result`.

### Etapa 3 — Obligations / Reports

`ObligationType` (CNJ, SEDI, ISS, CRC, ONR…), ocorrências mensais com `due_date`,
vínculo com `FinancialEntry`.

### Etapa 4 — Exports

CSV/JSON do mês, resumo para contabilidade, estrutura para o Atlas (`exports/atlas/`).

### Etapas 5-7

Anexos/comprovantes, importação de planilhas históricas (2016-2026),
categorias financeiras com CRUD e seed.

---

## Princípios de evolução

1. Adicionar módulos sem mexer nos existentes — `app/modules/<novo>/`
   espelha o layout de `finance`.
2. Toda regra cruzada nova mora em `rules.py` do módulo.
3. Toda mudança de schema passa por migration Alembic reversível, com
   backfill explícito quando colunas NOT NULL forem adicionadas.
4. Etapa nova só começa quando a anterior está com ruff limpo e testes passando.
5. **Read-only first.** O scanner nunca modifica arquivos do servidor analisado.
6. **Uso prático ao final de cada sprint.** Nenhuma sprint é preparatória sem entregável.
