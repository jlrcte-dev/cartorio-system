# POP — Uso do Gerador de Minuta de Inventário

> **Procedimento Operacional Padrão (POP)** — Cartório Costa Teixeira.
> Acompanha o módulo [`notas/inventarios`](../notas_inventarios.md) e o
> [checklist humano](../notas_inventarios_checklist.md).
>
> Sprint **NOTAS-INVENTARIO-POP-1**. Documento estritamente operacional —
> nenhuma regra de negócio do gerador é alterada por este POP.

---

## 1. Finalidade

Este POP descreve, **passo a passo**, como uma pessoa técnica ou semitécnica
da serventia gera uma **minuta-base de inventário extrajudicial** em ambiente
local controlado, a partir de um arquivo estruturado (YAML ou JSON).

A minuta produzida é um **rascunho operacional para conferência humana** —
**nunca é documento final assinado**:

- contém apenas placeholders e cálculos determinísticos;
- não substitui a qualificação completa das partes feita no **Engegraph**;
- não substitui a revisão jurídica do(a) tabelião(ã);
- não substitui o cálculo do ITCMD;
- só é considerada apta à lavratura **depois** de cumprido o checklist em
  [`notas_inventarios_checklist.md`](../notas_inventarios_checklist.md).

O objetivo deste POP é permitir **validação real, controlada e reprodutível**
do gerador, antes que ele entre em uso operacional cotidiano.

---

## 2. Quando usar

- Para gerar minuta-base de **inventário extrajudicial com 1 falecido**
  (único caso suportado no MVP — ver § 3 deste POP).
- Em validação interna do módulo, com **dados fictícios** ou com **dados
  reais previamente autorizados** pelo tabelião e mantidos fora do controle
  de versão.
- Para testar variações já suportadas:
  - inventário **com meeiro(a)** (regime de comunhão, `percentual_meacao`
    entre 0 (exclusivo) e 100);
  - inventário **sem meeiro(a)** (`possui_meeiro: false`).

---

## 3. Quando NÃO usar

- **Sem conferência jurídica posterior.** A minuta exige sempre revisão
  pelo(a) escrevente/tabelião(ã) responsável.
- **Com dados incompletos.** Patrimônio, herdeiros e distribuição devem
  estar fechados antes de gerar a minuta — o gerador é determinístico,
  não estima.
- Como **substituto** da análise jurídica (vocação hereditária, regime de
  bens, validação fiscal, ITCMD).
- Diretamente em **produção** sem antes ter cumprido toda a validação
  manual descrita no [checklist humano](../notas_inventarios_checklist.md).
- Para casos **fora do escopo do MVP**:
  - múltiplos falecidos;
  - sobrepartilha;
  - renúncia ou cessão de direitos hereditários;
  - adjudicação integral;
  - testamento registrado (este caso é judicial);
  - distribuição por valor absoluto (a sprint atual só aceita percentuais).
- Com **dados reais não autorizados** ou em diretórios versionados pelo Git.

---

## 4. Pré-requisitos

