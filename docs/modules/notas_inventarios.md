# Módulo `notas/inventarios` — Minuta-base de Inventário Extrajudicial

> Sprint **NOTAS-INVENTARIO-0/1** — análise estrutural do modelo de minuta e fundação
> mínima do módulo (`app/modules/notas/inventarios/`).
>
> Data: 2026-05-20.
> Escopo: Tabelionato de Notas — somente **inventário extrajudicial com 1 falecido**.

---

## 1. Objetivo do módulo

Gerar uma **minuta-base padronizada** de inventário extrajudicial a partir de **dados
estruturados, genéricos e sem PII**:

- quantidade de herdeiros e existência de meeiro;
- patrimônio total, meação, monte partilhável e quinhões;
- lista de bens, direitos e valores;
- distribuição dos bens entre meeiro/herdeiros;
- placeholders para qualificações pessoais.

**O sistema NÃO recebe, armazena ou versiona dados pessoais reais.** A qualificação
completa das partes (CPF, RG, endereço, nascimento, filiação) continua sendo feita no
**Engegraph**. O Cartório System produz a *estrutura restante* — texto, cálculos e
distribuição — com marcadores como:

```
[QUALIFICAÇÃO DO AUTOR DA HERANÇA]
[QUALIFICAÇÃO DO MEEIRO]
[QUALIFICAÇÃO DO HERDEIRO 1]
```

---

## 2. Etapa A — Análise estrutural da minuta

### 2.1. Arquivos analisados

| Caminho local (fora do Git) | Formato | Tipo |
|---|---|---|
| `_local_data/serventia_docs/Modelos de minutas/Modelo Inventário 1 FALECIDO.odt` | OpenDocument Text | Modelo (template) |

Após inspeção, o arquivo é um **modelo em branco**: usa marcadores explícitos como
`Nome do(s) falecido(s)`, `NOME DO PRIMEIRO HERDEIRO`, `R$NNN`, `XX%`, `DD/DD/DD`,
`NNN.NNN.NNN-NN`. **Não há dados pessoais reais.** Mesmo assim, o arquivo original
permanece em `_local_data/` (gitignorado); apenas a estrutura abstraída foi trazida
para este documento.

### 2.2. Blocos principais (numeração espelha a minuta)

| § | Bloco | Conteúdo | Origem dos dados |
|---|-------|----------|------------------|
| Cabeçalho | Identificação do ato | "Escritura Pública de Inventário e Partilha…" + cidade, comarca, tabeliã, data | Sistema/Engegraph |
| 1 | Qualificação das partes | Herdeiros descendentes + advogado | **Engegraph (placeholder)** |
| 2 | Autor da herança | Qualificação do *de cujus* (estado civil, regime de bens) | **Engegraph (placeholder)** |
| 3 | Falecimento | Data, hora, local, certidão de óbito | **Engegraph (placeholder)** |
| 4 | Inexistência de testamento | Consulta CENSEC / Prov. 56/2016 CNJ | Sistema (data, n.º) |
| 5 | Herdeiros | Lista de herdeiros descendentes | Cartório System (id + Engegraph para nome) |
| 6 | Inventariante | Nomeação + aceite (art. 617/618 CPC) | Cartório System (id) + Engegraph |
| 7 | Bens | 7.1, 7.2, … (imóveis, veículos, valores, etc.) | **Cartório System** |
| 8 | Débitos | Declaração de inexistência | Cartório System (flag) |
| 9 | Outras obrigações | Declaração de inexistência | Cartório System (flag) |
| 10 | Patrimônio | Total, meação, herança | **Cartório System (calculado)** |
| 10.1 | Meação | Valor da meação do(a) viúvo(a) | **Cartório System (calculado)** |
| 10.2 | Herança | Quinhão de cada herdeiro | **Cartório System (calculado)** |
| 11 | Partilha | Distribuição bem a bem (% e R$) | **Cartório System (calculado)** |
| 12 | Certidões | CND, CNDT, ações cíveis, RFB | Lista fixa + datas |
| 13 | CNIB | Indisponibilidade de bens | Sistema (data, hash, status) |
| 14 | Declarações | Bem livre, sem ações reais | Texto fixo |
| 15 | Declaração do advogado | Texto fixo | Engegraph (nome do advogado) |
| 16 | ITCMD | Demonstrativos SPL, data | Sistema (n.º guia, data) |
| 17 | Outras declarações | Texto fixo (Prov. 46/2020 GO, Dec. 93.240/86) | Fixo |
| 18 | Declarações finais | Autorização ao RI + Res. 35 CNJ | Fixo |
| 19 | Únicos herdeiros | Declaração art. 21 Res. 35 CNJ | Fixo |
| 20 | LGPD | Cláusula padrão (Lei 13.709/18, Prov. 134/2022 CNJ, CNPFE/2023 TJ-GO) | Fixo |
| Encerramento | DOI, emolumentos, assinaturas | Sistema (R$) + assinaturas físicas |

