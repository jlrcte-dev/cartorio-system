# Leitura local do Financeiro (`finance_snapshot`)

**Estado (2026-10-22):** leitor **offline** e experimental do demonstrativo diário de caixa,
sobre uma captura já feita pelo [coletor](drive_capture.md). Ele não coleta, não usa rede
nem credencial e não tem transporte nem agendamento. A fonte é uma **cópia de
desenvolvimento**, sem atualização periódica. O `export-atlas` (abaixo) grava, localmente,
um arquivo com contrato próprio para um futuro consumidor no Atlas; **ainda não há
consumidor, transporte nem ativação produtiva** (ADR-012, Proposto).

## Uso

```bash
python -m app.modules.finance_snapshot.cli analyze \
    --config <config isolada da fonte financeira> \
    --run-id <run da captura> \
    --periodo AAAA-MM
```

Os três argumentos são obrigatórios: não há config, run nem período padrão.

- A config precisa ter **uma** fonte da família `gerenciamento_financeiro` e nenhuma
  pasta. Qualquer outra é recusada antes de ler conteúdo.
- O run precisa ser o da última captura daquela fonte. Run, manifesto, tamanho e SHA-256
  são conferidos sobre os mesmos bytes interpretados, pelo mesmo vínculo do retrato de
  serviços. Nenhuma outra captura é buscada.
- Códigos de saída:
  - `0`: relatório local validado e publicado, mesmo com lacunas declaradas;
  - `2`: falha técnica, com etapa e código controlados. O relatório anterior é
    preservado, exceto em `publicacao_inconsistente` (abaixo), em que a CLI diz o estado
    real.
- **Publicação.** Depois da validação:
  1. o Markdown é gerado e os dois arquivos vão para `.staging`;
  2. `latest.md` é promovido;
  3. `latest.json` é promovido — **ponto de commit**.

  Falhar na geração (`markdown_nao_gerado`), na gravação em staging ou em qualquer das
  duas trocas (`falha_ao_publicar`) deixa o par anterior intacto: se a troca do JSON
  falha, o Markdown anterior é restaurado (ou removido, se não havia). Só se essa
  restauração também falhar o código é `publicacao_inconsistente`: `latest.json`
  continua o anterior, mas `latest.md` é o da tentativa recusada e precisa ser
  regenerado.
- O terminal mostra só contagens e códigos.

## Saída: `cartorio_system.finance_snapshot.local` 0.1

A saída fica em `<data_dir>/finance_snapshot/`: `latest.json` (autoritativo) e
`latest.md`, gerado a partir do JSON validado. São **privados**: trazem valores agregados
por bloco e dia, mas nunca registro individual, descrição, nome, protocolo ou nome de aba.

- **Esquema fechado:** chaves fixas e enumerações; dinheiro em decimal canônico (texto
  `-?\d+(\.\d+)?` sem zeros finais, sem arredondar).
- **Reconciliação:** a cobertura e as checagens precisam ser exatamente o recálculo a
  partir das abas.
- **Valor indisponível:** é `null` com motivo (`vazio`, `formula_sem_resultado`,
  `erro_de_formula`, `nao_numerico`, `numero_invalido`, `formato_de_data`,
  `bloco_indisponivel`, `total_nao_confirmado`, `sem_conferencia`,
  `conferencia_indisponivel`). Nunca vira zero; zero digitado continua zero.
- **Marcador de hífens = vazio** (aprovado pelo operador em 22/10/2026): texto digitado
  formado só por hífens ASCII (`-`, `-----`), sem os espaços externos, é ausência de
  valor. Não vira zero: em caixa inicial ou saldo conferido continua `null` (`vazio`), sem
  base de continuidade nem conferência. Outros traços (`–`, `—`), hífens com outro
  caractere, resultado de fórmula e qualquer outro texto continuam `nao_numerico`. Linha
  só de marcadores não é movimentação.
