# Relatório — Precisão percentual e fração ideal em inventários

> Sprint **NOTAS-INVENTARIO-FRACOES-1** — executada em **2026-09-03**.
> Módulo: `app/modules/notas/inventarios/` (evidência V4 de valor operacional).
> Decisão registrada em
> [ADR-010](../decisions/ADR-010-inventory-fraction-percentage-rendering.md).
> **A ADR-009 permanece intacta.** Nenhuma regra sucessória, cálculo monetário,
> API, banco ou migration foi alterado.

---

## 1. Veredito

```
NOTAS_INVENTARIO_FRACTIONS_IMPLEMENTED_WITH_REVIEW_REQUIRED
```

Os três objetivos técnicos do § 1 do escopo foram atingidos e comprovados:
precisão percentual variável, fração ideal opcional com validação, e preservação
da precisão no artefato de validação.

O sufixo `WITH_REVIEW_REQUIRED` **não** indica trabalho incompleto — indica um
ponto que o próprio escopo mandou não decidir sozinho. O § 5 determinava usar a
redação comprovada pelo caso sanitizado de 2026-07-09 e, **não sendo possível
identificá-la de forma inequívoca**, implementar a infraestrutura, deixar o
renderer atrás de contrato explícito e reportar a decisão humana.

Foi exatamente o que ocorreu, e por um motivo verificável: **o texto da escritura
daquele caso não contém uma única ocorrência de notação fracionária.** A
serventia redigiu por percentual; as frações vivem apenas nos documentos técnicos
internos. Não havendo redação aprovada, o gerador não inventa uma.

| Objetivo do § 1 | Resultado |
|---|---|
| Percentuais com mais de duas casas | 🟢 `3,125%` preservado na minuta, no resumo e no ODT |
| Fração ideal opcional | 🟢 aceita, validada, normalizada e exibida nos artefatos técnicos |
| Precisão percentual no JSON | 🟢 `"3.125"` preservado; dinheiro segue em 2 casas |
| Redação da fração na minuta | 🔴 **decisão humana pendente** — sem redação aprovada |

---

## 2. Baseline Git

Verificado antes de qualquer alteração, conforme o § 3 — não presumido.

| Item | Valor |
|---|---|
| Branch | `main` |
| HEAD | `a06f2bbaf878c26c4aa938329a22f8d0d66fb81b` |
| `origin/main` | `a06f2bbaf878c26c4aa938329a22f8d0d66fb81b` |
| Ahead / behind | **0 / 0** — sincronizado |
| Working tree | **limpo** |

Gates na entrada, todos verdes:

```
ruff format --check .  ->  147 files already formatted
ruff check .           ->  All checks passed!
pytest -q              ->  903 passed, 1 skipped
alembic heads          ->  f4a5b6c7d8e9 (head)
alembic check          ->  No new upgrade operations detected.
```

O estado herdado conferiu integralmente com o esperado. Não havia alteração
pré-existente a proteger.

---

## 3. O problema reproduzido antes da mudança

A aritmética sempre esteve correta. O defeito era de **representação**: um único
`f"{value:.2f}"` — o mesmo formatador do dinheiro — era aplicado também aos
percentuais.

Reprodução executada no baseline:

| Valor no domínio | Apresentado | Perda |
|---|---|---|
| `Decimal("3.125")` | `3,12%` | milésimo suprimido |
| `Decimal("0.005")` | `0,00%` | participação desaparece |
| `Decimal("0.0001")` | `0,00%` | participação desaparece |

O sintoma agregado, medido no rebaseline estratégico (§ 12.4): num cenário de
meeira mais nove herdeiros, os percentuais **exibidos** somavam `100,04%`
enquanto o cálculo interno permanecia exato.

Consequência operacional documentada: o inventário de veículo de **2026-07-09**,
com quinhões de 1/16 e 1/32, saiu do fluxo automatizado e foi redigido à mão.

---

## 4. Mapa dos pontos de perda de precisão

Levantado antes de escrever qualquer código, conforme o § 4.

### 4.1. Conversões de percentual para texto

| Arquivo | Linha | Contexto |
|---|---|---|
| `application/renderer.py` | 52 | `_fmt_pct` — `f"{value:.2f}%"` |
| `application/renderer.py` | 80 | resumo § 2 — percentual de meação |
| `application/renderer.py` | 93 | resumo § 3 — % de herança por herdeiro |
| `application/renderer.py` | 110 | resumo § 4 — % por beneficiário e bem |
| `application/renderer.py` | 402 | minuta § 10.1 — meação |
| `application/renderer.py` | 420 | minuta § 10.2.x — quinhão hereditário |
| `application/renderer.py` | **771** | minuta § 11 — alíneas por bem ← **ponto do caso real** |
| `interfaces/cli.py` | 223 | JSON — `"percentual"` via `_decimal_str` |
| `interfaces/cli.py` | 236 | `_decimal_str` — `f"{value:.2f}"`, usado para dinheiro **e** percentual |

