# Knowledge Base Implementation Roadmap

Roadmap incremental, **sem prazos fixos**, para a futura implementação do
módulo `knowledge_base` do Cartório System.

> Este documento complementa o
> [`KNOWLEDGE_BASE_BLUEPRINT.md`](KNOWLEDGE_BASE_BLUEPRINT.md) e está
> subordinado às proibições do [`CLAUDE.md`](../../CLAUDE.md) e às
> [ADRs 004–008](../decisions/).
>
> **Nada deste roadmap está implementado.** Cada fase exige decisão humana
> formal antes de iniciar.

---

## 1. Estado atual

| Item | Estado |
|---|---|
| Blueprint documental (KB-0) | **Concluído** (Sprint KNOWLEDGE-BASE-0, 2026-05-23) |
| Revisão de qualidade, allowlist e governança (KB-0.1) | **Concluída** (Sprint KNOWLEDGE-BASE-0.1, 2026-05-25) |
| [`PHASE_1_SOURCE_ALLOWLIST.md`](PHASE_1_SOURCE_ALLOWLIST.md) | Criada — fontes em `CANDIDATE_REQUIRES_REVIEW` aguardando DHP-06..09 |
| [`GOVERNANCE_DECISIONS.md`](GOVERNANCE_DECISIONS.md) | Criada — DHP-01..10 em `PROPOSED` |
| Módulo `app/modules/knowledge_base/` | **Não existe** |
| Módulo `app/modules/ai_gateway/` | **Não existe** |
| Banco / migration / schema | **Não criados** |
| Endpoints REST | **Não criados** |
| Integração com IA externa | **Não criada** |
| Embeddings / RAG / MCP / agentes | **Não criados** |
| Aprovação humana para implementar KB-1 | **Pendente** (DHP-01 a DHP-10) |

---

## 2. Fase 0 — Blueprint documental

**Status:** concluído na Sprint KNOWLEDGE-BASE-0 (2026-05-23) e revisado
na Sprint KNOWLEDGE-BASE-0.1 (2026-05-25).

**Entregas:**

- `docs/knowledge_base/KNOWLEDGE_BASE_BLUEPRINT.md`
- `docs/knowledge_base/README.md`
- `docs/knowledge_base/IMPLEMENTATION_ROADMAP.md` (este documento)
- `docs/knowledge_base/PHASE_1_SOURCE_ALLOWLIST.md` (KB-0.1)
- `docs/knowledge_base/GOVERNANCE_DECISIONS.md` (KB-0.1)

**Critério de aceite:** o blueprint define classificação de fontes,
metadados, chunking, citações, versionamento, política local/API externa e
limitações conhecidas. A allowlist registra fontes candidatas/permitidas/
bloqueadas com status por linha. As decisões de governança (DHP-01..10)
estão registradas como `PROPOSED`. Nenhum código foi escrito.

---

## 3. Fase 1 — Modelo conceitual de dados

**Escopo:**

- Modelagem conceitual das entidades `Document` e `Chunk`, com seus
  metadados (Seção 11 e 12 do blueprint).
- Definição dos enums (`source_type`, `chunk_type`, `confidentiality_level`,
  `pii_risk_level`).
- Definição do contrato de versionamento (`document_id` estável, `checksum`,
  `version_label`, `is_current`, `is_revoked`, `replaces`, `replaced_by`).
- Possíveis schemas Pydantic **em rascunho**, sem persistência.

**Fora desta fase:**

- Migration.
- Tabelas reais.
- Endpoints.
- Qualquer ingestão de conteúdo.

**Pré-requisitos:** aprovação humana formal de KB-0 e decisão sobre quais
documentos farão parte da base inicial (DHP-03 a DHP-07).

**Critério de aceite:** modelagem conceitual documentada e revisada; nenhum
módulo Python ainda criado.

---

## 4. Fase 2 — Registry local de documentos

**Escopo:**

- Implementação local **mínima** de um registry de documentos.
- Sem IA externa, sem embeddings, sem chamadas para fora.
- CRUD interno, restrito a uso local de curadoria.
- Versionamento por `document_id` + `version_label`.
- Validação de classificação obrigatória (Seção 6 do blueprint).

**Fora desta fase:**

- Chunks indexados.
- Citações canônicas implementadas.
- API externa.

**Pré-requisitos:** KB-1 aceita e ADR específica abrindo a implementação.

**Critério de aceite:** registro local de documentos com metadados completos
e versionamento auditável; cobertura por testes; isolamento de outros
módulos (`audit`, `lgpd`, `retention`, `compliance`, `finance`,
`registro_imoveis`, `notas`).

---

## 5. Fase 3 — Chunks e citações

**Escopo:**

- Implementação local de chunks de documentos com citação canônica
  rastreável.
- Validador de citação canônica (Seção 15 do blueprint): rejeitar formatos
  genéricos.