### 2.3. Campos variáveis identificados

Classificação por **origem do dado**:

#### A. Placeholders (Engegraph — nunca tocados pelo Cartório System)

- Nome, CPF, RG, nascimento, filiação, naturalidade, estado civil, regime de bens
  do *de cujus*, do meeiro, de cada herdeiro e do advogado.
- Endereços, profissões.
- Certidão de óbito (livro, fls., termo, data, cartório de RCPN).
- Dados completos do imóvel (descrição, matrícula real, selo digital).
- Número da OAB, etc.

#### B. Dados estruturados do ato (Cartório System)

- Cidade, comarca, tabeliã (configuração da serventia).
- Data e hora da lavratura (gerada pelo sistema).
- Quantidade de herdeiros (`N`).
- Existência de meeiro (`possui_meeiro: bool`).
- Percentual de meação (`percentual_meacao`, padrão 50 para comunhão).
- Patrimônio total (`Decimal`).
- Lista de bens (`id`, `tipo`, `descricao_generica`, `valor`).
- Distribuição (`bem → beneficiário → percentual`).
- Percentual de herança de cada herdeiro.
- Dados de certidões consultadas (CENSEC, CNIB, CND/CNDT) — apenas datas/hashes.
- Demonstrativo ITCMD (n.º guia SPL, data).
- Emolumentos e taxa judiciária.

#### C. Texto fixo (constantes de template)

- Cláusulas §§ 14, 15, 17, 18, 19, 20 (com pequenas variações textuais).
- Encerramento "EMITIDA A DOI…".

### 2.4. Blocos condicionais

| Condição | Comportamento |
|---|---|
| `possui_meeiro = false` | Suprimir §§ 10.1 e 11.1; redistribuir 100% entre herdeiros |
| Vários falecidos | **FORA DE ESCOPO** (modelo atual é "1 FALECIDO") — exigirá modelo separado |
| Imóvel vs. veículo vs. saldo bancário/dinheiro | Variação textual em § 7.x (descrição genérica difere) |
| `debitos_existentes = true` | § 8 muda de "não possuía débitos" para "possuía os seguintes débitos…" |
| `obrigacoes_existentes = true` | § 9 análogo a § 8 |
| `cnib_status` | § 13 muda texto se houver indisponibilidade real |
| Existência de advogado comum | § 1.N e § 15 — texto adapta para "advogados das partes" |

> **Decisão MVP:** Sprint 1 trata apenas o caso **`possui_meeiro` opcional + 1 falecido +
> sem débitos/obrigações + advogado único**. Demais variações ficam fora.

### 2.5. Regras de cálculo extraídas da minuta

```
patrimonio_total  = Σ bens.valor
meação            = patrimonio_total × (percentual_meacao / 100)   [se possui_meeiro]
monte_partilhavel = patrimonio_total − meação
quinhão_herdeiro  = monte_partilhavel × (percentual_heranca / 100)
```

Para cada bem `B`:

```
valor_meeiro(B)       = B.valor × (distribuicao[MEEIRO].percentual / 100)
valor_herdeiro_i(B)   = B.valor × (distribuicao[HERDEIRO_i].percentual / 100)
Σ percentuais(B)      = 100,00
```

Validações implícitas no texto:

- "50,00% (cinquenta por cento)" e "XX% ()" indicam que o percentual deve ter 2 casas
  decimais e que valor extenso por enquanto NÃO será gerado automaticamente.
- "avaliado em R$NNN correspondendo à sua meação R$NNN" pressupõe que o valor da fração
  bate com `bem.valor × percentual / 100`.

### 2.6. Pontos que exigem validação humana

1. **Estado civil / regime de bens** do autor da herança define se há meeiro e qual o
   percentual de meação. Cartório System recebe o flag; a verificação documental é
   manual no Engegraph.
2. **Vocação hereditária** (filhos vs. ascendentes vs. cônjuge concorrente) — fora do
   escopo. A serventia decide manualmente; o sistema apenas reflete `herdeiros[]`.
3. **Descrição dos bens** — o sistema gera descrição genérica; a descrição completa,
   matrícula real e procedência continuam manuais.
4. **Cálculo de ITCMD** — não é responsabilidade do sistema; apenas registra o número
   do demonstrativo SPL.
5. **Texto final lido às partes** — minuta gerada é *base*, sempre revisada pelo
   tabelião antes de assinatura.

### 2.7. Riscos de automatização

