# Retrato de serviços por setor e status (`services_snapshot`)

**Estado (2026-10-21):** atualização manual local da **única planilha piloto**
(`documentos_em_andamento`), com indicadores temporais agregados (formato local 1.1).
Sem agendamento, sem consumidor no Atlas. Depende do coletor
[`drive_capture`](drive_capture.md) e da decisão de acesso da
[ADR-011](../decisions/ADR-011-drive-readonly-capture.md) (*Proposta*).

## Comandos

A partir da raiz do repositório, com o venv do Cartório System:

```bash
python -m app.modules.services_snapshot.cli refresh   # coleta + retrato + publicação
python -m app.modules.services_snapshot.cli show      # último retrato válido; sem rede
```

`--config <caminho>` aceita outra config (padrão `_local_data/drive_capture/config.yaml`).
`refresh` exige o extra `pip install -e ".[drive]"`. `show` não autentica, não abre rede e
não exige o extra.

| Comando | Saída | Significado |
|---|---|---|
| `refresh` | 0 | relatório válido publicado, inclusive com cobertura **parcial** da fonte |
| `refresh` | 2 | falha técnica; último relatório válido preservado; tentativa registrada |
| `refresh` | 4 | outro `refresh` em andamento; nada feito, nada registrado |
| `show` | 0 | relatório válido, **confirmado** pelo registro da tentativa que o publicou |
| `show` | 1 | relatório válido, mas a **última tentativa falhou** (o retrato é o anterior) ou a atualização **não está confirmada** (registro ausente, de outro run ou anterior ao relatório) |
| `show` | 3 | nenhum relatório válido publicado ainda |
| `show` | 2 | arquivo local inválido; nada exibido |

Os códigos de saída da CLI do coletor não mudam.

## O que o `refresh` faz

1. Lê a config pelo mecanismo do coletor e exige **uma** fonte em `files` e `folders: []`.
2. Executa **uma coleta** pelo coletor existente (mesma autenticação, escopo
   `drive.readonly`, transporte só GET, retenção de duas gerações).
3. Vincula o retrato à geração produzida **nesta** execução: o `run_id` precisa coincidir
   no estado da fonte e no manifesto; procedência e SHA-256 são conferidos sobre os mesmos
   bytes que serão lidos.
4. Classifica com as regras calibradas, calcula os indicadores de datas contra a
   referência da captura e valida o relatório contra um esquema fechado.
5. Publica `latest.json` por troca atômica (o **ponto de publicação**) e, depois,
   registra `last_attempt.json`.

Em falha antes da troca (coleta, vínculo, integridade, leitura, validação ou
publicação), `latest.json` **não muda** — nem a captura, nem os horários — e só
`last_attempt.json` registra horário, etapa e código. Se a troca acontece e só o
registro da tentativa falha, o relatório novo **já está publicado**: `refresh` sai com 0
e avisa no stderr, e `show` responde 1 com "atualização não confirmada" — nunca como
sucesso, nunca como preservação do anterior. Registro ausente, de outro run ou anterior
ao relatório também não confirma sucesso; registro inválido faz `show` responder 2. Uma trava local (`services_snapshot/run.lock`) impede refresh sobreposto,
sem alterar a trava do coletor. O coletor descarta a geração mais antiga ao capturar uma
nova (mantém atual e anterior); o retrato não guarda capturas próprias.

**Primeira execução:** `show` responde 3 até o primeiro `refresh` bem-sucedido.
**Atualização bem-sucedida:** novo `latest.json`; `show` responde 0.
**Falha após um sucesso:** `show` responde 1, avisa que a atualização falhou e exibe o
último retrato válido com a captura e os horários originais.
**Relatório 1.0 já gravado:** `show` continua lendo e exibe o aviso de que os
indicadores de datas não estão disponíveis nele; o próximo `refresh` bem-sucedido grava
a 1.1. O objeto 1.0 nunca é rebatizado nem completado.

## Regras aplicadas (confirmadas pelo operador em 20/10/2026)

