# ADR-010 — Representação de percentual e fração ideal em inventários

- **Status:** Aceito (com um ponto de redação pendente de decisão humana — ver § Consequências)
- **Data:** 2026-09-03
- **Sprint:** `NOTAS-INVENTARIO-FRACOES-1`
- **Módulo:** `app/modules/notas/inventarios/`
- **Relacionada a:** [ADR-009](ADR-009-inventory-cent-rounding-policy.md) — que permanece **intacta**

---

## Contexto

O módulo `notas/inventarios` tem evidência **V4** de valor operacional: seis casos
reais entre 2026-05-23 e 2026-08-29. O
[rebaseline estratégico](../reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md)
(§ 12.4) demonstrou, porém, um defeito de **representação** — não de cálculo.

**A aritmética sempre esteve correta.** `InventarioCalculator` opera
inteiramente em `Decimal` com `ROUND_HALF_EVEN`, e os percentuais nunca são
calculados: vêm da entrada estruturada e são copiados sem transformação de
`Distribuicao.percentual` para `QuinhaoBem.percentual`.

O problema estava no formatador. Um único `f"{value:.2f}"` — o mesmo usado para
dinheiro — era aplicado também a percentuais:

| Valor no domínio | Apresentado antes | Perda |
|---|---|---|
| `Decimal("3.125")` | `3,12%` | milésimo suprimido |
| `Decimal("0.005")` | `0,00%` | participação desaparece |
| `Decimal("0.0001")` | `0,00%` | participação desaparece |

A consequência é verificável: num cenário de meeira mais nove herdeiros, os
percentuais **exibidos** somavam `100,04%` enquanto o cálculo interno
permanecia exato. Um documento cartorário não pode exibir percentuais que não
fecham.

**O caso real de 2026-07-09** materializou isso. Um inventário de veículo com
quinhões de 1/16 e 1/32 precisou sair do fluxo automatizado e ser redigido
manualmente, precisamente porque o gerador não preservava `3,125%` nem grafava a
fração ideal. O relatório técnico daquele caso registrou a limitação e propôs
esta sprint.

---

## Decisão

### 1. A aritmética não muda

Cálculo monetário, `ROUND_HALF_EVEN`, `DECIMAL_TOLERANCIA` e a política de
resíduo de centavos da **ADR-009 permanecem exatamente como estão**. Esta ADR
trata de representação. A única alteração no `InventarioCalculator` é o repasse
literal do novo metadado de `Distribuicao` para `QuinhaoBem`, sem participação
em qualquer conta.

### 2. Percentual e dinheiro passam a ter contratos de precisão distintos

Deixa de existir um formatador único. A camada autoritativa
`application/formatting.py` separa quatro contratos:

| Contrato | Função | Precisão |
|---|---|---|
| Dinheiro, leitura humana | `formatar_monetario` | sempre 2 casas |
| Dinheiro, JSON | `serializar_monetario` | sempre 2 casas |
| Percentual, leitura humana | `formatar_percentual` | variável (regra abaixo) |
| Percentual, JSON | `serializar_percentual` | variável (mesma regra) |

### 3. Regra de precisão do percentual

A precisão é **derivada da própria entrada**, não arbitrada:

- parte-se do expoente do `Decimal` — a precisão que o arquivo de entrada
  efetivamente declara;
- zeros à direita são descartados, para que `12.500` e `12.5` produzam o mesmo
  texto;
- nunca se desce abaixo de **2 casas**, preservando o padrão consolidado do
  documento.

Não há teto arbitrário, e não é preciso haver: **todo percentual do módulo vem
da entrada; nenhum é calculado.** Não existe dízima a truncar.

Efeito prático — muda **apenas** onde havia perda real:

| Entrada | Antes | Depois |
|---|---|---|
| `50` | `50,00%` | `50,00%` (inalterado) |
| `12.5` | `12,50%` | `12,50%` (inalterado) |
| `33.33` | `33,33%` | `33,33%` (inalterado) |
| `6.25` | `6,25%` | `6,25%` (inalterado) |
| **`3.125`** | `3,12%` | **`3,125%`** |
| **`0.005`** | `0,00%` | **`0,005%`** |

Nunca é emitida notação científica.

### 4. A fração ideal é opcional e **jamais inferida**

Este é o ponto de segurança central desta ADR.

O sistema **não conclui** que `3,125%` equivale a `1/32`, nem deriva fração de
qualquer relação sucessória — representação, estirpe, substituição, pré-morte ou
meio quinhão. A fração só existe quando **explicitamente fornecida na entrada**.

A finalidade da fração aqui é **representação documental, não interpretação
jurídica**. Ela é uma segunda grafia de uma participação que o percentual já
descreve — nunca informação nova, nunca insumo de cálculo.

### 5. A fração pertence à entidade mais estreita

`fracao_ideal` fica em `Distribuicao` — a entidade que já é dona do percentual
da participação — e é repassada a `QuinhaoBem`. **Não** é duplicada em
`Herdeiro`, `Bem` ou `Inventario`.

### 6. A fração fornecida é validada

Formato estrito `numerador/denominador`, com inteiros positivos, via
`fractions.Fraction` da biblioteca padrão — sem nova dependência. São recusados:
denominador zero, valores negativos, zero, decimais (`0.5`), notação científica
e texto arbitrário. O parser é deliberadamente **mais estrito que `Fraction`**,
que aceitaria várias dessas formas silenciosamente.

**Forma canônica simplificada:** `2/64` é normalizado para `1/32`. Isso é
consequência do próprio tipo `Fraction`, que normaliza na construção.

### 7. Coerência fração × percentual, com tolerância derivada

Uma fração incompatível com o percentual declarado é **recusada pelo validador**.

