# ADR-007 — MCP e Agentes Autônomos Fora das Fases Iniciais

## Status

Proposto

## Contexto

O ecossistema Anthropic/Claude disponibiliza MCP Connectors prontos, suporte a
MCP Server próprio e agentes autônomos via APIs de agentes (se disponíveis conforme
documentação e contrato aplicáveis). Essas tecnologias
oferecem capacidades avançadas de integração e automação, mas apresentam riscos
significativos para um sistema com dados sensíveis e responsabilidade regulatória
como o Cartório System.

Especificamente:

- **MCP Connectors (prontos):** não são elegíveis para Zero Data Retention (ZDR);
  dados trafegados podem ser retidos pela Anthropic conforme política padrão; requerem
  servidor MCP publicamente acessível via HTTP; suportam apenas Tool Calls (sem prompts
  ou recursos MCP).
- **MCP Server próprio:** requer infraestrutura pública HTTPS, implementação de
  autenticação e autorização rigorosa, e maturidade de governança que o sistema
  ainda não possui.
- **Agentes autônomos:** executam múltiplos passos com ferramentas; risco elevado de
  ação indevida (descarte, comunicação, modificação) sem supervisão humana; rastreabilidade
  complexa; sem precedente operacional no contexto cartorário.

A questão é: devem ser incluídos nas fases iniciais ou adiados?

## Decisão

**MCP Connectors prontos, MCP Server próprio e agentes autônomos ficam fora das
Fases 1, 2 e 3 do roadmap de IA.**

A adoção futura será reavaliada somente após a satisfação de todos os pré-requisitos
abaixo:

**Para MCP Server próprio (Fase 5+):**
- `knowledge_base` operacional e validada (Fase 1 concluída).
- `ai_gateway` com logging, redaction e prompt registry (Fase 2 concluída).
- Autenticação multiusuário implementada no Cartório System.
- Infraestrutura de produção com Postgres e VM própria com HTTPS.
- Revisão de segurança do servidor MCP antes de qualquer exposição pública.
- Nenhum dado sensível acessível via MCP sem autorização explícita.

**Para agentes autônomos (Fase 6+):**
- Todos os pré-requisitos do MCP Server.
- Escopo restrito e definido: apenas consulta e narração — sem ações irreversíveis.
- Aprovação humana obrigatória em cada step crítico do agente.
- Testes exaustivos em ambiente isolado antes de qualquer uso em produção.
- Responsável técnico treinado designado.

**MCP Connectors prontos (parceiros Anthropic):**
- Não usar com dados sensíveis em nenhuma fase (não elegíveis para ZDR).
- Poderão ser avaliados apenas para sistemas externos que a serventia adotar
  no futuro (ex.: iManage, Relativity), mediante análise contratual específica.
- Quando o tema MCP for reavaliado, a decisão deve ser registrada em ADR específica.

## Consequências

### Positivas

- Elimina riscos de exposição de dados sensíveis via MCP Connector (sem ZDR).
- Previne execução automática de ações irreversíveis por agentes sem supervisão.
- Garante que a governança (logs, redaction, revisão humana) preceda a automação.
- Reduz a complexidade das fases iniciais — foco em knowledge base e AI Gateway.
- Compatível com a postura conservadora do sistema em relação a dados cartorários.

### Negativas / Trade-offs

- Conectores prontos do ecossistema jurídico (Harvey, CourtListener, iManage) não
  estarão disponíveis nas fases iniciais — mesmo que potencialmente úteis.
- O Cartório System não se beneficiará de agentes automáticos nas primeiras fases.
- A maturidade necessária para Fase 5 pode levar anos — gestão de expectativa necessária.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| Usar MCP Connector com dados normativos (sem PII) | Sem ZDR; retenção imprevisível; ganho baixo vs. risco de acoplamento |
| Implementar MCP Server local (stdio) nas fases iniciais | MCP Connector só suporta HTTP remoto; MCP Server stdio não interopera com conectores; complexidade desnecessária |
| Agente para geração de narrativas (baixo risco) desde Fase 2 | Antes da maturidade de logs e governança; rastreabilidade insuficiente |
| Avaliar MCP caso a caso sem critério formal | Sem rastreabilidade; risco de decisão inconsistente sob pressão de prazo |

## Relação com normas e governança

- LGPD (Lei 13.709/2018): MCP Connector sem ZDR cria risco de transferência
  internacional de dados sem base legal adequada.
- Provimento CNJ 213/2026: ações automáticas sobre dados de registros imobiliários
  requerem rastreabilidade e responsabilidade humana — incompatíveis com agentes
  autônomos sem governança madura.
- ADR-004 e ADR-005: o adiamento do MCP é coerente com a estratégia incremental
  de conhecimento local antes de integração externa.
- DAR-003 (AI-LEGAL-0): esta ADR formaliza a decisão proposta em DAR-003.

## Próximos passos

1. Definir quando o tema MCP será reavaliado (DHP-10) — critério de maturidade,
   não apenas data.
2. Registrar em ADR específica quando a decisão de reavaliar MCP for tomada.
3. Não iniciar nenhuma implementação de MCP ou agente sem ADR formal e aprovação
   do gestor.

---

*Proposto na Sprint AI-LEGAL-0A — 2026-05-17*
*Nenhum código foi implementado. Pendente de aprovação humana.*