**Causa-raiz:** `_decimal_str` e `_fmt_pct` aplicavam a regra do dinheiro ao
percentual. Um único formatador para dois domínios com contratos distintos.

### 4.2. Entidades que possuem percentual

| Entidade | Campo | Papel |
|---|---|---|
| `Distribuicao` | `percentual` | **dono da participação por bem** — entidade mais estreita |
| `QuinhaoBem` | `percentual` | saída, copiada de `Distribuicao` sem aritmética |
| `Herdeiro` | `percentual_heranca` | percentual do monte |
| `Inventario` | `percentual_meacao` | percentual da meação |

Conclusão que orientou o desenho: **nenhum percentual é calculado.** Todos vêm da
entrada; o `calculator` copia `d.percentual` para `QuinhaoBem.percentual`. Isso é
o que torna possível derivar a precisão da entrada sem teto arbitrário.

### 4.3. Demais superfícies

- **ODT:** converte o Markdown já renderizado — herda a correção sem alteração.
- **Golden files:** 6 arquivos, todos com percentuais de no máximo 2 casas.

---

## 5. Decisão da ADR-010

Registrada em
[`ADR-010`](../decisions/ADR-010-inventory-fraction-percentage-rendering.md).
Pontos centrais:

1. **A aritmética não muda.** ADR-009, `ROUND_HALF_EVEN` e `DECIMAL_TOLERANCIA`
   permanecem como estão.
2. **Percentual e dinheiro passam a ter contratos separados**, em uma camada
   autoritativa única (`application/formatting.py`), com quatro funções de nome
   semanticamente explícito.
3. **Precisão derivada da entrada**, com piso de 2 casas e sem teto arbitrário.
4. **A fração nunca é inferida.** `3,125%` não vira `1/32` sozinho; nenhuma
   hipótese sucessória é deduzida.
5. **A fração pertence a `Distribuicao`** — a entidade mais estreita —, não é
   duplicada em `Herdeiro`, `Bem` ou `Inventario`.
6. **A fração é validada** com parser estrito e normalizada à forma canônica.
7. **Coerência fração × percentual** com tolerância derivada.
8. **A fração não aparece na minuta** por ausência de redação aprovada.

---

## 6. Contrato da fração ideal

### 6.1. Onde vive

```python
@dataclass(frozen=True)
class Distribuicao:
    beneficiario: str
    percentual: Decimal
    fracao_ideal: Fraction | None = None      # opcional, nunca inferida
```

Repassada a `QuinhaoBem` pelo calculador, sem transformação.

### 6.2. Entrada

```yaml
distribuicao:
  - beneficiario: HERDEIRO_8
    percentual: "3.125"
    fracao_ideal: "1/32"      # opcional
```

### 6.3. Validação

Parser deliberadamente **mais estrito que `fractions.Fraction`**, que aceitaria
silenciosamente formas que não são grafia de fração ideal em escritura:

| Entrada | Resultado |
|---|---|
| `"1/32"`, `"1/16"`, `"1/2"`, `"3/4"`, `"1/1"` | aceita |
| `"2/64"` | aceita, **normalizada para `1/32`** |
| `"1/0"` | recusada — denominador zero |
| `"0/5"` | recusada — não é maior que zero |
| `"-1/2"`, `"1/-2"` | recusadas — negativas |
| `"0.5"`, `"1e-2"` | recusadas — não são fração |
| `"abc"`, `"1/2/3"`, `""`, `"1 / 2"`, `"1//2"`, `"/2"`, `"1/"` | recusadas |
| `1.5` (não-string) | recusada |

Nenhuma dependência nova: `fractions.Fraction` é da biblioteca padrão.

---

## 7. Regra de formatação percentual

```
casas = expoente do Decimal, descartando zeros à direita, com piso de 2
```

**Sem teto arbitrário**, porque nenhum percentual do módulo é calculado — não
existe dízima a truncar. A precisão é sempre finita e escolhida por quem escreveu
a entrada.