| Risco | Mitigação na sprint atual |
|---|---|
| Geração de texto com dado errado induzir tabelião ao erro | Placeholders explícitos `[QUALIFICAÇÃO …]`; minuta marcada como "MINUTA — REVISAR" |
| Cálculo financeiro com `float` divergir do Engegraph | Uso obrigatório de `Decimal`, arredondamento explícito a 2 casas |
| Soma de percentuais com erro de centavos | Validação `abs(soma − 100) < 0,01` (tolerância configurável) |
| Confusão entre meação e herança | Validação cruzada: `meação + herança = patrimônio` |
| Vazamento de dados reais via testes/exemplos | Exemplos e fixtures **só** com placeholders e valores fictícios |
| Bem distribuído a beneficiário inexistente | Validação de integridade referencial entre `herdeiros[]` e `bens[].distribuicao[].beneficiario` |

### 2.8. Proposta de schema inicial de entrada

```yaml
tipo_ato: inventario_extrajudicial            # único valor aceito por enquanto
possui_meeiro: true                            # bool
percentual_meacao: 50                          # 0..100, obrigatório se possui_meeiro
patrimonio_total: 1000000.00                   # Decimal, > 0, deve bater com Σ bens.valor

herdeiros:
  - id: HERDEIRO_1                             # identificador local, sem PII
    percentual_heranca: 50                     # 0..100, Σ = 100
  - id: HERDEIRO_2
    percentual_heranca: 50

bens:
  - id: IMOVEL_1                               # identificador local
    tipo: imovel | veiculo | dinheiro | direito | outro
    descricao_generica: "Imóvel urbano objeto da matrícula [MATRICULA]"
    valor: 600000.00                           # Decimal, ≥ 0
    distribuicao:
      - beneficiario: MEEIRO                   # MEEIRO ou id de herdeiro
        percentual: 50
      - beneficiario: HERDEIRO_1
        percentual: 25
      - beneficiario: HERDEIRO_2
        percentual: 25
```

### 2.9. Fonte executável vs. template .j2 — estado atual

> **Decisão da Sprint NOTAS-INVENTARIO-3:** a fonte executável da minuta-base
> é `app/modules/notas/inventarios/application/renderer.py`
> (`render_minuta_markdown`). O arquivo
> `app/modules/notas/inventarios/infrastructure/templates/inventario_extrajudicial_padrao.md.j2`
> existe **apenas como espelho textual provisório** — não é interpretado em
> runtime, não há dependência de Jinja2 instalada e a renderização real é
> Python puro.
>
> **Por quê:** introduzir Jinja2 agora adicionaria dependência sem ganho — o
> renderer Python já produz o mesmo resultado, com mais controle sobre tipos,
> placeholders e Decimal. Eventual unificação (Jinja2 ↔ renderer) é decisão
> de sprint futura e exigirá ADR.
>
> **Manutenção:** ao alterar texto cartorário, atualizar `renderer.py`
> primeiro (a fonte) e refletir manualmente no `.j2` quando a estrutura
> textual mudar (cabeçalhos, ordem de cláusulas, novos blocos). O `.j2` não
> precisa espelhar lógica condicional fina — basta indicar onde os blocos
> aparecem.

O template versionado contém **apenas placeholders e cláusulas fixas**.
Nenhum trecho com dados reais é versionado, e datas de normas legais aparecem
por extenso ("7 de dezembro de 2017") para não disparar a verificação
anti-PII de `tests/test_notas_inventarios_renderer.py`.

Identificadores reservados:

| Placeholder | Significado | Origem real |
|---|---|---|
| `[QUALIFICAÇÃO DO AUTOR DA HERANÇA]` | Bloco completo de qualificação | Engegraph |
| `[QUALIFICAÇÃO DO MEEIRO]` | Bloco completo | Engegraph |
| `[QUALIFICAÇÃO DO HERDEIRO N]` | Bloco completo de cada herdeiro | Engegraph |
| `[QUALIFICAÇÃO DO ADVOGADO]` | Bloco completo | Engegraph |
| `[CERTIDAO_OBITO]` | Livro, fls., termo, data, RCPN | Engegraph |
| `[CENSEC_DATA]` | Data da consulta CENSEC | Engegraph |
| `[ITCMD_SPL_N]` | Número da guia SPL | Engegraph |
| `[CNIB_HASH]`, `[CNIB_DATA]`, `[CNIB_STATUS]` | Dados da consulta | Sistema externo |
| `[MATRICULA]`, `[REGISTRO_AQUISITIVO]`, `[SELO_DIGITAL]` | Dados do imóvel | Engegraph / RI |

---

## 3. Etapa B — Implementação inicial mínima

### 3.1. Estrutura criada

20 arquivos criados ao todo: 16 sob `app/modules/notas/`, 3 testes
(`tests/test_notas_inventarios_calculator.py`,
`tests/test_notas_inventarios_validator.py`,
`tests/test_notas_inventarios_output_dir.py`) e este documento. Nenhum arquivo
fora desses caminhos foi modificado.