A comparação não pode exigir igualdade textual de `Decimal`: frações como `1/3`
têm expansão decimal infinita, e o percentual escrito na entrada é
necessariamente arredondado. A tolerância é derivada da entrada, não arbitrada:

> **meia unidade da última casa decimal do percentual informado.**

Quem escreve `33.33` declara um valor arredondado à segunda casa, cujo maior
erro legítimo é `0,005`. Para `3.125` (três casas), a tolerância cai para
`0,0005`.

| Fração | Percentual | Tolerância | Resultado |
|---|---|---|---|
| `1/2` | `50` | 0,005 | válido |
| `1/32` | `3.125` | 0,0005 | válido |
| `1/3` | `33.33` | 0,005 | válido (erro 0,00333) |
| `1/3` | `33.34` | 0,005 | **recusado** (erro 0,00666 — não é o arredondamento correto) |
| `1/2` | `40` | 0,005 | **recusado** |

A tolerância monetária `DECIMAL_TOLERANCIA` **não** é reutilizada: os domínios
são distintos — um mede centavos de patrimônio, o outro mede arredondamento de
percentual.

### 8. Onde a fração é exibida — e onde não é

Esta decisão decorre de **evidência**, não de preferência.

A análise dos artefatos sanitizados do caso de 2026-07-09 mostrou que a
serventia usou a fração **apenas nos documentos técnicos internos** (o relatório
de análise e o mapa de partilha, que tem uma coluna "Fração ideal"). No **texto
da escritura** — a minuta manualmente redigida e o texto limpo destinado ao
Engegraph — há **zero ocorrências** de notação fracionária. A redação aprovada
usa percentual:

```
3,125% (três inteiros e cento e vinte e cinco milésimos por cento) do veículo
descrito e caracterizado no item 7.1, ...
```

Portanto:

| Artefato | Fração ideal | Justificativa |
|---|---|---|
| JSON de validação | **exibida** | artefato técnico; risco jurídico nulo |
| Resumo técnico (Markdown) | **exibida** em coluna própria | espelha o mapa de partilha da própria serventia |
| **Minuta (escritura)** | **NÃO exibida** | **não existe redação aprovada** — ver Consequências |
| ODT | herda a minuta | derivado do Markdown |

---

## Consequências

### Positivas

- O caso que forçou rota manual em 2026-07-09 passa a ser representável pelo
  fluxo automatizado quanto à precisão percentual.
- Percentuais exibidos voltam a fechar em 100% em cenários fracionários.
- O JSON de validação deixa de perder precisão, tornando-se conferível.
- Dinheiro e percentual passam a ter contratos explícitos e separados, o que
  impede que uma mudança em um afete o outro por acidente.

### Compatibilidade

**Os seis golden files anteriores permanecem byte a byte idênticos.** O piso de
2 casas garante que nenhum caso comum mude de redação. Um sétimo conjunto de
goldens foi criado para o cenário fracionário, em vez de alterar os existentes.

O campo `fracao_ideal` é omitido do JSON quando ausente — que é o caso comum —
preservando o formato histórico do artefato.

### 🔴 Decisão humana pendente — redação da fração na minuta

**A infraestrutura de fração está completa e testada, mas a minuta não a exibe.**

O motivo é o princípio de não inventar redação cartorária: o caso sanitizado de
2026-07-09 **não permite determinar** como a fração deveria aparecer no texto da
escritura, porque naquele caso ela simplesmente não apareceu — a serventia
redigiu por percentual.

Enquanto essa decisão não for tomada pelo tabelião, a fração permanece
disponível nos artefatos técnicos e ausente do documento cartorário. Alterar
isso exige:

1. definição, pela serventia, da redação exata (por exemplo, se a fração
   acompanha o percentual entre parênteses, se substitui o percentual, ou se
   aparece em cláusula própria);
2. nova ADR ou aditamento a esta;
3. regeneração do golden do caso fracionário.

### Observação registrada, fora do escopo desta ADR

A minuta manual de 2026-07-09 também grafa o percentual **por extenso** —
`3,125% (três inteiros e cento e vinte e cinco milésimos por cento)`. O gerador
não produz essa forma. É uma lacuna de redação distinta da tratada aqui,
registrada para avaliação futura; implementá-la agora seria expandir o escopo
desta sprint.

---

## Alternativas consideradas

| Alternativa | Por que foi descartada |
|---|---|
| Fixar percentual em 6 casas | Número arbitrário; produziria `50,000000%` em todos os casos comuns e quebraria os seis goldens sem ganho |
| Inferir a fração a partir do percentual | Viola o princípio de segurança: `3,125%` poderia ser `1/32`, mas afirmá-lo é interpretação jurídica que o sistema não deve fazer |
| Guardar a fração em `Herdeiro` | O percentual da participação pertence a `Distribuicao`; duplicar criaria duas fontes de verdade |
| Reutilizar `DECIMAL_TOLERANCIA` na comparação fração × percentual | Domínios distintos — centavos de patrimônio × arredondamento de percentual |
| Exibir a fração na minuta com redação inventada | Vedado: nenhuma redação aprovada pôde ser identificada nos artefatos sanitizados |

---

## Referências

- [`docs/modules/notas_inventarios.md`](../modules/notas_inventarios.md)
- [`ADR-009`](ADR-009-inventory-cent-rounding-policy.md) — política de centavos, intacta
- [`app/modules/notas/inventarios/application/formatting.py`](../../app/modules/notas/inventarios/application/formatting.py)
- [`docs/reports/RELATORIO_NOTAS_INVENTARIO_FRACOES_1.md`](../reports/RELATORIO_NOTAS_INVENTARIO_FRACOES_1.md)
- Rebaseline estratégico § 12.4 — demonstração quantificada da perda de precisão
