# ADR-008 — Toda Saída de IA é Rascunho Sujeito à Revisão Humana

## Status

Proposto

## Contexto

O Cartório Costa Teixeira é uma serventia extrajudicial de Registro de Imóveis.
O titular/delegatário/responsável pela serventia é pessoalmente responsável pelos
atos praticados. Essa responsabilidade funcional é intransferível — não pode ser
delegada a um sistema de IA, ao fornecedor de IA, ao desenvolvedor do sistema ou
a qualquer outra pessoa.

Modelos de linguagem como o Claude apresentam limitações conhecidas:

- **Hallucination:** citações, prazos e requisitos podem ser inventados com aparência
  de credibilidade.
- **Desatualização:** o modelo pode usar versão anterior de normativa.
- **Erro de jurisdição:** o modelo pode aplicar norma de outro Estado ou país.
- **Ausência de responsabilidade jurídica:** o fornecedor não assume responsabilidade
  pelos atos praticados com base nas respostas.

O repositório oficial `anthropics/claude-for-legal` declara explicitamente:

> "All outputs are drafts for attorney review, not legal advice."
> "The lawyer using the plugin — not the plugin and not Anthropic —
>  takes professional responsibility for the work product."

Esse princípio se aplica diretamente ao contexto cartorário.

## Decisão

**Toda saída de IA no Cartório System é classificada como informativa ou rascunho,
nunca como decisão final, parecer definitivo, declaração de conformidade ou documento
oficial.**

### Implementação obrigatória

1. **Classificação de saída:** Toda resposta de IA carrega obrigatoriamente um dos
   tipos:
   - `INFORMATIVO` — contexto geral, sem implicação operacional direta.
   - `RASCUNHO` — esboço que requer revisão humana antes de qualquer uso.
   - `REQUER_VALIDACAO_JURIDICA` — conteúdo com implicação jurídica, legal ou
     regulatória; não pode ser usado sem validação por profissional habilitado.

2. **Disclaimer estrutural obrigatório em toda saída:**
   ```
   [RASCUNHO — GERADO POR IA — REQUER REVISÃO HUMANA]
   Este conteúdo foi gerado por inteligência artificial com base em fontes normativas
   indexadas. Não constitui parecer jurídico, declaração de conformidade nem documento
   oficial. O uso externo ou operacional exige revisão e aprovação pelo responsável
   designado. O titular ou delegatário responsável pela serventia é o único responsável
   pelos atos praticados.
   ```

3. **Revisão humana registrada:** Toda saída de IA que for usada operacionalmente
   deve ter revisão humana registrada no `AiCallLog` com:
   - `human_review_required`: boolean (obrigatório sempre que `output_classification`
     for `RASCUNHO` ou `REQUER_VALIDACAO_JURIDICA`)
   - `human_review_status`: enum (`PENDENTE`, `APROVADO`, `REJEITADO`, `REESCRITO`)
   - `human_reviewed_by`: referência ao usuário revisor
   - `human_reviewed_at`: timestamp da revisão

4. **Impossibilidade técnica de bypass:** O sistema não deve oferecer caminho
   técnico para usar um output de IA classificado como `RASCUNHO` sem registrar
   uma revisão humana.

5. **Proibição de uso em documentos oficiais sem revisão:** Outputs de IA não podem
   ser copiados diretamente para atas, certidões, ofícios ou qualquer documento
   com valor jurídico sem revisão registrada.

## Consequências

### Positivas

- Protege o titular/delegatário/responsável pela serventia de responsabilidade por erros de IA.
- Garante rastreabilidade: sempre se sabe qual humano revisou cada saída usada.
- Previne confusão entre rascunho e decisão — risco crítico em contexto regulatório.
- Alinha com o princípio já estabelecido no Cartório System: "nunca declara
  conformidade automaticamente".
- Compatível com as exigências de auditoria do Provimento CNJ 213/2026.

### Negativas / Trade-offs

- Adiciona fricção ao uso de IA — toda saída exige revisão antes de uso operacional.
- Reduz a percepção de "automação" da IA nas primeiras fases.
- Requer designação formal de responsável humano pela revisão (DHP-08).

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| Permitir uso direto de saídas classificadas como `INFORMATIVO` | Risco de reclassificação informal; melhor manter a exigência consistente |
| Revisão humana apenas para saídas de alto risco | Difícil classificar risco antes da revisão; conservadorismo é mais seguro |
| Disclaimer apenas visual (sem registro em log) | Sem rastreabilidade; inviável para auditoria e conformidade |
| Responsabilidade compartilhada com o fornecedor de IA | Inviável juridicamente; Anthropic não assume responsabilidade pelos atos |

## Relação com normas e governança

- Responsabilidade funcional do delegatário: os atos praticados pelo registrador,
  titular ou delegatário responsável têm natureza pública e são de sua exclusiva
  responsabilidade (Lei 8.935/1994).
- LGPD (Lei 13.709/2018): decisões com impacto sobre titulares de dados não podem
  ser tomadas de forma exclusivamente automatizada (art. 20).
- Provimento CNJ 213/2026: rastreabilidade e auditabilidade são requisitos explícitos
  para sistemas críticos de serventias.
- ADR-001 (compliance-evidence-ownership): o princípio de que "evidências requerem
  responsabilidade humana" é extensível às saídas de IA.
- DAR-005 (AI-LEGAL-0): esta ADR formaliza a decisão proposta em DAR-005.

## Próximos passos

1. Designar responsável humano pela revisão de saídas de IA (DHP-08).
2. Implementar o modelo `AiCallLog` com campos de revisão humana (conforme ADR-004
   e requisitos da seção 15 do AI-LEGAL-0A).
3. Definir quem pode marcar uma saída como `APROVADO` — e se requer perfil
   específico (gestão, operacional, jurídico).
4. Incluir o disclaimer padrão no template de todos os prompts versionados.

---

*Proposto na Sprint AI-LEGAL-0A — 2026-05-17*
*Nenhum código foi implementado. Pendente de aprovação humana.*