| Entrada | Antes | Depois | Situação |
|---|---|---|---|
| `50` | `50,00%` | `50,00%` | inalterado |
| `50.00` | `50,00%` | `50,00%` | inalterado |
| `12.5` | `12,50%` | `12,50%` | inalterado |
| `12.500` | `12,50%` | `12,50%` | inalterado |
| `33.33` | `33,33%` | `33,33%` | inalterado |
| `6.25` | `6,25%` | `6,25%` | inalterado |
| `0.1` | `0,10%` | `0,10%` | inalterado |
| **`3.125`** | `3,12%` | **`3,125%`** | **corrigido** |
| **`0.005`** | `0,00%` | **`0,005%`** | **corrigido** |
| **`0.0001`** | `0,00%` | **`0,0001%`** | **corrigido** |

Nunca emite notação científica; usa vírgula decimal na minuta; é determinística.

**Quatro contratos separados**, conforme exigia o § 7:

| Função | Domínio | Precisão |
|---|---|---|
| `formatar_monetario` | dinheiro, humano | 2 casas fixas |
| `serializar_monetario` | dinheiro, JSON | 2 casas fixas |
| `formatar_percentual` | percentual, humano | variável |
| `serializar_percentual` | percentual, JSON | variável |

O mesmo `Decimal("3.125")` produz `"3.12"` como dinheiro e `"3.125"` como
percentual — comportamento coberto por teste dedicado.

---

## 8. Validação fração × percentual

A comparação **não pode** exigir igualdade textual de `Decimal`: frações como
`1/3` têm expansão infinita e o percentual da entrada é necessariamente
arredondado.

**Tolerância derivada da entrada, não arbitrada:**

> meia unidade da última casa decimal do percentual informado

Quem escreve `33.33` declara arredondamento à segunda casa, cujo maior erro
legítimo é `0,005`. Para `3.125`, cai para `0,0005`.

| Fração | Percentual | Tolerância | Diferença | Resultado |
|---|---|---|---|---|
| `1/2` | `50` | 0,005 | 0 | válido |
| `1/32` | `3.125` | 0,0005 | 0 | válido |
| `1/16` | `6.25` | 0,005 | 0 | válido |
| `1/8` | `12.5` | 0,005 | 0 | válido |
| `1/3` | `33.33` | 0,005 | 0,00333 | válido |
| `1/3` | `33.34` | 0,005 | 0,00666 | **recusado** |
| `1/2` | `40` | 0,005 | 10 | **recusado** |
| `1/32` | `6.25` | 0,005 | 3,125 | **recusado** |

`DECIMAL_TOLERANCIA` **não** foi reutilizada: mede centavos de patrimônio, não
arredondamento de percentual. Um teste dedicado trava essa separação.

---

## 9. Mudanças por arquivo

### Novos

| Arquivo | Papel |
|---|---|
| `application/formatting.py` | Camada autoritativa — 4 contratos + fração + tolerância |
| `examples/inventario_fracoes.yaml` | Fixture sintética com 1/16 e 1/32 |
| `docs/decisions/ADR-010-…md` | Decisão |
| `tests/test_notas_inventarios_formatting.py` | 57 testes |
| `tests/test_notas_inventarios_fracoes.py` | 42 testes |
| `tests/golden/notas_inventarios/inventario_fracoes_{minuta.md,resumo.md,validacao.json}` | Golden novo |

### Alterados

| Arquivo | Mudança |
|---|---|
| `domain/models.py` | `fracao_ideal: Fraction \| None = None` em `Distribuicao` e `QuinhaoBem` |
| `interfaces/schemas.py` | Campo opcional + parser estrito `_parse_fracao_ideal` |
| `application/calculator.py` | **1 linha** — repasse do metadado. Zero aritmética |
| `application/validator.py` | Regra `_validate_fracao_ideal` |
| `application/renderer.py` | Formatação delegada; coluna condicional no resumo |
| `interfaces/cli.py` | `_quinhao_payload` com serializador de percentual |
| `tests/test_notas_inventarios_golden.py` | 3º caso na parametrização |
| `docs/modules/notas_inventarios.md` | Nova § 6.1 |
| `docs/modules/notas_inventarios/POP_…md` | Campo na tabela + § 6.3.1 |
| `docs/decisions/index.md` | ADR-010 |
| `docs/roadmap.md` | Conclusão registrada no Horizonte B |

---

## 10. Golden files

**Objetivo preferencial do § 14 atingido integralmente.**