- Cada linha elegível é **um serviço**, que pode envolver vários atos. Sem deduplicação.
- Setores pela correspondência normalizada do **nome da aba** com: Escrituras; Registro
  de Imóveis; Escrituras - Diversas; Registro Civil; Procurações; Diversos. Posição não
  conta; nome desconhecido fica "setor não vinculado" (cobertura parcial).
- Campos pelo cabeçalho: Tarefa, Prioridade, Solicitante, Status, Data de início, Data de
  término, Responsável, Observações (Situação = Observações; Data inicial = Data de
  início; Data final = Data de término). Só esses tornam a linha elegível. Vencimento da
  Prenotação e Data da prenotação/Data de prenotação são **auxiliares** do RI: são lidos,
  mas não criam serviço. PRENOTAÇÃO e Outorgante ficam fora dos cálculos.
- Linhas ocultas contam; Status classifica.
- Status por igualdade exata após normalizar caixa, acentos e espaços (tabela em
  `app/modules/services_snapshot/rules.py`). Encerramentos distintos: **concluído** e
  **cancelado**; as outras nove categorias formam os **não encerrados reconhecidos**
  (bloqueado incluído). Vazio e desconhecido ficam à parte, fora de qualquer subtotal.
- Reconciliações por aba: categorias + ausentes + não mapeados; encerrados + não
  encerrados + ausentes + não mapeados; visíveis + ocultos.

## Datas (significado confirmado pelo operador em 21/10/2026)

| Campo | Significado |
|---|---|
| Data de início / Data inicial | cadastro do pedido |
| Data de término / Data final | encerramento, por conclusão ou cancelamento |
| Data da prenotação / Data de prenotação | prenotação no Registro de Imóveis |
| Vencimento da Prenotação | vencimento **informado na planilha**, distinto da prenotação |

**Conversão** (`app/modules/services_snapshot/dates.py`), só em campos de data
identificados por cabeçalho inequívoco (duplicado = `ambiguo`, métrica indisponível):

- número serial em célula cujo estilo declara formato de data, no sistema 1900 ou 1904
  declarado no XLSX; a fração (hora) é descartada sem conversão de fuso — datas civis;
- texto `d/m/aaaa` (ano com quatro dígitos) ou `aaaa-mm-dd`;
- todo o resto é **inválido**, sem correção: número sem formato de data (pode ser
  protocolo), serial < 1 (sentinelas), 29/02/1900 fictício, ano com dois dígitos, formato
  americano, texto livre, booleano, erro, fórmula sem resultado gravado. Vazio é
  **ausente**, nunca serial zero. Fórmulas não são recalculadas.

**Referência:** data civil da captura (`capturada_em`) em America/Sao_Paulo (UTC−03:00
fixo, sem horário de verão desde 2019), gravada em `referencia_temporal`. `show` exibe os
indicadores gravados, sem relógio. Captura, geração do relatório e referência são campos
distintos; gerar de novo não comprova atualização do serviço.

**Indicadores por setor** (dias corridos; sem pausas, feriados, SLA ou prazo legal):

- *Cobertura* de cadastro e encerramento **por grupo de Status** (não encerrados,
  concluídos, cancelados, sem status reconhecido): registros, válidas (até a
  referência), ausentes, inválidas, futuras. Ausência histórica em concluídos não se
  confunde com ausência na carteira aberta.
- *Idade da carteira não encerrada* (nove status, bloqueado incluído): referência −
  cadastro válido e não futuro; mesmo dia = 0. Faixas gerenciais 0–7, 8–15, 16–30,
  31–60, >60; a soma das faixas é o número de idades calculáveis.
- *Duração até conclusão* e *até cancelamento*, separadas: encerramento − cadastro, só com
  as duas datas válidas, encerramento ≥ cadastro e ≤ referência. Quantidade calculável,
  média e mediana; sem amostra, `null` (nunca zero).
- *Sinais de conferência*: encerramento anterior ao cadastro; não encerrado com data
  final preenchida; encerrado sem data final. Pedem conferência; não provam falha do
  colaborador. Inconsistência exclui só o indicador que não pode ser calculado.
