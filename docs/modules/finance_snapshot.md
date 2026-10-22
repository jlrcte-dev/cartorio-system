# Leitura local do Financeiro (`finance_snapshot`)

**Estado (2026-10-22):** leitor **offline** e experimental do demonstrativo diário de caixa,
sobre uma captura já feita pelo [coletor](drive_capture.md). Ele não coleta, não usa rede
nem credencial, não exporta para o Atlas e não tem transporte nem agendamento. A fonte é
uma **cópia de desenvolvimento**, sem atualização periódica.

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

## Limites

- Cancelamentos e estornos não são registrados na fonte.
- Não há consolidação entre blocos ou meios, saldo global, conciliação nem integração
  com o Atlas ou com o Finance pessoal.
- Os resultados descrevem a cópia lida, não a operação atual.
