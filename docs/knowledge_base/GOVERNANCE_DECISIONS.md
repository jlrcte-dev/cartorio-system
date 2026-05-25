# Governance Decisions — Knowledge Base

> Documento da Sprint **KNOWLEDGE-BASE-0.1** (2026-05-25).
> Registra **decisões de governança pendentes** e critérios de aprovação
> para a futura `knowledge_base`. Nenhuma decisão é tomada automaticamente
> por este documento. Todas as decisões aqui listadas dependem de
> aprovação humana formal do gestor/delegatário.
>
> Subordinado a:
> - [`KNOWLEDGE_BASE_BLUEPRINT.md`](KNOWLEDGE_BASE_BLUEPRINT.md)
> - [`PHASE_1_SOURCE_ALLOWLIST.md`](PHASE_1_SOURCE_ALLOWLIST.md)
> - [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md)
> - [ADRs 004–008](../decisions/)
> - [`CLAUDE.md`](../../CLAUDE.md)

---

## 1. Objetivo

Este documento registra:

- decisões humanas pendentes (DHP) necessárias para que a knowledge_base
  possa avançar para implementação efetiva;
- status atual de cada decisão;
- critérios formais para aprovação das ADRs 004–008;
- critérios objetivos para autorizar a próxima sprint
  (KNOWLEDGE-BASE-1);
- regras de não regressão que devem ser preservadas em qualquer cenário.

**Nada aqui equivale a aprovação.** O status default é `PROPOSED` para
toda decisão que ainda não tem registro explícito do gestor/delegatário.

---

## 2. Decisões Pendentes

### Status permitidos

| Status | Significado |
|---|---|
| `PROPOSED` | Decisão registrada como proposta; aguarda análise |
| `APPROVED` | Aprovada formalmente pelo gestor/delegatário (exige registro explícito) |
| `REJECTED` | Rejeitada com justificativa registrada |
| `DEFERRED` | Adiada para fase posterior, sem aprovação nem rejeição |
| `NEEDS_REVIEW` | Em revisão; depende de informação adicional ou consulta externa |

### Tabela de decisões

| decision_id | Decisão | Status | Impacto | Responsável sugerido | Observações |
|---|---|---|---|---|---|
| **DHP-01** | Aprovar separação `knowledge_base` / `ai_gateway` | `PROPOSED` | Arquitetural — viabiliza Fase 1 sem IA externa | Gestor / delegatário | Formaliza ADR-004 (hoje "Proposto") |
| **DHP-02** | Aprovar `knowledge_base` antes de IA externa | `PROPOSED` | Sequenciamento de fases; bloqueia IA até base madura | Gestor / delegatário | Formaliza ADR-005 |
| **DHP-03** | Aprovar política de dados permitidos e proibidos para IA | `PROPOSED` | Restringe ingestão e envio externo; protege LGPD/sigilo | Gestor + DPO | Formaliza ADR-006 |
| **DHP-04** | Aprovar exclusão de MCP e agentes autônomos nas fases iniciais | `PROPOSED` | Reduz superfície de risco; adia conectores prontos | Gestor / delegatário | Formaliza ADR-007 |
| **DHP-05** | Aprovar que saída de IA será rascunho sujeito à revisão humana | `PROPOSED` | Mantém responsabilidade no delegatário; impede uso direto de output | Gestor / delegatário | Formaliza ADR-008 |
| **DHP-06** | Aprovar lista explícita de fontes da Fase 1 | `PROPOSED` | Define o que entra na knowledge_base; controla volume e risco | Gestor + responsável pela curadoria normativa | Lista em [`PHASE_1_SOURCE_ALLOWLIST.md`](PHASE_1_SOURCE_ALLOWLIST.md); aprovação individual por linha |
| **DHP-07** | Confirmar capítulos iniciais do CNPFE-GO | `PROPOSED` | Define escopo de ingestão estadual; evita volume desnecessário | Responsável pela curadoria + jurídico | Pendência crítica para `cnpfe-go` na allowlist |
| **DHP-08** | Confirmar política contratual de uso dos documentos InovaLGPD | `PROPOSED` | Define se Matriz/Guia podem ser indexados localmente; veda envio externo | Gestor + jurídico | Material listado como `THIRD_PARTY_CONSULTING_DOC` na allowlist enquanto pendente |
| **DHP-09** | Definir responsável humano pela curadoria normativa | `PROPOSED` | Designa quem aprova promoção de fontes e revisão de chunks | Gestor / delegatário | Sem responsável designado, nenhuma fonte sai de `CANDIDATE_REQUIRES_REVIEW` |
| **DHP-10** | Definir critério objetivo para passar de KB-0.1 para KB-1 | `PROPOSED` | Evita transição ad-hoc; protege governança | Gestor / delegatário | Critérios mínimos sugeridos na Seção 4 abaixo |

> **Regra absoluta.** Nenhuma linha desta tabela deve ser marcada como
> `APPROVED` sem autorização explícita do gestor/delegatário registrada
> em mensagem direta ou ADR específica. Claude **não tem autonomia** para
> alterar o status.

---

## 3. Critérios para Aprovação das ADRs 004–008

As ADRs 004 a 008 estão atualmente em status **Proposto**. Para que a
knowledge_base possa avançar, é necessário que cada uma delas se enquadre
em **um** dos cenários abaixo:

1. **Aprovação formal:** o status na ADR passa de "Proposto" para
   "Aprovado", com data e responsável registrados.
2. **Aceitação como premissa operacional:** o gestor/delegatário declara
   formalmente que a ADR é premissa operacional do projeto, mesmo sem
   ritualização do status. Neste caso, a decisão deve ser registrada em
   `GOVERNANCE_DECISIONS.md` e/ou no [`CLAUDE.md`](../../CLAUDE.md).
3. **Substituição:** uma nova ADR substitui a original, com referência
   cruzada explícita em ambas.

Enquanto **nenhum** desses cenários se concretizar, a knowledge_base
permanece em status documental — sem código, sem ingestão, sem
implementação.

| ADR | Decisão associada | Cenário mínimo aceitável |
|---|---|---|
| [ADR-004](../decisions/ADR-004-separacao-knowledge-base-ai-gateway.md) | DHP-01 | Aprovação ou aceitação como premissa |
| [ADR-005](../decisions/ADR-005-knowledge-base-antes-de-ia-externa.md) | DHP-02 | Aprovação ou aceitação como premissa |
| [ADR-006](../decisions/ADR-006-dados-permitidos-e-proibidos-para-ia.md) | DHP-03 | Aprovação ou aceitação como premissa |
| [ADR-007](../decisions/ADR-007-mcp-e-agentes-fora-das-fases-iniciais.md) | DHP-04 | Aprovação ou aceitação como premissa |
| [ADR-008](../decisions/ADR-008-saida-de-ia-e-rascunho-sujeito-a-revisao.md) | DHP-05 | Aprovação ou aceitação como premissa |

---

## 4. Critérios para Autorizar KNOWLEDGE-BASE-1

A próxima sprint (KB-1) somente pode começar quando **todos** os itens
abaixo forem satisfeitos:

1. **Blueprint revisado** —
   [`KNOWLEDGE_BASE_BLUEPRINT.md`](KNOWLEDGE_BASE_BLUEPRINT.md) revisado
   e consistente com este documento.
2. **Allowlist criada** —
   [`PHASE_1_SOURCE_ALLOWLIST.md`](PHASE_1_SOURCE_ALLOWLIST.md) presente,
   com fontes classificadas e status atribuído por linha.
3. **Decisões de governança registradas** — DHP-01 a DHP-10 com status
   diferente de `PROPOSED` ou explicitamente aceitas como premissas no
   contexto da sprint.
4. **Fontes bloqueadas documentadas** — Seção 6 da allowlist preenchida
   e consistente com ADR-006.
5. **Política InovaLGPD definida ou marcada como restrita** — DHP-08
   resolvida ou explicitamente mantida em `CANDIDATE_REQUIRES_REVIEW`
   com `external_api_allowed=false`.
6. **ADRs 004–008 aprovadas ou aceitas como premissas** (ver Seção 3).
7. **Sem pendência crítica de confidencialidade** — nenhuma fonte na
   allowlist com risco PII `HIGH` ou `PROHIBITED` em status
   `APPROVED_FOR_PHASE_1`.

Falhar em qualquer item bloqueia KB-1. **Não cabe ao Claude decidir** a
transição: cabe ao gestor/delegatário.

---

## 5. Regras de Não Regressão

Independentemente da decisão tomada em qualquer DHP, as regras abaixo
**não podem regredir** sem ADR específica e aprovação formal:

1. **Não implementar IA externa sem base citável.** Nenhuma chamada à
   API de IA (Anthropic, OpenAI, Google, qualquer provedor) antes da
   knowledge_base estar estruturada e validada (ADR-005).
2. **Não usar dado operacional real.** Matrículas, partes, CPF, RG,
   endereços, valores e atos concretos permanecem proibidos (ADR-006).
3. **Não enviar documento interno a API externa.** Categoria
   `INTERNAL_TECHNICAL_DOC` mantém `external_api_allowed=false` por
   padrão; categoria `INTERNAL_CONFIDENTIAL_DOC` mantém
   `external_api_allowed=false` sempre.
4. **Não tratar consultoria como norma oficial.** Materiais
   `THIRD_PARTY_CONSULTING_DOC` (Matriz/Guia InovaLGPD) jamais podem ser
   apresentados como prescrição normativa.
5. **Não gerar resposta normativa sem citação específica.** Citação
   canônica autocontida obrigatória (Seção 15 do blueprint). Respostas
   genéricas ("conforme o Provimento") devem ser bloqueadas pelo
   `ai_gateway` futuro (ADR-008).
6. **Não substituir validação humana.** A IA é informativa/rascunho;
   nunca decide sobre conformidade, descarte, ato cartorário ou
   emissão de documento (ADR-008).
7. **Sem dependência cruzada com módulos de negócio.** A
   knowledge_base não importa nem é importada por `audit`, `lgpd`,
   `retention`, `compliance`, `finance`, `registro_imoveis` ou `notas`
   (ADR-002, princípio do projeto).
8. **Sem MCP, sem agentes autônomos.** Fora das fases iniciais
   (ADR-007).

---

*Sprint KNOWLEDGE-BASE-0.1 — 2026-05-25.*
*Nenhuma decisão foi aprovada automaticamente. Aguarda revisão humana
formal.*