- Status continua sendo a única classificação: data final não encerra serviço, e sem
  status reconhecido nada entra em carteira ou duração.

**Prenotação — só Registro de Imóveis, só não encerrados:** com Data da prenotação
identificada, dias corridos desde ela (média/mediana); com Vencimento da Prenotação, as
datas informadas anteriores à referência, iguais a ela, nos próximos 1–7 dias e além de 7
dias, com cobertura e lacunas de cada campo em separado. É **controle gerencial da
fonte**: não atesta prazo legal (LRP, arts. 9º e 205), caducidade ou perda de prioridade;
nenhum prazo é somado ou subtraído. Ausência de data de prenotação pode ser serviço ainda
não prenotado. PRENOTAÇÃO (número) e Outorgante nunca entram nos cálculos.

**Pendência de mapeamento (21/10/2026):** a planilha piloto **não tem** cabeçalho Data da
prenotação/Data de prenotação; a métrica fica indisponível (`nao_identificado`) até o
operador indicar um cabeçalho inequívoco. PRENOTAÇÃO não é usada no lugar dela.

## Arquivos e formato local

Em `<data_dir>/services_snapshot/` (padrão `_local_data/drive_capture/services_snapshot/`,
protegido pela ACL do diretório de dados e ignorado pelo Git):

- `latest.json` — **único resultado autoritativo**, formato
  `cartorio_system.services_snapshot.local` (local e experimental, **não** é contrato do
  Atlas). `refresh` grava a **v1.1**: `fonte`, `captura` (`run_id`, `capturada_em`,
  `drive_modified_time`, `drive_version`), `gerado_em`, `referencia_temporal` (`data`,
  `fuso`, `base`), `cobertura` (`qualidade` completa/parcial, abas
  interpretadas/pendentes/sem vínculo, percentuais, `reconciliacoes_ok`), `agregado`
  (inclui `datas`: soma das abas que têm cada campo, listadas em `abas_com_cadastro` e
  `abas_com_encerramento`; média e mediana sobre as amostras de todas elas) e `abas`
  (contagens por categoria, lacunas, sinais, reconciliações e `datas`: estado de cada
  campo de data, cobertura por grupo, idade, durações, sinais e, no RI, `prenotacao`).
  A **v1.0** (sem `referencia_temporal` nem `datas`) continua só legível pelo `show`.
- `last_attempt.json` — formato `cartorio_system.services_snapshot.attempt` v1.0:
  `tentativa_em`, `resultado` sucesso/falha, `etapa`, `codigo`, `run_id`.

Timestamps em ISO 8601 com fuso. O horário de captura é o da leitura da planilha, não o
da atualização dos serviços pelos colaboradores; `drive_modified_time` é sinal técnico.
O Markdown de `show` é derivado de `latest.json` a cada chamada.

**Sanitização por construção:** o relatório tem chaves fixas e cada valor é conferido
contra o domínio do seu campo (enumerações aprovadas, contagens, estatísticas numéricas
finitas, percentuais, timestamps, identificadores técnicos por regex) antes de ser
gravado; na v1.1, as reconciliações das datas também são verificadas (faixas = idades
calculáveis; cobertura = registros do grupo; `null` ⇔ sem amostra; referência = data da
captura; agregado = soma das abas). `show` valida de novo antes de exibir. Não há datas
individuais de pedidos, nomes de pessoas, protocolos, valores de células, observações,
cabeçalhos desconhecidos, IDs do Drive, e-mails, URLs, caminhos ou hashes. Status desconhecidos
aparecem só como `desconhecido_NN` (diagnóstico daquele relatório, não identificador).

## Fora do escopo

Agendamento, consumo pelo Atlas, monitoramento diário, cálculo jurídico de prazos
(dias úteis, feriados, suspensão/prorrogação, caducidade), SLA, atraso, produtividade
individual, contagem de atos, deduplicação, transições por serviço. Diferença entre dois
retratos não comprova entrada, conclusão ou produção de um serviço específico.