| Golden | Situação |
|---|---|
| `inventario_simples_minuta.md` | **byte a byte idêntico** |
| `inventario_simples_resumo.md` | **byte a byte idêntico** |
| `inventario_simples_validacao.json` | **byte a byte idêntico** |
| `inventario_sem_meeiro_minuta.md` | **byte a byte idêntico** |
| `inventario_sem_meeiro_resumo.md` | **byte a byte idêntico** |
| `inventario_sem_meeiro_validacao.json` | **byte a byte idêntico** |
| `inventario_fracoes_*` (3 arquivos) | **novos** |

Verificado por comparação direta antes de qualquer commit. **Nenhum golden
existente precisou mudar** — dois mecanismos garantem isso:

1. o **piso de 2 casas** faz todo percentual comum render o texto histórico;
2. `fracao_ideal` é **omitida do JSON** quando ausente, preservando o formato.

Conforme o § 14, o cenário fracionário entrou como **caso novo**, não como
transformação dos exemplos antigos.

---

## 11. Testes

| Categoria | Quantidade |
|---|---|
| **Herdados** (baseline) | **904** coletados — 903 passando + 1 skip de plataforma |
| **Novos** | **100** |
| **Total** | **1004** coletados — 1003 passando + 1 skip |

Distribuição dos novos:

| Arquivo | Testes | Cobertura |
|---|---|---|
| `test_notas_inventarios_formatting.py` | 57 | precisão, contratos separados, fração canônica, tolerância |
| `test_notas_inventarios_fracoes.py` | 42 | entrada, coerência, transporte, renderização, JSON, ODT, problema histórico |
| `test_notas_inventarios_golden.py` | +1 | 3º caso parametrizado |

Cobertura explícita dos itens exigidos pelo § 16 e § 17:

- **Percentuais:** `50`, `12.5` compatíveis; `3.125` não perde a terceira casa;
  `0.005` não vira zero; sem notação científica; determinístico.
- **JSON:** `3.125` preservado; dinheiro em 2 casas; fração omitida quando ausente.
- **Frações:** `1/32` válido; `2/64` normaliza; denominador zero, negativo e texto
  arbitrário recusados; mismatch recusado.
- **Renderer:** fração no resumo; ausência preserva a tabela histórica; ODT
  preserva a precisão; **minuta não exibe fração** (contrato travado por teste).
- **Regressão:** todos os goldens antigos + golden novo.
- **§ 17:** `3,125%` não é mais `3,12%`; `1/32` informado não se perde;
  percentuais exibidos somam 100%; **matemática idêntica com e sem fração**.

---

## 12. Demonstração antes/depois

Caso `examples/inventario_fracoes.yaml` — veículo de R$ 32.000,00, meeira com
1/2, sete herdeiros com 1/16 e dois com 1/32.

### Minuta § 11 (alínea do meio quinhão)

```diff
- a) 3,12% do bem descrito e caracterizado no item 7.1 (VEICULO_1), ...
+ a) 3,125% do bem descrito e caracterizado no item 7.1 (VEICULO_1), ...
```

Ocorrências de `3,12%` na minuta gerada: **0**. De `3,125%`: **2**.

### Resumo técnico § 4

```
| Beneficiário | Fração ideal | % | Valor |
|--------------|--------------|---|-------|
| `MEEIRO`     | 1/2          | 50,00%  | R$ 16.000,00 |
| `HERDEIRO_1` | 1/16         | 6,25%   | R$ 2.000,00  |
| `HERDEIRO_8` | 1/32         | 3,125%  | R$ 1.000,00  |
```

Percentuais exibidos: `50,00 + 7 × 6,25 + 2 × 3,125 = 100,00%` — fecham
exatamente, o que não acontecia antes.

### JSON de validação

```diff
- { "beneficiario": "HERDEIRO_8", "percentual": "3.12",  "valor": "1000.00" }
+ { "beneficiario": "HERDEIRO_8", "percentual": "3.125", "valor": "1000.00",
+   "fracao_ideal": "1/32" }
```

### ODT

`content.xml` contém `3,125%`; não contém `3,12%`.

---

## 13. Confirmação de matemática inalterada

O § 12 do escopo era categórico. Três provas independentes:

**1. Diff do calculador.** Uma única linha funcional:

```diff
+                    fracao_ideal=d.fracao_ideal,
```

Nenhuma linha de aritmética foi tocada. `quantize_money`, `ROUND_HALF_EVEN`,
`DECIMAL_TOLERANCIA`, meação, monte, quinhões e `divergencia_centavos`
permanecem exatamente como estavam.