- **Linha descrita sem valor:** linha com descrição e nenhum valor utilizável nas
  colunas de valor do bloco deixa a soma diagnóstica do bloco `parcela_incompleta`. Vale
  para qualquer forma de ausência: célula ausente, vazia, em branco ou marcador de
  hífens. Uma só coluna preenchida (entrada **ou** saída) já é valor. Linha sem
  descrição continua ignorada. No protesto, o texto pré-impresso do modelo "Protocolo nº"
  (exato, sem número) não é descrição (aprovado pelo operador).
- **`blocos.pix.formula_do_total`**: `cobre_o_bloco`, `omite_linhas` (a fórmula SUM legível
  do total não alcança todas as linhas do bloco) ou `nao_verificavel` (total digitado ou
  fórmula ilegível); `null` com o bloco não localizado. Depende só da fórmula, nunca dos
  valores. Havendo alguma aba `omite_linhas`, `limitacoes` recebe
  `pix_total_publicado_omite_linhas_do_bloco`, a cobertura conta as abas em
  `pix_formula_do_total`, e o Markdown traz o aviso e marca o PIX dessas abas.

## Regras de leitura

- **Uma aba é um dia.** A data vem do nome `ddmm` no período informado; a data do corpo
  ("Movimentação do caixa dia") só é comparada.
- **Sufixos aprovados:** apenas `feriado`.
- **Leitura por âncora**, nunca por endereço. A correspondência é exata depois de
  normalizar acentos, caixa, espaços e variantes de hífen. Os rótulos aprovados estão em
  `layout.py`.
- **"Total em transferências" é o total da maquininha** (confirmado pelo operador): é
  procurado só na coluna de rótulo do bloco da maquininha, abaixo do cabeçalho "Valor a
  receber"/"Valor cobrado"; o total a receber vem da coluna "Valor a receber" e o cobrado
  da coluna "Valor cobrado". O PIX usa só o rótulo exato "Total", na sua própria coluna.
- **Âncora ausente ou repetida** na sua região deixa o bloco indisponível. A primeira
  ocorrência nunca é escolhida.
- **"Célula seguinte"** respeita a faixa mesclada do rótulo, e o valor precisa começar
  ali. Por isso o parser seguro passou a expor as mesclas (`Sheet.merges`).
- **Valores:** são os gravados pela planilha, convertidos para `Decimal` a partir do texto
  do XML. Nenhuma fórmula é avaliada.
  - Saída é positiva na coluna Saída.
  - Caixa inicial e saldo teórico são saldos; o malote não é somado a nada.
- **Totais:** são as células publicadas. No dinheiro, a linha de totais é a imediatamente
  acima de "Retirada para malote", sem descrição; com descrição, os totais ficam
  `total_nao_confirmado`.

| Bloco | Campos por dia |
|---|---|
| Dinheiro | caixa inicial, n.º de registros, totais de entradas e saídas, malote, saldo teórico, saldo conferido, diferença válida |
| Verificação do caixa | verificações preenchidas (horário + valor + quem conferiu) e incompletas; nunca nomes |
| PIX/transferências | total publicado |
| Repasses de protesto | n.º de registros; totais recebido, repassado e de emolumentos (bloco do demonstrativo, **não** a família `protestos`) |
| Maquininha | totais a receber e cobrado |

## Estados, temporalidade e checagens

Os estados abaixo estão em ordem de precedência:

1. `ignorada`: nome sem `ddmm`, data inválida ou fora do período. É reavaliada se o nome
   for corrigido.
2. `fora_do_padrao`: sufixo não aprovado, data repetida ou bloco não localizado.
3. `feriado`: valores preservados.
4. `preenchido`: algum registro não nulo em dinheiro, malote, PIX, protesto ou cartão.
5. `sem_lancamento`: nada disso **na cópia**. Não quer dizer que não houve movimento.

A temporalidade (`anterior`, `referencia`, `futura`) usa a data da captura em
America/Sao_Paulo. Aba futura não recebe checagem.