- Vínculo `chunk.document_id → document.document_id`.
- Sem indexação semântica, sem embeddings, sem RAG.

**Fora desta fase:**

- API externa.
- Geração de respostas.
- `ai_gateway`.

**Pré-requisitos:** KB-2 operacional; curadoria definida; ADR específica.

**Critério de aceite:** chunks persistidos com citação canônica válida;
testes cobrindo formatos válidos e inválidos; nenhuma chamada externa.

---

## 6. Fase 4 — Ingestão controlada de fontes públicas

**Escopo:**

- Ingestão **manual e curada** de fontes públicas (Provimento CNJ 213/2026,
  Provimento CNJ 50/2015 e compilado, CNPFE-GO por capítulos relevantes,
  ADRs do projeto, demais leis públicas aplicáveis).
- Cada fonte ingressa com classificação, metadados e checksum.
- Curadoria humana **obrigatória** antes de marcar uma versão como
  `is_current=true`.
- Fontes interpretativas (Matriz/Guia InovaLGPD) entram como
  `THIRD_PARTY_CONSULTING_DOC`, com `external_api_allowed=false`.

**Fora desta fase:**

- Documentos confidenciais (`INTERNAL_CONFIDENTIAL_DOC`) — exigem ADR
  específica.
- Dados operacionais reais.
- IA externa.

**Pré-requisitos:** KB-3 operacional; lista explícita de documentos
autorizados pelo gestor.

**Critério de aceite:** base normativa local operacional, citável e
versionada; consultas locais retornam chunks com citação canônica.

---

## 7. Fase 5 — Validações e relatórios

**Escopo:**

- Relatórios de curadoria: documentos faltantes, conflitos de versão,
  citações inválidas, chunks órfãos.
- Detecção de mudanças de fonte via checksum.
- Procedimentos formais de atualização de fontes (substituição de versão
  vigente, marcação de revogação).
- Cobertura completa de testes da base.

**Pré-requisitos:** KB-4 operacional em uso real de curadoria.

**Critério de aceite:** base estável, auditável, com relatórios e
procedimentos documentados. **Esta é a condição mínima para abrir
discussão sobre AI-GATEWAY-0 (ADR-005).**

---

## 8. Fase 6 — Preparação para `ai_gateway`

**Escopo conceitual** (não-implementação ainda):

- Definição de contrato de interface entre `knowledge_base` e
  `ai_gateway` (ADR-004).
- Política de redaction.
- Política de logging (`AiCallLog`).
- Política de classificação de saída (`INFORMATIVO`, `RASCUNHO`,
  `REQUER_VALIDACAO_JURIDICA`) — ADR-008.
- Feature flag `AI_GATEWAY_ENABLED=false` por padrão.
- Modo dry-run com mocks.

**Pré-requisitos:** KB-5 aceita; ADR formal autorizando `ai_gateway`;
contrato Enterprise/ZDR avaliado, se aplicável.

**Critério de aceite:** plano explícito e aprovado de implementação do
`ai_gateway`, com critérios de governança documentados. A implementação
em código é objeto de sprint própria (AI-GATEWAY-0) — **fora deste roadmap**.

---

## 9. Fora do roadmap inicial

Itens **explicitamente fora** deste roadmap e que exigirão ADR específica
para reentrar em pauta:

- MCP Connectors prontos (ADR-007).
- MCP Server próprio (ADR-007).
- Agentes autônomos (ADR-007).
- Uso de embeddings ou RAG antes de KB-5.
- Envio de `INTERNAL_CONFIDENTIAL_DOC` para API externa.
- Envio de `OPERATIONAL_METADATA` sem redaction validada para API externa.
- Qualquer envio de `SENSITIVE_OPERATIONAL_DATA` a serviços externos (ADR-006).
- Integração com Atlas a partir da knowledge_base.
- Compartilhamento de banco entre `knowledge_base` e outros módulos.

---

## 10. Critérios para autorizar implementação

A passagem de qualquer fase deste roadmap para a seguinte exige, no mínimo:

1. **Aprovação humana** explícita do gestor/delegatário, registrada em ADR.
2. **Critério de maturidade** atendido — não basta o calendário.
3. **Testes** previstos e cobertura definida.
4. **Documentação** atualizada antes de qualquer commit de código.
5. **Sem dependência cruzada** com módulos de negócio (`audit`, `lgpd`,
   `retention`, `compliance`, `finance`, `registro_imoveis`, `notas`).
6. **Sem dados sensíveis** ingressando na base.
7. **Sem IA externa** até KB-5 estar estável (ADR-005).
8. **Política de revisão humana** aplicada (ADR-008).
9. **Política de dados** aplicada (ADR-006).

**Nenhuma fase começa por iniciativa do Claude.** O início depende de
decisão humana formal, registrada em sprint própria.

---

*Sprint KNOWLEDGE-BASE-0 — 2026-05-23.*
*Roadmap conceitual, sem prazos fixos, sem código.*