**2. Teste comparativo direto.** `test_matematica_monetaria_identica_com_e_sem_fracao`
roda o **mesmo** inventário duas vezes — com e sem fração — e compara
`patrimonio_total`, `valor_meacao`, `monte_partilhavel`, `divergencia_centavos`,
`quinhao_por_herdeiro`, `total_por_beneficiario` e o valor de cada quinhão.
Todos idênticos.

**3. Golden files byte a byte.** Os seis anteriores incluem valores monetários em
minuta, resumo e JSON. Byte a byte idênticos ⇒ nenhum valor mudou.

**ADR-009 intacta.** A fixture foi escolhida com patrimônio divisível por 32
justamente para fechar em centavos exatos e isolar representação de resíduo. O
comportamento de alerta segue governado exclusivamente pela ADR-009.

---

## 14. Quality gate

Rodado localmente ao final, na ordem do § 19.

| Gate | Resultado |
|---|---|
| `ruff format --check .` | 🟢 **150 files already formatted** |
| `ruff check .` | 🟢 **All checks passed!** |
| `pytest -q` | 🟢 **1003 passed, 1 skipped** |
| `alembic heads` | 🟢 **f4a5b6c7d8e9 (head)** — único |
| `alembic check` | 🟢 **No new upgrade operations detected.** |

Suíte de notas isolada, rodada antes do gate global para feedback rápido:
**236 passed, 768 deselected**.

| Contagem | Valor |
|---|---|
| Testes herdados | 904 (903 + 1 skip) |
| Testes novos | 100 |
| **Total** | **1004** (1003 + 1 skip) |
| Regressões | **0** |

O único skip continua sendo o `chmod` condicional ao Windows, que executa
normalmente no CI Linux.

---

## 15. Riscos remanescentes

| # | Risco | Prob. | Impacto | Situação |
|---|---|:--:|:--:|---|
| **RF-1** | **Fração não aparece na minuta** — o usuário pode esperar que apareça | média | médio | 🔴 **Aberto por decisão deliberada.** Documentado na ADR-010 § 8, na § 6.1.4 do módulo, no POP § 6.3.1 e travado por teste. Depende do tabelião definir a redação |
| **RF-2** | Percentual por extenso ausente — a minuta manual grafa `3,125% (três inteiros e cento e vinte e cinco milésimos por cento)`; o gerador não | média | baixo | 🟡 **Registrado, fora de escopo.** Lacuna de redação distinta, identificada ao analisar o caso sanitizado |
| **RF-3** | Entrada com precisão absurda (ex.: 28 casas) renderiza 28 casas | baixa | baixo | 🟡 Aceito: é fidelidade à entrada. Não há teto porque nenhum percentual é calculado; um teto seria arbitrário |
| **RF-4** | Fração informada errada e coerente com percentual errado passa na validação | baixa | médio | 🟡 A validação confere coerência **interna**, não correção jurídica. O checklist humano continua obrigatório |
| **RF-5** | Coluna de fração muda a forma da tabela do resumo | baixa | baixo | 🟢 Mitigado: decisão por documento, não por bem; ausência de fração preserva a tabela histórica, com teste |

---

## 16. Git status final

```
git status --short
(vazio — working tree limpo)
```

| Item | Início | Fim |
|---|---|---|
| HEAD | `a06f2bb` | 4 commits à frente |
| `origin/main` | `a06f2bb` | `a06f2bb` — **inalterado** |
| Ahead / behind | 0 / 0 | **4 / 0** |
| Push | — | ❌ **não executado** — aguarda autorização (§ 23) |

### Conformidade com o escopo

| Restrição | Cumprida |
|---|:--:|
| Não alterar regras sucessórias | ✅ |
| Não alterar cálculo monetário | ✅ (provado de três formas) |
| Não alterar política de centavos / ADR-009 | ✅ |
| Não alterar cenários suportados | ✅ |
| Não alterar API, banco, migrations | ✅ |
| Não inferir fração jurídica | ✅ (teste dedicado) |
| Não inventar redação cartorária | ✅ (contingência do § 5 acionada) |
| Não abrir imagem/documento bruto com PII | ✅ (só artefatos sanitizados) |
| Fixture sem dados do caso real | ✅ (valores sintéticos) |
| Goldens antigos preservados | ✅ (6/6 byte a byte) |
| Staging explícito, sem `git add .` | ✅ |
| Sem `--no-verify`, sem `--force` | ✅ |
| Push somente com autorização | ✅ **não executado** |

---

*Fim do relatório — `NOTAS-INVENTARIO-FRACOES-1` · 2026-09-03.*