```
app/modules/notas/
  __init__.py
  inventarios/
    __init__.py
    domain/
      __init__.py
      models.py            # dataclasses: Bem, Herdeiro, Distribuicao, Inventario
      errors.py            # exceções específicas
    application/
      __init__.py
      calculator.py        # cálculos: patrimônio, meação, monte, quinhões
      validator.py         # validações estruturais e numéricas
      renderer.py          # resumo técnico Markdown (NÃO é a minuta)
    infrastructure/
      __init__.py
      loaders.py           # carregar YAML / JSON
      output_dir.py        # proteção do --output-dir do CLI
      templates/
        inventario_extrajudicial_padrao.md.j2   # esqueleto — não usado nesta sprint
    interfaces/
      __init__.py
      cli.py               # python -m app.modules.notas.inventarios.interfaces.cli
    examples/
      inventario_simples.yaml      # exemplo com 2 herdeiros, com meeiro
      inventario_sem_meeiro.yaml   # exemplo sem meeiro
```

### 3.2. Validações implementadas (Sprint 1)

1. `tipo_ato` deve ser `inventario_extrajudicial`.
2. `patrimonio_total > 0`.
3. Se `possui_meeiro`: `0 < percentual_meacao ≤ 100`.
4. Se NÃO possui meeiro: `percentual_meacao` deve ser `0` ou ausente.
5. `len(herdeiros) ≥ 1` e todos com `id` único, não vazio.
6. Soma de `percentual_heranca` dos herdeiros = 100 (tolerância ±0,01).
7. `len(bens) ≥ 1` e todos com `id` único, não vazio.
8. `Σ bens.valor == patrimonio_total` (tolerância ±0,01).
9. Para cada bem: soma da distribuição = 100 (tolerância ±0,01).
10. Para cada bem: todo `beneficiario` ∈ `{"MEEIRO"} ∪ {herdeiros[*].id}`.
11. Se `possui_meeiro = false`: nenhum bem pode ter beneficiário `MEEIRO`.
12. Nenhum valor calculado pode resultar negativo.

### 3.3. Cálculos implementados

`InventarioCalculator.compute(inventario) -> ResumoInventario`:

- `patrimonio_total` (recalculado a partir dos bens — confronta com o declarado).
- `valor_meacao` e `monte_partilhavel`.
- `quinhao[herdeiro_id]` por herdeiro.
- `distribuicao_por_bem[bem_id] -> { beneficiario: (percentual, valor) }`.
- `total_por_beneficiario` (verificação cruzada: meeiro + Σ herdeiros = patrimônio).

Todos os cálculos usam `Decimal` (precisão 28 dígitos, `ROUND_HALF_EVEN`).

### 3.4. CLI

```bash
python -m app.modules.notas.inventarios.interfaces.cli \
  --input app/modules/notas/inventarios/examples/inventario_simples.yaml \
  --output-dir outputs/inventarios
```

Saídas padrão (sempre em `outputs/inventarios/`, gitignorado):

- `inventario_validacao.json` — resultado da validação (ok/erros) + resumo dos cálculos.
- `inventario_resumo.md` — **resumo técnico** legível com placeholders (NÃO é a minuta
  completa).

Com `--render-minuta`, gera adicionalmente:

- `inventario_minuta.md` — **minuta-base** da escritura pública (§§ 1–20 +
  encerramento + campo de revisão humana). Apenas placeholders; nunca PII real.
  Só é produzida quando a validação passa (exit 0). Política de centavos
  seguida pela minuta: [ADR-009](../decisions/ADR-009-inventory-cent-rounding-policy.md).

#### Proteção do `--output-dir`

O CLI valida o caminho antes de gravar. A política é **whitelist**:

- Dentro do repositório: permitido apenas se o primeiro componente for
  `outputs/`, `tmp/` ou `.ai_tmp/` (os três gitignorados).
- Fora do repositório: liberado — responsabilidade do usuário.

Qualquer outro destino interno — pastas conhecidas (`app/`, `docs/`, `tests/`,
`_local_data/`, `.git/`, `alembic/`, `scripts/`) ou pastas ad-hoc
(`relatorios_inventario/`, `inventarios_saida/`, etc.) — faz a CLI sair com
código `2` e mensagem orientativa.

Implementação em [output_dir.py](../../app/modules/notas/inventarios/infrastructure/output_dir.py).

### 3.5. O que **NÃO** está implementado nesta sprint

- Renderização da minuta completa via Jinja2 (template existe como esqueleto, mas o
  renderizador atual produz apenas `inventario_resumo.md`).
- Múltiplos falecidos.
- Variações condicionais de § 8/§ 9 com débitos/obrigações.
- Variações de regime de bens (somente comunhão parcial padrão é tratada via
  `percentual_meacao`).
- API REST, persistência em banco, integração com Engegraph/Atlas.

---

## 4. Recomendações para a próxima sprint