Checagens. São sinais para conferência, nunca conclusão sobre caixa ou colaborador:

- **Conferência:** a diferença só vale com saldo conferido numérico (zero incluído),
  saldo teórico e diferença disponíveis. Sem contagem manual, o estado é
  `sem_conferencia`, mesmo com a fórmula presente.
- **Continuidade:** compara o caixa inicial com o saldo teórico da aba de data
  imediatamente anterior, por data. Não pula aba fora do padrão nem data ambígua, e
  registra a data-base e os dias desde ela. A base só vale com caixa inicial e saldo
  teórico próprios (`base_sem_saldo` caso contrário).
- **Soma × total:** soma `Decimal` só como diagnóstico; o total exibido é sempre a célula
  publicada. Fica indisponível com parcela inválida, parcela incompleta, parcela por
  fórmula ou subtotal no perímetro.
  - **PIX:** o perímetro de negócio aprovado é o bloco inteiro (todas as linhas de
    movimentação, sem cabeçalho nem total). A soma de todas as linhas é comparada com o
    total publicado mesmo quando a fórmula da fonte omite linhas: `diverge` é sinal
    conhecido da fonte, não falha da execução, e `confere` não corrige a fórmula.
  - **Demais blocos:** fórmula SUM legível que deixa de fora linha preenchida torna a
    comparação `perimetro_divergente`.
- **Data do corpo × nome:** a divergência é apenas apontada.

## Exportação para o Atlas (`export-atlas`)

```bash
python -m app.modules.finance_snapshot.cli export-atlas \
    --config <config isolada da fonte financeira> \
    --run-id <run esperado do relatório> \
    --periodo AAAA-MM
```

Os três argumentos são obrigatórios: nenhum run é descoberto e nenhum período é escolhido.
Lê **só** `<data_dir>/finance_snapshot/latest.json`, uma vez. Não lê `latest.md`, não abre o
XLSX, não roda `analyze`, não coleta, não autentica e não usa rede; funciona mesmo sem as
gerações retidas pelo coletor. Grava `<data_dir>/finance_snapshot/atlas_snapshot.json`,
**privado** (agregados diários com valores). O arquivo de serviços, em
`services_snapshot/`, não é tocado.

| Saída | Significado |
|---|---|
| 0 | exportação válida publicada, inclusive com lacunas, dias futuros e alertas do PIX |
| 2 | falha técnica ou entrada recusada, com código controlado (abaixo) |
| 3 | nenhum relatório (`sem_relatorio`): rode `analyze` com a mesma config, run e período. Nada é exportado e o diretório não é criado |
| 4 | outra exportação financeira em andamento (`exportacao_em_andamento`) |

Não há saída 5: ela existe nos serviços para um formato legado que o financeiro não tem.

**Vínculo e validação, nesta ordem:**

1. A config precisa ter uma fonte `gerenciamento_financeiro` e nenhuma pasta, pela mesma
   regra do `analyze` (`fora_do_recorte_financeiro`). Isso é conferido antes de abrir
   conteúdo.
2. JSON em UTF-8. Chave duplicada, `NaN`/`Infinity` e número não finito são recusados
   (`entrada_invalida`). Formato ou versão diferentes de
   `cartorio_system.finance_snapshot.local` 0.1 dão `formato_nao_suportado`. Depois vem o
   `validate_report` do formato local (`entrada_invalida`).
3. `fonte_alias`/`familia` são conferidos contra a fonte configurada
   (`fonte_divergente`), o run contra `--run-id` (`run_divergente`) e o período contra
   `--periodo` (`periodo_divergente`).
4. O objeto é montado campo a campo e validado contra o contrato inteiro
   (`exportacao_invalida`). Tempos e datas são validados como valores, não como texto
   (`inconsistencia_temporal`):
   - instantes com fuso, com captura ≤ geração do relatório ≤ exportação;
   - referência igual à data civil da captura em America/Sao_Paulo;
   - datas civis válidas dentro do período;
   - temporalidade coerente com a referência.

   O período **não** precisa ser o mês da captura: uma captura posterior pode trazer um
   período passado.

