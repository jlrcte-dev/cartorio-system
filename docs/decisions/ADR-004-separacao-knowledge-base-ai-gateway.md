# ADR-004 — Separação entre Knowledge Base e AI Gateway

## Status

Proposto

## Contexto

A investigação AI-LEGAL-0 identificou que o Cartório System precisará, no futuro,
de dois componentes distintos para suportar inteligência normativa com governança:

1. Uma **base de conhecimento normativo** (`knowledge_base`) — organização, indexação
   e busca local de fontes normativas sem chamadas externas de IA.
2. Um **gateway de chamadas de IA** (`ai_gateway`) — camada de controle para chamadas
   à API da Anthropic, com redaction, prompts versionados, logs de auditoria e revisão
   humana obrigatória.

A decisão de separar ou unificar esses componentes afeta a arquitetura modular do
sistema, a independência das fases de implementação e a rastreabilidade regulatória.

## Decisão

Criar, futuramente, dois módulos distintos:

- `app/modules/knowledge_base/` — responsabilidade única: organização, indexação e
  busca local de fontes normativas. Opera sem IA em Fase 1. Em Fase 4, fornece
  contexto para o AI Gateway via RAG.
- `app/modules/ai_gateway/` — responsabilidade única: controle de chamadas de IA,
  redaction, prompt registry versionado, log auditável (`AiCallLog`), disclaimers
  e classificação de saídas.

Os dois módulos seguem o mesmo princípio de referência fraca já adotado no projeto:
comunicam-se por interfaces explícitas, sem FK cruzada e sem dependência de banco
compartilhado.

## Consequências

### Positivas

- Separação de responsabilidades clara: a base normativa pode ser desenvolvida,
  testada e validada sem nenhuma chamada de IA.
- Permite iniciar com Fase 1 (knowledge_base sem IA) antes de qualquer exposição
  de dados a APIs externas.
- Facilita auditoria: o `ai_gateway` é o único ponto de saída de dados para a
  Anthropic API — centralizando controles de redaction e logging.
- Reduz risco regulatório: o `knowledge_base` pode ser revisado e aprovado
  independentemente antes de qualquer decisão sobre uso de IA externa.
- Compatível com a arquitetura modular existente (finance, audit, compliance, lgpd,
  retention) — adiciona dois módulos sem modificar os existentes.
- Permite substituição futura do AI Gateway por outro provedor sem afetar a base
  normativa.

### Negativas / Trade-offs

- Maior superfície de código inicial em comparação a um módulo único.
- Requer definição clara de contrato de interface entre os dois módulos antes da
  implementação do RAG (Fase 4).
- Dois módulos para manter, documentar e testar.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| Módulo único `ai_intelligence/` | Mistura responsabilidades; impede Fase 1 sem IA; dificulta auditoria |
| `normative_intelligence/` unificado | Semanticamente ambíguo; acoplamento entre busca local e chamadas externas |
| Knowledge base como subpasta do `ai_gateway` | Impede uso independente da base; cria dependência prematura de IA |
| Nenhum módulo dedicado (RAG ad-hoc) | Sem rastreabilidade; sem controle de dados; inviável para contexto regulatório |

## Relação com normas e governança

- Provimento CNJ 213/2026: exige rastreabilidade e auditabilidade de sistemas críticos.
- LGPD (Lei 13.709/2018): o `ai_gateway` como ponto único de saída facilita controle
  de quais dados pessoais podem ser enviados externamente.
- ADR-001 e ADR-002: a separação respeita o princípio de módulos independentes com
  referências fracas já estabelecido no projeto.
- DAR-001 (AI-LEGAL-0): esta ADR formaliza a decisão proposta em DAR-001.

## Próximos passos

1. Aprovação humana (DHP-01): gestor deve aprovar ou rejeitar a criação dos módulos.
2. Se aprovado: criar Sprint Knowledge-Base-0 (mapeamento de documentos, sem código).
3. Definir contrato de interface entre `knowledge_base` e `ai_gateway` antes de Fase 4.
4. Cada módulo terá sua própria ADR de implementação quando a sprint correspondente
   for iniciada.

---

*Proposto na Sprint AI-LEGAL-0A — 2026-05-17*
*Nenhum código foi implementado. Pendente de aprovação humana.*