1. **NOTAS-INVENTARIO-2 — CONCLUÍDA:** renderização Markdown da minuta-base em
   Python puro (sem Jinja2). Commit `47956cc`.
2. **NOTAS-INVENTARIO-3 — CONCLUÍDA (esta sprint):** revisão cartorária da
   minuta Markdown (PEP, frase de transição § 1→§ 2, procedência detalhada de
   imóveis, texto completo dos §§ 6, 14, 17, 18, 19, 20, encerramento com
   linhas de assinatura) e checklist humano em
   [`notas_inventarios_checklist.md`](notas_inventarios_checklist.md).
3. **NOTAS-INVENTARIO-4 (próxima):** variações condicionais reais — débitos
   declarados (§ 8 com lista de credores), obrigações remanescentes (§ 9),
   advogados múltiplos (§§ 1.N e 15), e CNIB com status diferente de
   `NEGATIVO` (alerta antes da assinatura).
4. **NOTAS-INVENTARIO-5:** schema Pydantic + validações tipadas + cobertura
   de testes estendida (golden files comparando saída byte a byte).
5. **NOTAS-INVENTARIO-6:** pacote `infrastructure/exporters/` para gerar
   `.docx` ou `.odt` a partir do Markdown — preservando placeholders para
   preenchimento manual. Esta sprint **NÃO** implementa export.
6. **ADR obrigatório** quando: definir contrato de import (campos vindos do
   Engegraph), unificar fonte Markdown ↔ Jinja2, definir formato de saída
   versionável (markdown vs odt vs docx), integrar com módulo de selo digital
   / arquivamento.

---

## 5. Riscos remanescentes

- O template versionado é simplificação do modelo original. Antes da Sprint 2, o
  tabelião deve revisar `inventario_extrajudicial_padrao.md.j2` e validar o texto
  fixo das cláusulas §§ 14, 15, 17, 18, 19, 20.
- Tolerância de centavos (`±0,01`) pode mascarar erros de digitação em valores
  grandes. Avaliar uso de tolerância proporcional em sprint futura.

---

## 5.0. Formato do § 11 — apenas alíneas

> **Decisão da Sprint NOTAS-INVENTARIO-3-FINAL:** o § 11 da minuta cartorária
> (`inventario_minuta.md`) usa **apenas alíneas (a, b, c…)** por beneficiário,
> preservando o modelo padrão da serventia. Quadros/tabelas de partilha
> **não aparecem** na minuta.
>
> **Por quê:** o modelo da serventia é o padrão cartorário aceito e não pode
> ser modificado por automação. A minuta-base deve espelhar fielmente esse
> formato; o tabelião não deve precisar reformatar a partilha após a
> geração.
>
> **Onde os quadros tabulares ainda aparecem:** no resumo técnico
> `inventario_resumo.md` (§ 3 e § 5) e no JSON de validação
> `inventario_validacao.json` (`resumo.bens[].quinhoes`). Esses dois
> artefatos são para conferência interna, não para lavratura.

## 5.1. Checklist de conferência humana

O checklist operacional para revisão da minuta-base antes da lavratura está
em [`notas_inventarios_checklist.md`](notas_inventarios_checklist.md). Cobre
18 blocos (identidade do ato, autor da herança, falecimento, testamento,
meeiro, herdeiros, bens, partilha, débitos, certidões, CNIB, ITCMD,
advogado, declarações LGPD, alerta de centavos, placeholders pendentes,
encerramento e aprovação final).

A minuta gerada (`inventario_minuta.md`) inclui no final um bloco "CAMPO
DE REVISÃO HUMANA" com 5 etapas mínimas (qualificações, cálculos, ITCMD,
remoção de placeholders, aprovação final) e link explícito para o checklist
completo.

## 6. Política de centavos

> **Decisão vigente:** [ADR-009 — Política de centavos em inventários
> extrajudiciais](../decisions/ADR-009-inventory-cent-rounding-policy.md).
> A subseção abaixo descreve a regra confirmada pelo ADR; a discussão original
> e as três alternativas avaliadas (alerta puro, ajuste controlado, distribuição
> por valor) ficam preservadas no próprio ADR.

A combinação de percentuais (ex.: `33,33% × 3 = 99,99%`) faz com que a soma do
que é efetivamente distribuído possa diferir do patrimônio total em alguns
centavos. **O sistema não corrige essa diferença automaticamente** — em vez
disso:

1. O calculador retorna `ResumoInventario.divergencia_centavos` com o valor
   absoluto da diferença.
2. O JSON de validação (`inventario_validacao.json`) expõe sempre o campo
   `resumo.divergencia_centavos`, e adiciona um objeto `alerta_centavos` no nível
   raiz quando há divergência.
3. O resumo Markdown inclui uma seção "⚠ Alerta de centavos" quando aplicável.
4. A minuta-base (`inventario_minuta.md`, gerada com `--render-minuta`) inclui
   uma seção "⚠ AVISO TÉCNICO — DIVERGÊNCIA DE CENTAVOS" quando há resíduo,
   instruindo o tabelião a revisar a partilha bem a bem antes da assinatura.