A procedência é a **declarada no relatório validado**. O vínculo aos bytes do XLSX
(manifesto, tamanho, SHA-256) foi feito pelo `analyze` e **não** é refeito aqui. O
exportador não reconfere a captura no Drive, e o arquivo não tem assinatura nem promessa de
autenticidade.

**Publicação.** O JSON é serializado e relido antes da gravação. Depois vem a troca
atômica privada do coletor (`atomic_write_bytes`). Se ela falhar, o estado do arquivo é
**conferido em disco** e a CLI diz qual é:

- `preservada`: a exportação anterior está intacta, byte a byte;
- `ausente`: não havia exportação anterior e nenhum arquivo final foi criado;
- `substituida` (`gravado_com_falha_posterior`): a troca concluiu e a falha veio depois,
  na limpeza do temporário. O arquivo já é a nova exportação validada e a anterior não
  existe mais;
- `indeterminado`.

Falhas antes da gravação (`leitura_falhou`, `falha_ao_serializar`, recusas) não tocam o
arquivo final. O `latest.json` e o `latest.md` nunca são modificados.

**Trava.** `finance_snapshot/run.lock` (o `RunLock` do coletor) impede **outra exportação**
ao mesmo tempo. O `analyze` **não** usa essa trava. A consistência vem de ler um único
`latest.json`, promovido atomicamente pelo `analyze`, que precisa ser do run e do período
pedidos. Trava alheia nunca é removida. Uma trava órfã, de processo interrompido, exige
remoção manual, depois de conferir que nenhuma exportação está rodando. Se a exportação
publicar mas não conseguir soltar a trava, o código é `trava_nao_removida`: o arquivo já
foi publicado.

**Reexportar** muda só `tempos.exportado_em`. Captura, geração do relatório, referência e
limitações continuam as do relatório: exportar de novo não renova a captura nem atesta
atualidade operacional ou qualidade financeira.

### Contrato `cartorio_system.atlas.finance_snapshot` 1.0

Exemplo sintético completo, gerado pelo próprio exportador com relógio fixo:
[`finance_snapshot_atlas.example.json`](finance_snapshot_atlas.example.json). Um teste
recusa divergência entre o exemplo e o código.

As chaves são fixas em todos os níveis. O texto é só enumeração ou formato técnico. Valor
monetário é `{valor, motivo}`: decimal canônico em texto, ou `null` com motivo, nunca zero.
Contagens são inteiros não negativos, nunca booleanos.

| Campo | Conteúdo |
|---|---|
| `formato`, `versao` | `cartorio_system.atlas.finance_snapshot`, `1.0` |
| `origem` | `formato_local`, `versao_local` (`0.1`), `escopo` (`fonte_financeira_unica`), `fonte_alias`, `familia` (`gerenciamento_financeiro`), `run_id` |
| `periodo` | `AAAA-MM`, igual ao relatório e ao `--periodo` |
| `tempos` | `capturada_em`, `relatorio_gerado_em` (copiados do relatório, ISO 8601 com `Z` ou deslocamento), `exportado_em` (UTC), `referencia_indicadores` (AAAA-MM-DD), `fuso_referencia` (`America/Sao_Paulo`) |
| `limitacoes` | os cinco códigos fixos do relatório e, se alguma aba tem `omite_linhas`, `pix_total_publicado_omite_linhas_do_bloco` |
| `cobertura` | as contagens do relatório: `abas_total`, por estado, por temporalidade (com `sem_data`), datas interpretadas e repetidas, abas com campo indisponível, campos indisponíveis por motivo, valores com mais de duas casas, localização por bloco, `pix_formula_do_total` |
| `checagens` | totais de conferência (`valida_zero`, `valida_nao_zero`, `sem_conferencia`, `indisponivel`, `nao_aplicavel`), continuidade, soma × total por campo e data do corpo |
| `dias[]` | um item por aba do relatório, **na ordem**: `posicao`, `data`, `estado`, `motivo_estado`, `temporalidade`, `blocos`, `checagens` |

