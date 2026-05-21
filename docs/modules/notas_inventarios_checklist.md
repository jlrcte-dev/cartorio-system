# Checklist operacional — Conferência da minuta-base de inventário

> Documento de uso interno do Tabelionato de Notas — Cartório Costa Teixeira.
> Acompanha o módulo [`notas/inventarios`](notas_inventarios.md) e o
> [ADR-009 — Política de centavos](../decisions/ADR-009-inventory-cent-rounding-policy.md).
>
> **Propósito:** orientar a revisão da minuta-base (`inventario_minuta.md`,
> gerada pela CLI com `--render-minuta`) antes de ser levada ao Engegraph para
> qualificação completa das partes e antes da lavratura.

A minuta gerada pelo Cartório System é um **rascunho** — contém apenas
placeholders e cálculos determinísticos. Nenhum item deste checklist é
substituível por automação; cada linha exige conferência humana.

---

## 1. Identidade do ato

- [ ] Tipo do ato confere com `tipo_ato: inventario_extrajudicial` (único
  caso suportado no MVP — múltiplos falecidos, sobrepartilha, renúncia,
  cessão e adjudicação integral ficam fora desta sprint).
- [ ] Cidade, comarca, UF e tabeliã preenchidos no preâmbulo.
- [ ] Data e hora da lavratura confirmadas.

## 2. Autor da herança (§ 2)

- [ ] Nome civil completo do autor da herança, sem abreviaturas.
- [ ] Nacionalidade, profissão.
- [ ] Data e local de nascimento.
- [ ] Filiação (pai e mãe).
- [ ] RG (com órgão emissor e UF) e CPF.
- [ ] Estado civil ao tempo do óbito.
- [ ] Regime de bens — coerente com a flag `possui_meeiro` e com o valor de
  `percentual_meacao`.

## 3. Falecimento (§ 3)

- [ ] Data e hora do óbito.
- [ ] Cidade/UF onde ocorreu o falecimento.
- [ ] Idade do falecido.
- [ ] Certidão de óbito: RCPN (Cartório de Registro Civil das Pessoas
  Naturais), livro, folhas, termo, data da lavratura.

## 4. Testamento (§ 4)

- [ ] Consulta CENSEC apresentada e arquivada (Provimento CNJ 56/2016).
- [ ] Data de emissão da Consulta CENSEC preenchida em `[CENSEC_DATA]`.
- [ ] Resultado da consulta: "NÃO CONSTA". Se constar testamento, **o ato é
  judicial** e este fluxo não se aplica — interromper a lavratura.

## 5. Meeiro(a) (quando aplicável, § 1.2 e § 10.1)

- [ ] Regime de bens compatível com a existência de meeiro (comunhão
  parcial, comunhão universal, ou outro regime que admita meação).
- [ ] Qualificação completa do(a) meeiro(a).
- [ ] Percentual da meação (`percentual_meacao`) confere com o regime de
  bens (50% para comunhão parcial padrão).
- [ ] Valor da meação calculado bate com `patrimônio × percentual_meacao / 100`.

## 6. Herdeiros (§ 1.1 e § 5)

- [ ] Vocação hereditária validada manualmente: descendentes vs.
  ascendentes vs. cônjuge concorrente (vocação automática **não** é
  responsabilidade do sistema).
- [ ] Cada herdeiro: nome civil completo, nacionalidade, estado civil,
  profissão, RG, CPF, endereço.
- [ ] Quantidade de herdeiros conferida (preâmbulo § 5 — "X (extenso)").
- [ ] Percentuais de herança somam **exatamente** 100,00% (tolerância
  ±0,01).
- [ ] Inventariante nomeado em § 6 está entre os herdeiros listados.
- [ ] Declaração PEP (Resolução COAF nº 29/2017) — confirmar que **nenhum**
  herdeiro é pessoa politicamente exposta; se for, ajustar a redação.

## 7. Bens, direitos e valores (§ 7 e § 10)

Para cada bem listado em § 7:

- [ ] `id` local (ex.: `IMOVEL_1`, `SALDO_1`) coerente entre §§ 7, 10, 11.
- [ ] Tipo do bem (`imovel`, `veiculo`, `dinheiro`, `direito`, `outro`).
- [ ] Descrição genérica preenchida com dados verificáveis (sem PII no
  exemplo, mas com matrícula, placa, conta bancária, etc. na minuta final).
- [ ] Valor avaliado em **Decimal**, conferido com avaliação da repartição
  pública competente (SEFAZ ou Prefeitura).
- [ ] Para imóveis: matrícula, RI, Comarca, UF, Certidão de Inteiro Teor
  (data), selo digital, título aquisitivo (DA PROCEDÊNCIA DA AQUISIÇÃO).
- [ ] Para bens não-imóveis: identificação específica (instituição
  financeira, placa, número de registro, contrato).
- [ ] Soma `Σ bens.valor == patrimonio_total` (tolerância ±0,01).
- [ ] Patrimônio total, meação e monte partilhável conferidos.
- [ ] Quinhão hereditário de cada herdeiro conferido.

## 8. Partilha (§ 11)

A minuta cartorária emite o § 11 **apenas em alíneas** (a, b, c…) por
beneficiário, preservando o modelo padrão da serventia. Para conferência
numérica, usar o resumo técnico (`inventario_resumo.md`) e o JSON de
validação (`inventario_validacao.json`) — esses sim contêm quadros tabulares.

Para cada bem partilhado:

- [ ] Soma dos percentuais de distribuição = 100,00% (tolerância ±0,01).
- [ ] Cada beneficiário pertence a `{MEEIRO} ∪ {ids dos herdeiros}`.
- [ ] Valor distribuído por beneficiário = `bem.valor × percentual / 100`.
- [ ] As alíneas da minuta refletem a mesma distribuição dos quadros do
  resumo técnico (conferir bem a bem).