5. A CLI imprime um aviso em `stderr` (sem alterar o exit code).

A próxima reavaliação desta política está condicionada aos critérios listados
em [ADR-009 § Critérios para revisão futura](../decisions/ADR-009-inventory-cent-rounding-policy.md#crit%C3%A9rios-para-revis%C3%A3o-futura).

---

## 7. Contrato de entrada — schema Pydantic v2

> **Sprint NOTAS-INVENTARIO-4.** O contrato YAML/JSON é validado por um
> schema Pydantic v2 antes de chegar ao validador de negócio. Estrutura,
> tipos e ``Decimal`` seguro entram no schema; soma de percentuais e
> integridade referencial permanecem no
> [`application/validator.py`](../../app/modules/notas/inventarios/application/validator.py).

### 7.1. Pipeline atual

```
YAML/JSON
  └─► loaders.load_inventario   ─ decodifica e protege contra YAML/JSON malformado
       └─► schemas.parse_inventario_input
            ├─ InventarioInputSchema  ─ Pydantic v2 (estrutural)
            │   ├─ extra="forbid"  ─ recusa campo não previsto
            │   ├─ Literal["inventario_extrajudicial"]
            │   ├─ Decimal seguro (float convertido via str — sem ruído binário)
            │   └─ TipoBem validado por field_validator com mensagem "tipo inválido"
            └─ to_inventario()       ─ converte para os modelos imutáveis do domínio
                 └─► InventarioValidator (negócio)
                      └─► InventarioCalculator
                           └─► renderer.render_resumo_markdown / render_minuta_markdown
```

### 7.2. O que é validação **estrutural** (Pydantic)

- presença dos campos obrigatórios (`tipo_ato`, `possui_meeiro`, `patrimonio_total`, `herdeiros`, `bens`);
- tipos: `bool`, `Decimal`, `str`, `TipoBem`, listas;
- listas não vazias (`herdeiros` e `bens`);
- `extra="forbid"` em todos os modelos — protege contra digitação criativa
  no YAML ("nome_real", "matricula_real") que poderia mascarar erro;
- coerção segura para `Decimal`: aceita `int`, `str` e `float` (float → `str` →
  `Decimal`, evitando `Decimal(0.1) → 0.10000000000000000555…`);
- booleano em campo numérico é rejeitado (`Decimal(True) == 1` é armadilha);
- mensagens de erro agregadas com o caminho do campo (`bens.0.valor: …`)
  para facilitar diagnóstico via CLI.

### 7.3. O que continua como validação de **negócio** (validator)

- `Σ herdeiros[*].percentual_heranca == 100` (tolerância ±0,01);
- `Σ bens[*].valor == patrimonio_total` (tolerância ±0,01);
- `Σ bens[*].distribuicao[*].percentual == 100` por bem;
- todo `beneficiario` ∈ `{"MEEIRO"} ∪ {ids de herdeiros}`;
- meeiro proibido quando `possui_meeiro=false`;
- `percentual_meacao` dentro do intervalo correto conforme `possui_meeiro`;
- ids únicos e não vazios em `herdeiros[]` e `bens[]`;
- `MEEIRO` reservado — não pode ser id de herdeiro;
- política de centavos da [ADR-009](../decisions/ADR-009-inventory-cent-rounding-policy.md).

### 7.4. Exemplos com `Decimal` seguro

Os exemplos versionados foram migrados para **strings decimais** nos campos
monetários e percentuais, evitando passagem por `float` no parser YAML:

```yaml
percentual_meacao: "50"
patrimonio_total: "1000000.00"
```

Quem montar payloads em Python pode passar tanto `str` quanto `Decimal`;
floats são aceitos (e convertidos via `str`), mas a recomendação é
preferir strings decimais para clareza e reprodutibilidade.

### 7.5. Golden files

As três saídas canônicas — `inventario_validacao.json`,
`inventario_resumo.md` e `inventario_minuta.md` — para os dois exemplos
canônicos vivem em:

```
tests/golden/notas_inventarios/
  inventario_simples_validacao.json
  inventario_simples_resumo.md
  inventario_simples_minuta.md
  inventario_sem_meeiro_validacao.json
  inventario_sem_meeiro_resumo.md
  inventario_sem_meeiro_minuta.md
```

Os goldens são **fixtures versionáveis** — texto, sem PII, sempre em LF
(o teste verifica e falha se aparecer CRLF). Eles funcionam como teste
de regressão byte a byte: qualquer mudança no renderer, no validator ou
no JSON de validação que não seja intencional quebra
`tests/test_notas_inventarios_golden.py`.

#### Como atualizar um golden manualmente

Quando uma mudança intencional de minuta/resumo/validação for feita
(cláusula textual nova, campo a mais no JSON, política de centavos
ajustada):

```powershell
# 1. Rodar a CLI nos dois exemplos canônicos com a versão nova:
python -m app.modules.notas.inventarios.interfaces.cli `
  --input app/modules/notas/inventarios/examples/inventario_simples.yaml `
  --output-dir .ai_tmp/inv_simples `
  --render-minuta
python -m app.modules.notas.inventarios.interfaces.cli `
  --input app/modules/notas/inventarios/examples/inventario_sem_meeiro.yaml `
  --output-dir .ai_tmp/inv_sem_meeiro `
  --render-minuta

# 2. Inspecionar diff dos arquivos gerados vs. golden atual:
Compare-Object `
  (Get-Content tests/golden/notas_inventarios/inventario_simples_minuta.md) `
  (Get-Content .ai_tmp/inv_simples/inventario_minuta.md)

# 3. Copiar para tests/golden/notas_inventarios/, normalizar CRLF→LF,
#    e commitar junto com a mudança que motivou a regeneração.
```

A atualização **não** acontece automaticamente durante o teste — a
política é deliberada: golden files são parte do contrato e exigem
revisão consciente. Outputs gravados em `outputs/` continuam fora do
controle de versão.

#### O que os goldens **não** contêm

- nenhum dado pessoal real (CPF, RG, endereço, nome civil);
- nenhum CPF/CNPJ/CEP/e-mail/data dd/mm/aaaa — o teste anti-PII no
  conjunto golden recusa qualquer ocorrência;
- nenhuma referência a documentos físicos da serventia.

---

## 8. Export ODT — `--export-odt`

> **Sprint NOTAS-INVENTARIO-5.** A CLI passa a exportar a minuta-base
> também em `.odt` (OpenDocument Text), para conferência prática no
> LibreOffice Writer. O exportador vive em
> [`infrastructure/exporters/odt_exporter.py`](../../app/modules/notas/inventarios/infrastructure/exporters/odt_exporter.py).

### 8.1. Markdown continua sendo a fonte canônica

O `.odt` é um **artefato derivado**. A fonte de verdade da minuta segue
sendo `inventario_minuta.md`, produzido por `render_minuta_markdown`.
O pipeline é estritamente unidirecional:

```text
YAML/JSON → Pydantic → validação de negócio → cálculo
  → render_minuta_markdown() → inventario_minuta.md
  → export_inventario_odt(markdown) → inventario_minuta.odt
```

O ODT **nunca** volta para o pipeline como entrada e **não** substitui o
Markdown. Qualquer mudança na minuta é feita no `renderer.py`; o ODT é
regerado a partir do Markdown resultante.

### 8.2. Uso na CLI

```bash
# Contrato anterior preservado — gera apenas validação + resumo:
python -m app.modules.notas.inventarios.interfaces.cli \
  --input app/modules/notas/inventarios/examples/inventario_simples.yaml \
  --output-dir outputs/inventarios

# --render-minuta: gera também inventario_minuta.md (inalterado):
python -m app.modules.notas.inventarios.interfaces.cli \
  --input app/modules/notas/inventarios/examples/inventario_simples.yaml \
  --output-dir outputs/inventarios --render-minuta

# --export-odt: gera inventario_minuta.md E inventario_minuta.odt:
python -m app.modules.notas.inventarios.interfaces.cli \
  --input app/modules/notas/inventarios/examples/inventario_simples.yaml \
  --output-dir outputs/inventarios --export-odt
```

- `--export-odt` **implica** a renderização da minuta Markdown — não é
  preciso passar `--render-minuta` junto.
- Se a validação falhar: nem o `.md` nem o `.odt` são gerados; a CLI
  retorna o mesmo exit code de validação (`1`) e imprime mensagem clara.
- A proteção de `--output-dir` (whitelist `outputs/`, `tmp/`, `.ai_tmp/`
  ou caminho externo) continua valendo para o `.odt`.

### 8.3. Como o ODT é montado

Um `.odt` é um ZIP com estrutura OpenDocument conhecida. O exportador o
monta com a **biblioteca padrão do Python** (`zipfile`,
`xml.sax.saxutils`) — **nenhuma dependência externa foi adicionada**:

| Entrada | Observação |
|---|---|
| `mimetype` | primeira entrada do ZIP, **sem compressão**, valor `application/vnd.oasis.opendocument.text` |
| `content.xml` | texto da minuta convertido de Markdown |
| `styles.xml` | estrutura de estilos mínima |
| `meta.xml` | metadados — **sem datas**, para manter o pacote determinístico |
| `META-INF/manifest.xml` | manifesto do pacote |

O conversor Markdown→ODT cobre apenas o subconjunto que a minuta usa:
títulos, parágrafos, citações, listas, alíneas e a tabela do campo de
revisão humana (convertida em parágrafos com tabulação). Títulos
recebem tratamento diferenciado conforme § 8.5: **cláusulas numeradas**
viram parágrafos de corpo, e apenas **títulos não numerados** (título
do documento, `ENCERRAMENTO`, `CAMPO DE REVISÃO HUMANA`) viram
cabeçalhos ODF. Não é um conversor Markdown completo — *conteúdo
preservado e arquivo editável* tem prioridade sobre formatação
perfeita.

Todas as entradas do ZIP usam data fixa e o `meta.xml` não carrega
timestamps, então o `.odt` é **byte-determinístico** para a mesma
entrada (coberto por teste).

### 8.4. ODT depende de revisão humana — e não é versionado

O `.odt` carrega os mesmos placeholders (`[QUALIFICAÇÃO DO …]`,
`[CNIB_HASH]`, etc.) e o bloco "CAMPO DE REVISÃO HUMANA" da minuta
Markdown. Continua sendo um **rascunho**: o tabelião preenche os
placeholders e revisa antes da lavratura.

- O `.odt` é gravado apenas em `outputs/`, `tmp/`, `.ai_tmp/` ou caminho
  externo autorizado — **nunca é versionado** (assim como o `.md` de
  saída).
- Não há golden binário de `.odt` nesta sprint; a regressão é coberta
  testando a estrutura interna do pacote (ZIP válido, ordem do
  `mimetype`, presença de `content.xml`/`manifest.xml`, placeholders,
  ausência de PII).
- Exportação mais rica (DOCX, estilos avançados, tabelas ODF nativas)
  pode ser refinada em sprint futura — o foco atual é um artefato
  mínimo, seguro, editável e testável.

### 8.5. Padrão cartorário — cláusulas em texto corrido

> **Sprint NOTAS-INVENTARIO-5B.** Ajuste visual do `.odt`: as cláusulas
> numeradas da minuta deixam de ser renderizadas como títulos do
> LibreOffice Writer.

O modelo da serventia é uma minuta cartorária em **texto corrido** — as
cláusulas aparecem apenas **numeradas e destacadas**, não como
cabeçalhos com hierarquia de documento. O exportador segue esse padrão:

- Cláusulas numeradas (`## 1. DA QUALIFICAÇÃO DAS PARTES`,
  `### 10.1. DA MEAÇÃO`, `### 7.2. …`) são renderizadas como
  **parágrafos de corpo** (`text:p`), nunca como `text:h`. O ODT **não**
  aplica estilos de título/cabeçalho do Writer às cláusulas numeradas.
- O rótulo da cláusula (numeração + título, com `:` ao final) recebe o
  estilo de texto `ClauseLabel` — **negrito e sublinhado**, tamanho
  normal. O conteúdo que segue o rótulo permanece texto normal.
- O parágrafo da cláusula usa o estilo `CartorioBody` — corpo
  justificado, herdado de `Standard`, **sem `outline-level` e sem
  espaçamento de título**.
- Títulos **não numerados** seguem como cabeçalhos ODF: o título do
  documento (`# ESCRITURA PÚBLICA …`), `ENCERRAMENTO`, `Assinaturas` e
  `CAMPO DE REVISÃO HUMANA`. São divisores estruturais, não cláusulas.

Os dois estilos vivem em `styles.xml`; a detecção de cláusula numerada
é feita pelo padrão `^\d+(?:\.\d+)*\.\s` aplicado ao texto do título.
A regressão é coberta por `tests/test_notas_inventarios_odt_exporter.py`
(ausência de `text:h` para cláusulas numeradas, estilo de rótulo em
negrito/sublinhado, conteúdo em texto normal, determinismo preservado).

### 8.6. Diretórios de saída — política de organização

Os artefatos `.md`/`.odt`/`.json`/`.pdf` da minuta **nunca são
versionados**. Cada diretório de saída tem um papel definido:

| Diretório | Papel | Versionado? |
|---|---|---|
| `.ai_tmp/` | Arquivos **temporários** de validação de sprint/agente. Descartável a qualquer momento. | Não — gitignored |
| `outputs/` | Saídas locais **manuais da CLI**, para o desenvolvedor abrir e conferir (ex.: `outputs/notas_inventarios/manual/`). | Não — gitignored |
| `exports/atlas/` | **Reservado** à integração futura com o Atlas. Não receber minutas ODT/MD. | Conteúdo gitignored; só `.gitkeep` versionado |
| `tests/golden/notas_inventarios/` | **Único** local de saídas esperadas versionadas (golden files de regressão — § 7.5). | Sim |
| `app/modules/notas/inventarios/examples/` | Entradas de exemplo versionadas (§ 2.8). | Sim |

`.ai_tmp/` e `outputs/` já constam do `.gitignore`. Limpar esses
diretórios é seguro — não há arquivo versionado neles.