Os comandos abaixo assumem PowerShell (ambiente principal de uso). Em bash
equivalente, troque `\`` (continuação de linha do PowerShell) por `\`.

1. **Abrir terminal na raiz do projeto.** A raiz contém o arquivo
   `pyproject.toml`. Conferir:

   ```powershell
   Test-Path pyproject.toml
   ```

   Deve retornar `True`.

2. **Ativar o ambiente virtual** (se houver):

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. **Confirmar a versão do Python.** O projeto exige Python `>=3.12,<3.13`
   (ver `pyproject.toml`):

   ```powershell
   python --version
   ```

4. **Garantir dependências instaladas** (em ambiente novo):

   ```powershell
   pip install -e .[dev]
   ```

5. **Validar que o módulo está acessível** rodando o help da CLI:

   ```powershell
   python -m app.modules.notas.inventarios.interfaces.cli --help
   ```

   O help deve listar os parâmetros `--input`, `--output-dir`,
   `--render-minuta` e `--export-odt`.

---

## 5. Estrutura geral do fluxo

```text
1. Preparar ambiente
2. Criar JSON (ou YAML) de entrada
3. Executar o comando de geração
4. Conferir arquivos gerados
5. Abrir a minuta .odt no LibreOffice Writer
6. Validar conteúdo usando o checklist
7. Registrar problemas encontrados
8. Apagar dados sensíveis, se houver
```

Cada passo é detalhado nas seções abaixo.

---

## 6. Como criar o arquivo de entrada

### 6.1. Onde salvar

O arquivo de entrada deve ficar **fora do controle de versão** para
nunca arrastar dados reais por engano. Os caminhos recomendados:

| Diretório | Quando usar | Versionado? |
|---|---|---|
| `.ai_tmp/inventario_real_001/` | Validação rápida, descartável a qualquer momento. | Não — gitignored |
| `outputs/notas_inventarios/manual/<caso>/` | Validação local com algum tempo de vida (revisão por outra pessoa, repetição com ajustes). | Não — gitignored |
| Caminho **fora do repositório** (ex.: `C:\Users\<seu_user>\inventarios_teste\`) | Quando o caso envolver dados reais autorizados, para distância máxima do Git. | N/A |

Os exemplos **canônicos versionados** ficam em
`app/modules/notas/inventarios/examples/` e contêm **apenas dados
fictícios** — sirva-se deles como ponto de partida, mas **não** salve
sobre eles uma versão com dados reais.

### 6.2. Nome recomendado do arquivo

Padrão sugerido (escolha um e seja consistente):

```text
inventario_<descritor_curto>.json   ou   inventario_<descritor_curto>.yaml
```

Exemplos:

- `inventario_caso_001.json`
- `inventario_teste_simples.yaml`
- `inventario_sem_meeiro_real_autorizado.json`

Não use no nome o nome real do falecido ou de herdeiros. Use identificadores
de caso (números, códigos internos).

### 6.3. Blocos obrigatórios

O contrato de entrada é definido pelo schema Pydantic em
[`app/modules/notas/inventarios/interfaces/schemas.py`](../../../app/modules/notas/inventarios/interfaces/schemas.py).
**Não invente campos** — o schema usa `extra="forbid"` e rejeita qualquer
chave não prevista.

Campos obrigatórios na raiz:

| Campo | Tipo | Regras |
|---|---|---|
| `tipo_ato` | string | **Único valor aceito:** `"inventario_extrajudicial"`. |
| `possui_meeiro` | bool | `true` ou `false`. |
| `percentual_meacao` | string decimal | Se `possui_meeiro=true`: `0 < p ≤ 100`. Se `false`: deve ser `"0"`. |
| `patrimonio_total` | string decimal | Maior que zero. Deve bater com a soma dos `bens.valor` (tolerância ±0,01). |
| `herdeiros` | lista (≥1) | Cada item tem `id` (string única) e `percentual_heranca` (string decimal). |
| `bens` | lista (≥1) | Cada item tem `id`, `tipo`, `valor`, `distribuicao` e, opcionalmente, `descricao_generica`. |

Regras estruturais importantes:

- **Identificador `MEEIRO` é reservado** — não pode ser usado como `id` de
  herdeiro; serve apenas como `beneficiario` na distribuição quando
  `possui_meeiro=true`.
- **Percentuais devem somar 100** (tolerância ±0,01):
  - soma de `herdeiros[*].percentual_heranca` = 100;
  - soma de `bens[*].distribuicao[*].percentual` = 100, **por bem**.
- **`tipo` de cada bem** ∈ `{"imovel", "veiculo", "dinheiro", "direito", "outro"}`.
- **Cada `beneficiario`** na distribuição ∈ `{"MEEIRO"} ∪ {ids dos herdeiros}`.
- Se `possui_meeiro=false`, **nenhum bem** pode ter `MEEIRO` como
  beneficiário.

### 6.4. Cuidados com tipos, datas, CPF, nomes

- **Valores monetários e percentuais** devem ser passados como **string
  decimal** (`"50"`, `"1000000.00"`, `"33.33"`). Isso evita ruído binário
  do `float`. O schema aceita `float` (converte via `str` antes de criar
  `Decimal`), mas a recomendação operacional é **sempre usar strings**.
- **Datas, CPF, RG, endereços, números de matrícula reais** **não** devem
  entrar no arquivo de entrada — eles ficam por conta do **Engegraph**.
  No JSON, use placeholders dentro de `descricao_generica` quando útil
  (ex.: `"Imóvel urbano objeto da matrícula [MATRICULA]"`).
- **Inventariado e inventariante reais** não aparecem na entrada do
  gerador. O módulo recebe apenas `ids` lógicos (`HERDEIRO_1`,
  `IMOVEL_1`, etc.). As qualificações reais são preenchidas depois, no
  Engegraph, sobre os placeholders da minuta gerada.
- **Bens** entram apenas com `id`, `tipo`, `valor` e descrição genérica.
  Matrículas, placas, contas bancárias reais, registros aquisitivos e
  selos digitais ficam para a etapa manual posterior.

### 6.5. Cuidados anti-dados-reais (LGPD)

- **Nunca** usar dados reais para teste de desenvolvimento. Use sempre
  identificadores claramente fictícios (`HERDEIRO_1`, `SALDO_1`,
  `MARIA EXEMPLO`) e valores arredondados que **não** correspondam a um
  caso concreto da serventia.
- Dados reais autorizados só podem ser usados:
  - em ambiente local da máquina autorizada;
  - em diretório gitignored (`.ai_tmp/`, `outputs/`) ou fora do
    repositório;
  - com remoção manual depois da validação (ver § 13).

---

## 7. Exemplos de arquivo de entrada

> Os exemplos abaixo são **fictícios e completos**. Copie-os para um
> arquivo em `.ai_tmp/` ou `outputs/notas_inventarios/manual/...`, ajuste
> e rode a CLI.
>
> **Não** salve esses exemplos sobre os arquivos canônicos em
> `app/modules/notas/inventarios/examples/`.

### 7.1. Exemplo JSON — inventário simples (com meeiro)

```json
{
  "tipo_ato": "inventario_extrajudicial",
  "possui_meeiro": true,
  "percentual_meacao": "50",
  "patrimonio_total": "1000000.00",

  "herdeiros": [
    { "id": "HERDEIRO_1", "percentual_heranca": "50" },
    { "id": "HERDEIRO_2", "percentual_heranca": "50" }
  ],

  "bens": [
    {
      "id": "IMOVEL_1",
      "tipo": "imovel",
      "descricao_generica": "Imóvel urbano objeto da matrícula [MATRICULA]",
      "valor": "600000.00",
      "distribuicao": [
        { "beneficiario": "MEEIRO",     "percentual": "50" },
        { "beneficiario": "HERDEIRO_1", "percentual": "25" },
        { "beneficiario": "HERDEIRO_2", "percentual": "25" }
      ]
    },
    {
      "id": "SALDO_1",
      "tipo": "dinheiro",
      "descricao_generica": "Saldo bancário em instituição financeira [BANCO]",
      "valor": "400000.00",
      "distribuicao": [
        { "beneficiario": "MEEIRO",     "percentual": "50" },
        { "beneficiario": "HERDEIRO_1", "percentual": "25" },
        { "beneficiario": "HERDEIRO_2", "percentual": "25" }
      ]
    }
  ]
}
```

Caso fictício correspondente, para entender o que esse JSON representa
(use **apenas como referência mental** — nada disso entra no JSON):

| Papel | Nome fictício |
|---|---|
| Inventariado(a) | Antônio Exemplo da Silva |
| Meeiro(a) | Maria Exemplo da Silva |
| Herdeiros | João Exemplo, Ana Exemplo |
| Patrimônio | R$ 1.000.000,00 (imóvel urbano + saldo bancário) |
| Regime | Comunhão parcial — meação 50% |

### 7.2. Exemplo JSON — inventário sem meeiro

```json
{
  "tipo_ato": "inventario_extrajudicial",
  "possui_meeiro": false,
  "percentual_meacao": "0",
  "patrimonio_total": "300000.00",

  "herdeiros": [
    { "id": "HERDEIRO_1", "percentual_heranca": "33.33" },
    { "id": "HERDEIRO_2", "percentual_heranca": "33.33" },
    { "id": "HERDEIRO_3", "percentual_heranca": "33.34" }
  ],

  "bens": [
    {
      "id": "IMOVEL_1",
      "tipo": "imovel",
      "descricao_generica": "Imóvel rural objeto da matrícula [MATRICULA]",
      "valor": "200000.00",
      "distribuicao": [
        { "beneficiario": "HERDEIRO_1", "percentual": "33.33" },
        { "beneficiario": "HERDEIRO_2", "percentual": "33.33" },
        { "beneficiario": "HERDEIRO_3", "percentual": "33.34" }
      ]
    },
    {
      "id": "VEICULO_1",
      "tipo": "veiculo",
      "descricao_generica": "Veículo automotor placa [PLACA]",
      "valor": "100000.00",
      "distribuicao": [
        { "beneficiario": "HERDEIRO_1", "percentual": "33.33" },
        { "beneficiario": "HERDEIRO_2", "percentual": "33.33" },
        { "beneficiario": "HERDEIRO_3", "percentual": "33.34" }
      ]
    }
  ]
}
```

Esse caso aciona a política de centavos da
[ADR-009](../../decisions/ADR-009-inventory-cent-rounding-policy.md):
`33,33 + 33,33 + 33,34 = 100,00`, mas a soma das frações por valor
acumula resíduo de centavos — a minuta inclui um alerta técnico
para o tabelião.

### 7.3. Equivalência YAML

Os exemplos canônicos em
[`app/modules/notas/inventarios/examples/`](../../../app/modules/notas/inventarios/examples/)
estão em YAML e funcionam exatamente do mesmo jeito. Para usar YAML,
basta salvar com extensão `.yaml` ou `.yml` e passar o caminho em
`--input`. O loader reconhece a extensão e desserializa.

---

## 8. Como executar a geração da minuta

O comando real e suportado, conforme
[`interfaces/cli.py`](../../../app/modules/notas/inventarios/interfaces/cli.py):

```powershell
python -m app.modules.notas.inventarios.interfaces.cli `
  --input <caminho-do-arquivo-de-entrada> `
  --output-dir <caminho-de-saida> `
  [--render-minuta] `
  [--export-odt]