- [ ] Se `possui_meeiro = false`, nenhum bem pode ter `MEEIRO` como
  beneficiário (nem subitem 11.1 de meeiro, nem assinatura de meeiro).

## 9. Débitos e obrigações (§§ 8 e 9)

- [ ] Confirmar com os herdeiros se há débitos do *de cujus*. Em caso
  afirmativo, **substituir** o parágrafo padrão de inexistência por
  descrição detalhada (credor, valor, vencimento) e abater do monte
  partilhável antes da assinatura.
- [ ] Idem para outras obrigações (§ 9).

## 10. Certidões (§ 12)

- [ ] Certidão Negativa de Débitos Inscritos em Dívida Ativa.
- [ ] Certidão Negativa de Débitos Trabalhistas (CNDT).
- [ ] Certidão Negativa de Ações Cíveis.
- [ ] Certidão Negativa de Débitos Relativos aos Tributos Federais e à
  Dívida Ativa da União.
- [ ] Todas em nome do autor da herança e dentro do prazo de validade.

## 11. CNIB (§ 13)

- [ ] Consulta realizada em nome do autor da herança.
- [ ] CPF/CNPJ correto.
- [ ] Código HASH, data, hora e status preenchidos.
- [ ] Se `STATUS ≠ NEGATIVO / NADA CONSTA`, **avaliar** se a partilha pode
  prosseguir — escalar para o tabelião.

## 12. ITCMD (§§ 16 e 19)

- [ ] Demonstrativo de Cálculo do ITCD Causa Mortis (número da guia
  SPL) emitido pela Secretaria de Estado da Economia.
- [ ] Guia paga (ou isenção declarada conforme legislação estadual).
- [ ] Data da última alteração da guia confere com a apresentação.
- [ ] Valores da guia consistentes com os cálculos do sistema.

## 13. Advogado (§§ 1.N e 15)

- [ ] Qualificação completa do advogado (nome, OAB/UF, endereço).
- [ ] Procuração ou poderes verificados.
- [ ] Declaração do advogado (§ 15) confere com a participação efetiva.

## 14. LGPD, declarações finais e únicos herdeiros (§§ 17, 18, 19, 20)

- [ ] Texto da cláusula de tratamento de dados (LGPD, Lei 13.709/2018;
  Provimento CNJ 134/2022; CNPFE/2023 TJ-GO) preservado integralmente.
- [ ] Texto do artigo 3º da Resolução nº 35 do CNJ (§ 18) preservado.
- [ ] Declaração de únicos herdeiros (§ 19, artigo 21 da Resolução nº 35
  do CNJ).
- [ ] Declaração de ausência de união estável (§ 19, artigo 1.725 do
  Código Civil).

## 15. Alerta técnico de centavos (ADR-009)

Se a minuta contiver a seção "⚠ AVISO TÉCNICO — DIVERGÊNCIA DE CENTAVOS":

- [ ] Verificar o valor `divergencia_centavos` no
  `inventario_validacao.json`.
- [ ] Revisar a partilha bem a bem.
- [ ] **Não corrigir centavos silenciosamente**. Conforme
  [ADR-009](../decisions/ADR-009-inventory-cent-rounding-policy.md),
  decidir caso a caso: reescrever a distribuição manualmente, alertar o
  herdeiro afetado ou aceitar o resíduo declarado.

## 16. Placeholders pendentes

- [ ] Nenhum `[QUALIFICAÇÃO DO …]` permanece na versão final.
- [ ] Nenhum `[DATA_LAVRATURA]`, `[CIDADE_SERVENTIA]`, `[COMARCA]`,
  `[UF]`, `[CENSEC_DATA]`, `[CNIB_*]`, `[ITCMD_*]`, `[MATRÍCULA …]`,
  `[PROCEDÊNCIA …]`, `[EMOLUMENTOS]`, `[TAXA_JUDICIARIA]` permanece na
  versão final.
- [ ] Nenhum trecho de comentário interno da minuta-base (avisos
  introdutórios em blockquote, "preencher pelo Engegraph", "Esta
  minuta-base NÃO calcula débitos") permanece na versão final assinada.

## 17. Encerramento e assinaturas

- [ ] Texto "E por se acharem assim contratados…" preservado.
- [ ] Emolumentos e Taxa Judiciária preenchidos.
- [ ] Espaços de assinatura presentes: herdeiros, meeiro(a) (se houver),
  advogado(a) e tabeliã.

## 18. Aprovação final

- [ ] Revisão de qualificações pelo Engegraph.
- [ ] Conferência de valores e cálculos.
- [ ] Validação fiscal (ITCMD / DOI).
- [ ] Remoção de todos os placeholders.
- [ ] Aprovação final do(a) tabelião(ã) responsável — **única assinatura
  que valida a versão final**.

---

## Anexo — Pontos NÃO contemplados nesta sprint

Os itens abaixo **não** são gerados nem calculados pelo módulo atual.
Continuam responsabilidade manual do tabelião / do Engegraph:

- Múltiplos falecidos (ex.: casal falecido em sucessões simultâneas).
- Renúncia ou cessão de direitos hereditários.
- Sobrepartilha.
- Testamento complexo (registro com testamento exige judicialização).
- Adjudicação integral por um único herdeiro.
- Distribuição por valor absoluto (atualmente só percentual).
- Variação por regime de bens (somente comunhão parcial padrão é tratada
  via `percentual_meacao`).
- Cálculo de débitos do autor da herança.
- Exportação para `.docx` ou `.odt` (esta sprint encerra na renderização
  Markdown).