Campos por bloco, além de `localizado` e `motivo`:

| Bloco | Campos |
|---|---|
| `dinheiro` | `caixa_inicial`, `registros`, `total_entradas`, `total_saidas`, `retirada_malote`, `saldo_teorico`, `saldo_conferido`, `diferenca` |
| `verificacao` | `preenchidas`, `incompletas` |
| `pix` | `total` (o publicado), `formula_do_total` |
| `protesto` | `registros`, `total_recebido`, `total_repassado`, `total_emolumentos` |
| `maquininha` | `total_a_receber`, `total_cobrado` |

Por dia, `checagens` traz:

- `conferencia`: `estado`, `motivo` e `sinal`;
- `continuidade`: `estado`, `motivo`, `base_data` e `dias_desde_base`;
- `soma`: `estado` e `motivo` por campo;
- `data_corpo`: `estado` e `motivo`.

`dias[]` é uma **lista**, não um mapa por data. Itens `ignorada` continuam presentes, com
`data`, `temporalidade` e `blocos` em `null`. Datas repetidas aparecem uma vez por aba.

**Coerência conferida** (divergência recusa o objeto, nunca o corrige):

- **Contagens:** cobertura, checagens e limitações são recontadas a partir de `dias[]`.
- **Blocos:** bloco não localizado tem motivo, contagens `null` e campos
  `bloco_indisponivel`. Dia elegível tem todos os blocos localizados.
- **Aplicabilidade:** dia `ignorada`, `fora_do_padrao` ou futuro tem todas as checagens
  `nao_aplicavel`, com o motivo correspondente.
- **Conferência:** `valida` exige diferença, saldo conferido e saldo teórico numéricos, e o
  `sinal` precisa corresponder à diferença. `sem_conferencia` exige saldo conferido vazio.
- **Continuidade:** a base é a data imediatamente anterior entre as exportadas, e
  `dias_desde_base` é a distância real. O estado precisa ser o único compatível com os
  campos, na precedência do leitor:
  1. `sem_base`;
  2. `base_ambigua` (data-base repetida);
  3. `base_fora_do_padrao` (base inelegível);
  4. `base_sem_saldo` (base sem caixa inicial ou sem saldo teórico próprio);
  5. `caixa_inicial_indisponivel`;
  6. com tudo disponível, `confere` se o caixa inicial é igual (em `Decimal`) ao saldo
     teórico da base, e `diverge` se não é.

  A comparação só aceita ou recusa o objeto; nunca corrige o estado.
- **Soma × total:** `total_indisponivel` vale se e somente se o total publicado é `null`.

Nada é recalculado a partir do XLSX nem de fórmulas.

**Fora do contrato:** nomes de abas, lançamentos, descrições, nomes, protocolos, IDs ou
URLs do Drive, caminhos locais e credenciais. A versão e o `modifiedTime` do Drive, o
tamanho e o SHA-256 do XLSX ficam só no relatório privado de origem. O contrato também
**não** traz bloco de atualização: não existe registro de tentativas financeiras
equivalente ao `last_attempt.json` dos serviços. Por isso ele não informa tentativa
posterior nem confirma atualização. As enumerações são declaradas no exportador, e um teste
avisa quando o formato local mudar. Mudança no contrato exige versão nova e decisão
própria.

## Limites

- Cancelamentos e estornos não são registrados na fonte.
- Não há consolidação entre blocos ou meios, saldo global, conciliação nem integração
  com o Finance pessoal. A exportação para o Atlas é só um arquivo local: não há
  consumidor no Atlas, transporte, agendamento nem ativação produtiva.
- Os resultados descrevem a cópia lida, não a operação atual.
