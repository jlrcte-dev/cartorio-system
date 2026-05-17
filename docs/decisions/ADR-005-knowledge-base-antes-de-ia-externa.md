# ADR-005 — Knowledge Base Normativa Precede Qualquer IA Externa

## Status

Proposto

## Contexto

O Cartório System está avaliando a adoção futura de IA para suporte normativo.
A decisão sobre a ordem de implementação das fases tem impacto direto no risco
regulatório, na qualidade das respostas e na governança do sistema.

Existe a possibilidade de pular a Fase 1 (knowledge base sem IA) e ir diretamente
para chamadas à API da Anthropic — o que reduziria o tempo até a primeira funcionalidade
de IA, mas criaria riscos técnicos e regulatórios significativos:

- Sem base normativa estruturada, o RAG futuro não terá fonte confiável.
- Sem classificação de dados, o risco de envio de dados inadequados à API é real.
- Sem critérios de governança validados, não há como garantir que apenas dados
  autorizados sejam enviados.

## Decisão

A primeira fase técnica de implementação deve ser `knowledge_base` **sem IA** —
exclusivamente com organização, indexação e busca local de fontes normativas aprovadas.

Chamadas reais à API de IA (Anthropic ou qualquer outro provedor) somente poderão
ser avaliadas e implementadas **depois** que todos os itens abaixo estiverem concluídos:

1. Base normativa local estruturada e validada (`knowledge_base` operacional).
2. Classificação de dados definida formalmente (quais documentos podem ir para API).
3. Política sobre documentos InovaLGPD confirmada (restrição contratual analisada).
4. Critérios de governança de IA documentados e aprovados pelo gestor.
5. Pipeline de redaction implementado e testado no `ai_gateway`.
6. Modelo `AiCallLog` implementado com campos mínimos conforme AI-LEGAL-0A.
7. Feature flag `AI_GATEWAY_ENABLED=false` implementada e testada.
8. Modo dry-run funcional com mocks verificáveis.

## Consequências

### Positivas

- Reduz risco de exposição prematura de dados a APIs externas.
- Cria fonte controlada e versionada para o RAG futuro — melhora qualidade.
- Permite validação humana da base antes de qualquer IA gerar resposta com base nela.
- Evita dependência prematura de fornecedor externo de IA.
- A base normativa tem valor independente da IA — já melhora a organização interna.
- Compatível com as fases de maturidade do AI Gateway (ver AI-LEGAL-0).

### Negativas / Trade-offs

- O gestor não verá funcionalidade de IA nas primeiras sprints — apenas organização
  normativa e busca local.
- Requer disciplina para não pular fases sob pressão de prazo.
- Pode gerar percepção de lentidão no avanço da camada de IA.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| Implementar AI Gateway diretamente na Fase 1 | Sem base normativa estruturada; sem classificação de dados; risco de LGPD |
| Usar Claude.ai manualmente (sem sistema) enquanto espera | Aceitável como paliativo temporário; não substitui governança |
| RAG com embeddings direto na Fase 1 | Alta complexidade sem base de dados validada; risco de qualidade e custo |
| Contratar plano Enterprise e ir para API imediatamente | Custo prematuro; governança e base ainda inexistentes |

## Relação com normas e governança

- LGPD (Lei 13.709/2018): a Fase 1 sem IA elimina o risco de transferência
  internacional de dados pessoais enquanto a governança não estiver madura.
- Provimento CNJ 213/2026: a base normativa estruturada é elemento essencial de
  rastreabilidade e conformidade antes de qualquer automação.
- ADR-004: esta decisão depende e complementa a separação entre `knowledge_base`
  e `ai_gateway` estabelecida em ADR-004.
- DAR-002 (AI-LEGAL-0): esta ADR formaliza a decisão proposta em DAR-002.

## Próximos passos

1. Aprovação humana (DHP-01 e DHP-02): gestor confirma a ordem das fases.
2. Definir quais documentos entram na base normativa (DHP-03 e DHP-06).
3. Iniciar Sprint Knowledge-Base-0 (mapeamento documental, sem código).
4. Após Fase 1 validada, abrir discussão sobre Sprint AI-Gateway-0.

---

*Proposto na Sprint AI-LEGAL-0A — 2026-05-17*
*Nenhum código foi implementado. Pendente de aprovação humana.*
