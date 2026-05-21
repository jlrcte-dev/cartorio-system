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

### 2.9. Proposta de template genérico seguro

O template versionado em
`app/modules/notas/inventarios/infrastructure/templates/inventario_extrajudicial_padrao.md.j2`
contém **apenas placeholders e cláusulas fixas**. Nenhum trecho com dados reais é
versionado.

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

Saídas (sempre em `outputs/inventarios/`, gitignorado):

- `inventario_validacao.json` — resultado da validação (ok/erros) + resumo dos cálculos.
- `inventario_resumo.md` — **resumo técnico** legível com placeholders (NÃO é a minuta
  completa; texto cartorário do §§ 1 a 20 fica para sprint futura).

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

1. **NOTAS-INVENTARIO-2**: implementar renderização completa do template com Jinja2,
   ainda sem PII (apenas placeholders).
2. **NOTAS-INVENTARIO-3**: variações condicionais (sem meeiro, sem débitos, com débitos,
   advogados múltiplos).
3. **NOTAS-INVENTARIO-4**: schema Pydantic + validações tipadas + cobertura de testes
   estendida (golden files).
4. **NOTAS-INVENTARIO-5**: pacote `infrastructure/exporters/` para gerar `.docx` ou
   `.odt` a partir do Markdown — preservando placeholders para preenchimento manual.
5. **ADR obrigatório** quando: definir contrato de import (campos vindos do Engegraph),
   definir formato de saída versionável (markdown vs odt vs docx), integrar com módulo
   de selo digital / arquivamento.

---

## 5. Riscos remanescentes

- O template versionado é simplificação do modelo original. Antes da Sprint 2, o
  tabelião deve revisar `inventario_extrajudicial_padrao.md.j2` e validar o texto
  fixo das cláusulas §§ 14, 15, 17, 18, 19, 20.
- Tolerância de centavos (`±0,01`) pode mascarar erros de digitação em valores
  grandes. Avaliar uso de tolerância proporcional em sprint futura.

---

## 6. Política de centavos — decisão temporária

A combinação de percentuais (ex.: `33,33% × 3 = 99,99%`) faz com que a soma do
que é efetivamente distribuído possa diferir do patrimônio total em alguns
centavos. **Esta sprint não corrige essa diferença automaticamente** — em vez
disso:

1. O calculador retorna `ResumoInventario.divergencia_centavos` com o valor
   absoluto da diferença.
2. O JSON de validação (`inventario_validacao.json`) expõe sempre o campo
   `resumo.divergencia_centavos`, e adiciona um objeto `alerta_centavos` no nível
   raiz quando há divergência.
3. O resumo Markdown inclui uma seção "⚠ Alerta de centavos" quando aplicável.
4. A CLI imprime um aviso em `stderr` (sem alterar o exit code).

**Não corrigir silenciosamente é a regra.** A próxima sprint deve decidir entre:

- **(a) Alerta apenas** — fluxo atual; obriga o tabelião a ajustar manualmente
  por valor (não por percentual) quando a divergência for inaceitável.
- **(b) Ajuste controlado** — atribuir o centavo residual a um beneficiário
  pré-definido (ex.: último herdeiro listado) com registro explícito no relatório.
- **(c) Distribuição por valor** — passar a aceitar entrada por valor absoluto
  (`R$`) por bem/beneficiário em vez de percentual, eliminando arredondamento.

A escolha entre (a), (b) e (c) impacta contrato de entrada e formato de saída —
exige **ADR** antes de implementar.