```

Exemplo concreto para uma validação local com `.odt`:

```powershell
python -m app.modules.notas.inventarios.interfaces.cli `
  --input .ai_tmp\inventario_teste_001\inventario_teste_001.json `
  --output-dir outputs\notas_inventarios\manual\teste_001 `
  --export-odt
```

### 8.1. Parâmetros

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `--input` | sim | Caminho do arquivo YAML/JSON de entrada. Extensões aceitas: `.yaml`, `.yml`, `.json`. |
| `--output-dir` | sim | Diretório onde os arquivos de saída serão gravados. **Whitelist** — ver § 8.2. |
| `--render-minuta` | não | Gera adicionalmente `inventario_minuta.md` (minuta-base com placeholders). Só é produzida quando a validação passa. |
| `--export-odt` | não | Gera `inventario_minuta.md` **e** `inventario_minuta.odt`. **Implica** `--render-minuta` — não é preciso passar os dois juntos. |

### 8.2. Whitelist de `--output-dir`

A CLI **bloqueia** caminhos dentro do repositório que não estejam sob
`outputs/`, `tmp/` ou `.ai_tmp/` (todos gitignorados). Implementação em
[`infrastructure/output_dir.py`](../../../app/modules/notas/inventarios/infrastructure/output_dir.py).

