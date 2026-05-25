# docs/knowledge_base — Base documental do futuro módulo `knowledge_base`

Esta pasta concentra a documentação **conceitual e arquitetural** da futura
base de conhecimento normativo do Cartório System.

> **Atenção.** Nenhum módulo `knowledge_base` foi implementado.
> Não há código, banco, migration, schema, endpoint, CLI, embeddings, RAG,
> integração com IA externa, MCP nem agentes nesta etapa.
> A pasta é uma **base de preparação documental** para sprints futuras.

## Por que esta pasta existe

O Cartório System precisa, no futuro, organizar fontes normativas e
referências legais de forma estruturada — com metadados, versões, chunks e
citações rastreáveis — antes de qualquer uso de IA externa. As decisões
arquiteturais relevantes estão registradas em:

- [ADR-004 — Separação entre Knowledge Base e AI Gateway](../decisions/ADR-004-separacao-knowledge-base-ai-gateway.md)
- [ADR-005 — Knowledge Base antes de IA externa](../decisions/ADR-005-knowledge-base-antes-de-ia-externa.md)
- [ADR-006 — Dados permitidos e proibidos para IA](../decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md)
- [ADR-007 — MCP e agentes autônomos fora das fases iniciais](../decisions/ADR-007-mcp-e-agentes-fora-das-fases-iniciais.md)
- [ADR-008 — Toda saída de IA é rascunho sujeito à revisão humana](../decisions/ADR-008-saida-de-ia-e-rascunho-sujeito-a-revisao.md)

A Sprint **KNOWLEDGE-BASE-0** (2026-05-23) produziu apenas documentação,
respeitando as proibições do [`CLAUDE.md`](../../CLAUDE.md) e o limite de
escopo definido.

## Documentos desta pasta

| Documento | Descrição |
|---|---|
| [`KNOWLEDGE_BASE_BLUEPRINT.md`](KNOWLEDGE_BASE_BLUEPRINT.md) | Blueprint conceitual completo: princípios, classificação de fontes, metadados, chunking, citações, versionamento, política local/API externa, limitações e checklist |
| [`PHASE_1_SOURCE_ALLOWLIST.md`](PHASE_1_SOURCE_ALLOWLIST.md) | Lista **explícita** e revisável das fontes autorizáveis na Fase 1, com status por linha e critérios de adição |
| [`GOVERNANCE_DECISIONS.md`](GOVERNANCE_DECISIONS.md) | Decisões humanas pendentes (DHP-01..10), critérios de aprovação das ADRs 004–008 e regras de não regressão |
| [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) | Roadmap incremental por fase, sem prazos fixos, com critérios de autorização para implementação |

## O que ainda não existe

- `app/modules/knowledge_base/` (módulo Python).
- `app/modules/ai_gateway/` (módulo Python).
- Tabelas, schemas, migrations, endpoints, CLI ou jobs.
- Embeddings, índice vetorial, RAG.
- Integração com API externa (Anthropic, OpenAI, Google etc.).
- MCP Server, MCP Connectors, agentes autônomos.

Qualquer implementação dependerá de aprovação humana formal e de ADR
específica para cada fase futura (ver `IMPLEMENTATION_ROADMAP.md`).
