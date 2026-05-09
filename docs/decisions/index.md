# Índice de Decisões — Cartório System

Este diretório contém as decisões técnicas e arquiteturais do projeto, em dois formatos:

- **Decisões técnicas (D-XX):** decisões de implementação registradas em [`technical_decisions.md`](technical_decisions.md), cobrindo stack, banco, migrations, padrões de código e princípios do sistema.
- **ADRs (Architecture Decision Records):** decisões arquiteturais formalizadas no formato padrão (Contexto / Decisão / Consequências / Alternativas).

---

## Decisões técnicas (D-01 a D-23)

Arquivo: [`technical_decisions.md`](technical_decisions.md)

| ID | Assunto |
|----|---------|
| D-01 | Stack: Python 3.12 + FastAPI + SQLAlchemy 2 + Pydantic v2 |
| D-02 | Python 3.12 pinado em `>=3.12,<3.13` |
| D-03 | SQLite em desenvolvimento; Postgres planejado para produção |
| D-04 | Alembic é a única fonte de DDL |
| D-05 | Finance-first em vez de Protocols-first |
| D-06 | Sistema independente do Atlas |
| D-07 | Coexistência com Engegraph; sem substituição |
| D-08 | Auditoria mínima sem autenticação |
| D-09 | Validação financeira no Pydantic + service, antes do banco |
| D-10 | `entry_type` e `competence_month` imutáveis após criação |
| D-11 | `amount` no PATCH: omitido OK, positivo OK, `null` proibido |
| D-12 | `payment_date × status` é regra dura |
| D-13 | `CANCELLED` e `TO_REVIEW` ficam fora do `result_estimate` |
| D-14 | `result_estimate` inclui `PENDING` (é estimativa, não caixa) |
| D-15 | Direction obrigatória — rígida em RECEITA/DESPESA/REPASSE, livre em AJUSTE |
| D-16 | Logging em stdout; handler 500 com `logger.exception` |
| D-17 | Migrations com backfill explícito ao adicionar coluna NOT NULL |
| D-18 | Não usar `from __future__ import annotations` em `schemas.py` |
| D-19 | Catálogo `FinancialCategory` existe mas não é exposto |
| D-20 | Testes em SQLite in-memory + StaticPool |
| D-21 | Módulo de auditoria interna antes da expansão operacional |
| D-22 | Adequação ao Provimento CNJ nº 213/2026 como eixo paralelo |
| D-23 | DocumentDiagnosis analisa artefatos do scanner, não o servidor diretamente |

---

## ADRs

| ADR | Título | Status |
|-----|--------|--------|
| [ADR-001](ADR-001-compliance-evidence-ownership.md) | ComplianceEvidence como entidade central de evidência regulatória | Aceito |
| [ADR-002](ADR-002-weak-references-between-regulatory-modules.md) | Referências fracas entre módulos regulatórios | Aceito |
| [ADR-003](ADR-003-document-registry-ownership.md) | Document Registry — ownership e fronteiras do módulo | Aceito |

---

## Como criar um novo ADR

1. Copiar o template:
   ```
   ADR-NNN-titulo-curto.md
   ```
2. Preencher as seções: Status, Contexto, Decisão, Consequências positivas, Consequências negativas, Alternativas consideradas, Referências.
3. Adicionar linha neste índice.
4. Referenciar no commit e no sprint report.

Ver critérios de obrigatoriedade em [`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md), Seção 6.