- ✅ `outputs/notas_inventarios/manual/teste_001/`
- ✅ `.ai_tmp/teste_001/`
- ✅ `tmp/teste_001/`
- ✅ `C:\Users\<user>\inventarios_teste\teste_001\` (fora do repositório)
- ❌ `docs/teste_001/` — bloqueado, sai com código `2`.
- ❌ `app/teste_001/` — bloqueado.
- ❌ `tests/golden/teste_001/` — bloqueado.

### 8.3. Códigos de saída

| Exit code | Significado | Ação esperada |
|---|---|---|
| `0` | Validação OK — arquivos gerados. | Abrir a minuta e seguir o checklist. |
| `1` | Validação de negócio falhou. | Ler `inventario_validacao.json`, corrigir a entrada e rodar de novo. **A minuta não é gerada quando o exit é 1.** |
| `2` | Erro de entrada (arquivo ausente, extensão inválida, YAML/JSON malformado, schema rejeitado, `--output-dir` proibido). | Corrigir o arquivo ou o caminho e rodar de novo. |

---

## 9. Onde encontrar os arquivos gerados

Após a execução bem-sucedida, o diretório indicado em `--output-dir`
conterá:

| Arquivo | Quando é gerado | Conteúdo | Quem deve revisar |
|---|---|---|---|
| `inventario_validacao.json` | **Sempre** (mesmo se a validação falhar). | Resultado da validação (`ok`/`erros`) + resumo numérico (patrimônio, meação, monte, quinhões, alerta de centavos). | Quem está rodando — primeiro arquivo a abrir. |
| `inventario_resumo.md` | **Sempre**. | Resumo técnico legível em Markdown — quadros de partilha, totais por beneficiário, alerta de centavos. **Não é a minuta.** | Quem está rodando, para conferência interna. |
| `inventario_minuta.md` | Apenas com `--render-minuta` **ou** `--export-odt`, e somente se a validação passar (exit `0`). | Minuta-base completa em Markdown — §§ 1–20, encerramento, placeholders e bloco "CAMPO DE REVISÃO HUMANA". | Tabelião / escrevente. |
| `inventario_minuta.odt` | Apenas com `--export-odt`, e somente se a validação passar. | Mesma minuta em formato OpenDocument, editável no LibreOffice Writer. | Tabelião / escrevente. |

Diferenças entre os formatos:

- **`.json`** → controle (consumo por humano técnico ou por scripts).
- **`.md`** → fonte canônica e legível da minuta. É o que o renderer
  produz. Edição manual deve ser feita **na minuta `.odt`** ou direto no
  Engegraph — alterar o `.md` perde a próxima regeneração.
- **`.odt`** → artefato derivado, editável no LibreOffice Writer.
  Carrega os mesmos placeholders e cláusulas do `.md`. Ver § 8.3 do
  módulo em [`notas_inventarios.md`](../notas_inventarios.md) para
  detalhes da formatação cartorária.

Os arquivos `.json` e `.md` de resumo são **auxiliares** — servem para
diagnóstico técnico e checagem de cálculos. O arquivo principal para
revisão humana é o **`.odt`** (ou o `.md` da minuta, se preferir leitura
em texto puro).

---

## 10. Checklist de conferência da minuta

> Este é o checklist **resumido** para a validação técnica do POP. O
> checklist completo (18 blocos, cobrindo todas as cláusulas) está em
> [`notas_inventarios_checklist.md`](../notas_inventarios_checklist.md).
> **Cumprir os dois.**

### 10.1. Dados das partes

- [ ] Nome do(a) inventariado(a) e qualificação completa (a serem
  preenchidos no Engegraph) — placeholders `[QUALIFICAÇÃO DO AUTOR DA
  HERANÇA]` corretos na minuta.
- [ ] CPF e RG do inventariado coerentes com o documento de óbito.
- [ ] Estado civil ao tempo do óbito coerente com a flag
  `possui_meeiro` e com `percentual_meacao`.
- [ ] Data e local de óbito conferidos com a certidão.
- [ ] Inventariante nomeado em § 6 está entre os herdeiros listados em
  `herdeiros[]`.
- [ ] Lista de herdeiros confere com a vocação hereditária do caso real
  (a vocação é validada manualmente — o sistema apenas reflete
  `herdeiros[]`).
- [ ] Meeiro(a) **incluído** quando `possui_meeiro: true` — § 1.2 e
  § 10.1 presentes.
- [ ] Meeiro(a) **ausente** quando `possui_meeiro: false` — §§ 10.1 e
  10.2 ausentes; nenhum bem com beneficiário `MEEIRO`.

### 10.2. Bens

- [ ] Todos os bens reais do espólio foram listados na entrada.
- [ ] Matrículas, endereços, contas bancárias, placas — os placeholders
  estão claramente marcados (a serem preenchidos manualmente).
- [ ] Valores transportados sem erro de digitação (conferir contra os
  documentos de avaliação).
- [ ] Percentuais de distribuição por bem somam 100 (tolerância ±0,01).
- [ ] Quinhões fazem sentido para o regime de bens e para a vocação
  hereditária do caso.

### 10.3. Texto jurídico

- [ ] Qualificações estão coerentes e cada placeholder está identificável.
- [ ] Estrutura da minuta está completa (§§ 1 a 20 + encerramento) — sem
  bloco faltando.
- [ ] Não restam campos vazios ou placeholders **fora** dos blocos
  esperados (qualificações, certidões, CNIB, ITCMD, matrícula etc.).
- [ ] Não há texto duplicado entre cláusulas.
- [ ] Não há trechos incompatíveis com o caso (ex.: § de meação na
  minuta sem meeiro).

### 10.4. Arquivo gerado

- [ ] O `.odt` abre corretamente no LibreOffice Writer.
- [ ] Formatação aceitável: cláusulas numeradas como parágrafos de corpo
  com rótulo em negrito e sublinhado (padrão cartorário); títulos não
  numerados como cabeçalhos.
- [ ] Sem caracteres quebrados ou acentos errados (verificar `ç`, `ã`,
  `é`, etc.).
- [ ] Documento pronto para revisão humana posterior no Engegraph.

---

## 11. Checklist de segurança e LGPD

- [ ] **Não** estão sendo usados dados reais fora do ambiente
  autorizado pela serventia.
- [ ] **Nenhuma** minuta com dados reais está salva em pasta versionada
  pelo Git. O `git status` (§ 12) não mostra arquivos com PII.
- [ ] **Nenhum** JSON com dados pessoais foi cometido (`git status` está
  limpo do lado da pasta de testes).
- [ ] Arquivos gerados **não** foram compartilhados fora dos canais
  internos da serventia.
- [ ] Os arquivos temporários em `.ai_tmp/`/`outputs/` serão apagados
  quando a validação encerrar (ver § 13).
- [ ] Para testes de desenvolvimento, **somente dados fictícios** estão
  sendo usados.

> Diretrizes operacionais permanentes vivem em [`CLAUDE.md`](../../../CLAUDE.md)
> e em
> [`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../../../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md).
> Em caso de conflito, prevalece o que estiver mais restritivo.

---

## 12. Registro de problemas encontrados

Use o modelo abaixo para registrar cada execução de validação. Salve-o
**fora do controle de versão** (mesmas regras de § 6.1).

```markdown
## Registro de Validação

- Data:
- Responsável:
- Tipo de inventário (com / sem meeiro / outro):
- Arquivo JSON usado (apenas nome local, sem PII):
- Comando executado:
- Arquivos gerados (lista de arquivos no --output-dir):
- Resultado (exit code + leitura de inventario_validacao.json):
- Problemas encontrados:
  - [ ] ...
  - [ ] ...
- Ajustes necessários (na entrada, na CLI ou no módulo):
- Prioridade (baixa / média / alta / bloqueador):
- Observações (placeholders confusos, formatação ODT, divergências de
  centavos, etc.):
```

Quando algum problema apontar para o **módulo** (e não para a entrada),
escalar via canal interno de issues do projeto — **sem anexar dados
reais** no registro.

---

## 13. Troubleshooting

| Problema | Possível causa | Como resolver |
|---|---|---|
| `No module named app.modules...` ao rodar a CLI | Terminal não está na raiz do projeto **ou** o ambiente virtual não foi ativado / dependências não instaladas. | `cd` para a raiz do repositório, ativar `.venv`, rodar `pip install -e .[dev]`. |
| `arquivo não encontrado: ...` (exit `2`) | Caminho do `--input` errado, arquivo não existe. | Conferir o caminho. Em PowerShell, evitar contrabarras escapadas — usar `\` simples. |
| `extensão não suportada: '.txt' ...` (exit `2`) | Arquivo de entrada com extensão fora de `.yaml`/`.yml`/`.json`. | Renomear ou recriar o arquivo com extensão correta. |
| `YAML inválido em ...` ou `JSON inválido em ...` (exit `2`) | Vírgula faltando, aspas erradas, indentação YAML quebrada. | Validar o arquivo com um linter (`python -c "import json,sys; json.load(open(r'<path>'))"`). Comparar com o exemplo em § 7. |
| `extra forbidden` para algum campo no erro de entrada (exit `2`) | Foi adicionado um campo que o schema não conhece (`extra="forbid"`). | Remover o campo. O contrato vive em [`interfaces/schemas.py`](../../../app/modules/notas/inventarios/interfaces/schemas.py). |
| `tipo inválido: '<x>'. Valores aceitos: ...` (exit `2`) | `bens[].tipo` fora do enum (`imovel`, `veiculo`, `dinheiro`, `direito`, `outro`). | Usar um dos valores listados. |
| `percentual_meacao deve ser 0 quando possui_meeiro=false` (exit `1`) | `possui_meeiro: false` com `percentual_meacao != 0`. | Acertar a coerência: se não há meeiro, `percentual_meacao` deve ser `"0"`. |
| `'MEEIRO' é um identificador reservado ...` (exit `1`) | `id` de herdeiro igual a `MEEIRO`. | Renomear o herdeiro (`MEEIRO` só pode aparecer como `beneficiario` em `distribuicao`). |
| `Soma dos percentuais de herança deve ser 100 ...` (exit `1`) | Erro de digitação nos percentuais de herança. | Corrigir até a soma bater 100 ±0,01. |
| `Soma dos valores dos bens (...) difere do patrimonio_total declarado (...)` (exit `1`) | `patrimonio_total` não bate com `Σ bens.valor`. | Recalcular o patrimônio total ou os valores dos bens. |
| `bem '...': beneficiário '...' não consta na lista de herdeiros` (exit `1`) | `id` de beneficiário em `distribuicao` não existe em `herdeiros[]`. | Conferir e corrigir o `id`. Se for o meeiro, usar literalmente `MEEIRO` (caixa alta). |
| `--output-dir '...' aponta para '...' dentro do repositório, diretório não permitido` (exit `2`) | Caminho de saída fora da whitelist (`outputs/`, `tmp/`, `.ai_tmp/`). | Mover a saída para um diretório permitido (§ 8.2). |
| `[atencao] divergencia de centavos: ...` (exit `0`) | Política de centavos: percentuais como `33,33%×3` acumulam resíduo. | Não é erro — é **alerta** ([ADR-009](../../decisions/ADR-009-inventory-cent-rounding-policy.md)). Revisar a partilha bem a bem antes da lavratura. |
| Arquivo `.odt` não foi gerado | `--export-odt` ausente, ou validação falhou (exit `1`). | Adicionar `--export-odt`; ler `inventario_validacao.json` para corrigir a entrada. |
| Minuta abre com `[QUALIFICAÇÃO DO ...]` em toda parte | É esperado — placeholders só são preenchidos depois, no Engegraph. | Seguir o fluxo: minuta gerada → Engegraph → revisão final. |

Para erros não cobertos acima, ler o `stderr` impresso pela CLI e
inspecionar o `inventario_validacao.json` — todas as mensagens são
pensadas para serem autoexplicativas.

---

## 14. Fluxo mínimo recomendado para a primeira validação real

1. Criar pasta de teste local **ignorada pelo Git**:

   ```powershell
   New-Item -ItemType Directory -Force `
     .\.ai_tmp\inventario_teste_001 | Out-Null
   ```

2. Copiar um exemplo canônico para servir de ponto de partida:

   ```powershell
   Copy-Item `
     app\modules\notas\inventarios\examples\inventario_simples.yaml `
     .ai_tmp\inventario_teste_001\inventario_teste_001.yaml
   ```

3. Preencher dados **fictícios** (ou reais previamente autorizados, sob
   as regras de § 11) editando o arquivo copiado. **Não** alterar o
   arquivo original em `examples/`.

4. Rodar a CLI:

   ```powershell
   python -m app.modules.notas.inventarios.interfaces.cli `
     --input .ai_tmp\inventario_teste_001\inventario_teste_001.yaml `
     --output-dir outputs\notas_inventarios\manual\teste_001 `
     --export-odt
   ```

5. Abrir o `.odt`:

   ```powershell
   Invoke-Item outputs\notas_inventarios\manual\teste_001\inventario_minuta.odt
   ```

6. Aplicar o checklist resumido (§ 10 deste POP) **e** o checklist
   completo em
   [`notas_inventarios_checklist.md`](../notas_inventarios_checklist.md).

7. Registrar problemas usando o modelo de § 12.

8. Apagar os arquivos sensíveis, se houver:

   ```powershell
   Remove-Item -Recurse -Force `
     .ai_tmp\inventario_teste_001, `
     outputs\notas_inventarios\manual\teste_001
   ```

   Confirmar com `git status` (§ 12 deste POP) que nada sobrou na área
   versionada.

---

## 15. Critérios de pronto da sprint POP

Esta sprint estará **pronta** quando todos os itens abaixo forem
verdadeiros:

- [ ] POP criado em
  [`docs/modules/notas_inventarios/POP_USO_GERADOR_MINUTA_INVENTARIO.md`](POP_USO_GERADOR_MINUTA_INVENTARIO.md)
  (este arquivo).
- [ ] Comando real `python -m app.modules.notas.inventarios.interfaces.cli`
  documentado, com parâmetros e exit codes verificados contra o código.
- [ ] Ao menos um JSON exemplo **completo e fictício** presente neste
  POP (§ 7).
- [ ] Checklist de validação visível e operacional (§ 10), com link
  para o checklist completo (§ 1).
- [ ] Procedimento orienta como evitar versionamento de dados reais
  (§§ 6.1, 11, 13, 14).
- [ ] `ruff check .` e `ruff format --check .` passam.
- [ ] `pytest` passa (ao menos a suíte do módulo `notas/inventarios` —
  ver § 16 deste POP).
- [ ] `git status` final mostra **apenas** os arquivos documentais
  esperados (este POP e, se criada, a pasta `docs/modules/notas_inventarios/`).
- [ ] Nenhuma lógica do gerador foi alterada por esta sprint.

---

## 16. Como rodar somente os testes do módulo

Para iteração rápida durante a validação:

```powershell
pytest tests/test_notas_inventarios_calculator.py `
       tests/test_notas_inventarios_validator.py `
       tests/test_notas_inventarios_renderer.py `
       tests/test_notas_inventarios_schemas.py `
       tests/test_notas_inventarios_golden.py `
       tests/test_notas_inventarios_odt_exporter.py `
       tests/test_notas_inventarios_output_dir.py `
       -q
```

Atalho equivalente via glob (mesmo conjunto):

```powershell
pytest tests/test_notas_inventarios_*.py -q
```

A suíte completa do projeto (`pytest -q`) continua sendo o critério
final antes de considerar qualquer mudança pronta — ela cobre a
interação dos módulos `audit`, `lgpd`, `compliance`, `retention`,
`finance` e `notas`, garantindo que esta sprint documental **não**
quebrou nada por acidente.
