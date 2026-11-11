# Piloto — cópia verificada e observador fora do host (CARTORIO-OPS-2)

> **Estado:** piloto em bancada, com dados sintéticos. Nada instalado em lugar nenhum.
> Decisão: [ADR-015](../decisions/ADR-015-copia-verificada-e-observador-fora-do-host.md)
> (*Proposto*). Recuperação pelo destino: item 3 do
> [checklist da janela da OPS-1](ops_window_checklist.md). Todos os valores abaixo são de
> laboratório.
>
> **Endurecimento `CARTORIO-OPS-3`:** caminho do destino sem link em nenhum componente e
> preso a descritores (§2.1), recusa × falha por `errno` (§4.1) e sobras de `.preparo/`
> relatadas e removidas só com prova (§2.2, §8.1). Origem: achados S1, S2 e S4 de um
> ensaio de laboratório de recuperação, com dados sintéticos.

## 1. O que é — e o que não é

| É | Não é |
|---|---|
| Importação verificada de uma publicação da rotina de backup para um destino privado (`app.ops.offsite`) | Transporte de rede, agenda definitiva ou troca da rotina de backup |
| Observador que lê o último relatório do verificador e a cópia, sem acessar banco (`app.ops.observer`) | Envio de alerta: a saída é JSON local com código de saída |
| Base para a recuperação pelo PC dedicado com o modo cópia do ensaio | Retenção com exclusão, imagem de VM ou Engegraph |

## 2. Contrato do destino

```text
<destino>/geracoes/<carimbo>/backup-<carimbo>.dump   geração publicada (0700, arquivos 0600)
<destino>/geracoes/<carimbo>/backup-<carimbo>.json
<destino>/.preparo/<carimbo>-<sufixo>/               preparo de uma execução; ninguém lê
```

- **Origem só lida.** Vale a publicação mais recente com manifesto (ou `--stamp`). Dump sem
  manifesto é publicação parcial e nunca é importado.
- **Conferência na origem e no preparo:** a mesma `evaluate_publication` do verificador —
  manifesto regular e completo, referência confinada e sem link, carimbo coerente, ponto de
  recuperação legível e não futuro, tamanho, SHA-256 e banco esperado. O banco vem de
  `--expected-database`, configuração à parte, nunca do manifesto.
- **Promoção atômica:** o diretório de preparo inteiro vira a geração por `rename`, e o
  leitor vê a geração completa ou não a vê.
- **Mesma cópia de novo:** `already_published`, sem escrever nada.
- **Mesmo carimbo com outro conteúdo, ou geração inválida:** `generation_collision`, e a
  geração existente fica intocada. Vale também para duas execuções sobrepostas.
- **Falha ou interrupção** removem só o preparo da própria execução. A última geração
  válida continua legível; o relatório traz `last_valid_generation`.
- **Permissões desde a criação:** diretórios novos `0700`, arquivos `0600`. Destino
  existente é usado como está se for diretório de verdade, do mesmo dono e sem escrita de
  grupo ou outros; senão é recusado sem ser tocado. Link em qualquer componente do
  caminho, em `geracoes/`, em `.preparo/` ou numa geração nunca é seguido (§2.1).
- **Plataforma:** só roda onde o isolamento é comprovável por modo POSIX, como o modo
  cópia do ensaio (`offsite_unsupported_platform` no Windows).

### 2.1 Caminho do destino (OPS-3)

- **Aberto componente a componente**, a partir de `/`, sem seguir link em nenhum deles —
  ancestral inclusive. Link num ancestral é `destination_symlink` com `detail.part =
  "ancestor"`; o alvo do link não é criado, escrito nem lido. Caminho com `..` é
  `destination_not_canonical`.
- **Preso a descritores.** No POSIX, tudo o que vem depois — criar `geracoes/` e
  `.preparo/`, gravar o par, conferir o preparo, promover e remover o próprio preparo — é
  relativo aos diretórios já abertos (`openat`, `mkdirat`, `renameat`, `fstat`). Trocar um
  componente do caminho por um link no meio da execução não muda onde se escreve nem o que
  se confere. A conferência do preparo e da geração existente usa a mesma
  `evaluate_publication`, lendo pelo diretório aberto.
- **O leitor também não atravessa link** em nenhum componente: `last_valid_generation` do
  relatório e o observador (`copies_layout_invalid`).
- **Informe o caminho canônico** (`realpath`), também quando um diretório do sistema é link
  (por exemplo, `/home` → `/var/home`): a decisão de seguir esse link é do operador, uma
  vez, na configuração — nunca da execução.
- **Permissões que passam a contar.** A raiz, `geracoes/` e `.preparo/` são abertos para
  leitura: raiz sem leitura do dono (por exemplo `0300`), que a OPS-2 aceitava, agora é
  `destination_unusable`. Os ancestrais só precisam de busca (`O_PATH`, Linux); em outro
  POSIX sem `O_PATH` precisam também de leitura. Só o Linux é provado (CI).
- **Limite:** ancestral gravável por outro usuário continua sendo confiança do operador —
  só link é recusado ali, não dono nem modo. Escolha um destino cujos ancestrais sejam do
  próprio usuário ou de root e sem escrita de outros.

### 2.2 Preparo de execução interrompida (OPS-3)

Cada execução trava (`flock`) o próprio preparo enquanto vive e, só com a trava obtida,
grava nele o marcador `.cartorio-offsite-run` (esquema `cartorio_system.ops.offsite_staging`,
carimbo, sufixo, início e um resumo — SHA-256 truncado — de `/etc/machine-id` com o
`boot_id` do kernel, nunca copiado para o relatório). O marcador sai antes da promoção: a
geração publicada tem só o par. A trava morre com o processo, inclusive num `SIGKILL`.

A trava só prova algo entre processos **do mesmo kernel**: num destino de rede (NFS, CIFS,
FUSE) compartilhado por duas máquinas, uma pode segurá-la sem que a outra veja. Por isso a
sobra só é `orphan` se o marcador foi escrito **nesta máquina, neste boot**; de outra
máquina, de um boot anterior, ou numa máquina sem `machine-id`/`boot_id`, ela é `unproven`.

Toda importação inventaria `.preparo/` antes de criar o próprio preparo, sem seguir link e
sem abrir o que não passou nas provas anteriores:

| Estado | Prova | O que acontece |
|---|---|---|
| `orphan` | nome `<carimbo>-<8 hex>`, diretório de verdade, do mesmo dono, sem escrita de grupo ou outros; aberto sem seguir link e igual ao que o `lstat` viu; trava livre; marcador coerente com o nome e escrito nesta máquina neste boot | relatado; removido **só** com `--remove-orphan-staging`, ainda com a trava na mão e se o nome continuar apontando para o mesmo diretório |
| `active` | trava presa por outro processo agora (inclusive outro inventário no mesmo instante) | relatado, nunca tocado |
| `unproven` | nome do formato, mas sem marcador coerente (versão anterior à OPS-3, morte entre a criação e a trava, morte entre a retirada do marcador e a promoção, marcador forjado, de outra máquina ou de outro boot) ou sem como travar | relatado, nunca removido automaticamente — limpeza manual (§8.1) |
| `unexpected` | nome fora do formato (não ecoado), link, arquivo, de outro dono ou aberto a grupo ou outros | contado, nunca aberto nem tocado |

Idade (`age_hours`): pelo marcador no `orphan`; pela última modificação do diretório nos
demais (`null` se o instante gravado não é representável). Idade nunca decide nada. O relatório traz `staging.leftovers` com `counts` por
estado, `entries` (até 20, as mais antigas, só com nome do formato), `removed` e
`removal_failed`. Falha ao remover um órfão não muda o veredito da importação. Sem pedido,
o inventário só lê: a mesma cópia de novo continua sem escrever nada.

## 3. Comandos — um por etapa

Valores de laboratório. Troque pelos decididos na implantação.

```bash
# 1. Importar a publicação mais recente (origem só lida, destino privado)
python -m app.ops.offsite --source /srv/lab/backups --destination /srv/lab/copias \
    --expected-database cartorio_lab
#    saída 0: published ou already_published · 1: failed · 2: refused
#    --destination: caminho canônico (sem link nem '..' em nenhum componente)
#    --remove-orphan-staging: remove de .preparo/ só o que for comprovadamente órfão (§2.2)

# 2. Observar sinal da aplicação e cópia (nunca acessa banco)
python -m app.ops.observer --signal /srv/lab/sinal/last-check.json --copies /srv/lab/copias \
    --expected-database cartorio_lab --signal-max-age-minutes 45 --copy-max-age-hours 26
#    saída 0: ok · 1: fail · 2: inconclusive
```

### 3.1 Demonstração ponta a ponta — Linux com PostgreSQL 18

Gera dump e manifesto sintéticos com o ensaio, copia, retira a origem do fluxo e restaura
a partir do destino com o modo cópia. Na bancada Windows não roda (sem PostgreSQL nem
Linux).

**No CI:** o passo "OPS-2: cópia fora do host" do job `postgres-gate`
(`scripts/ops/offsite_gate.py`) faz esta sequência automaticamente, depois da publicação
da OPS-1, que fica intocada. Também confere o SHA-256 e os modos no destino, o observador
com sinal e, com a origem e o sinal retirados, `signal_missing` com a cópia válida mantida.
Roda antes os 32 testes POSIX (13 da OPS-2 e 19 da OPS-3) com o nome de cada um no log.
Reprova com teste pulado ou
prova faltando e só imprime um resumo sintético conferido contra credencial. Os ensaios
criam a área deles dentro da área do passo, e só o ensaio para e confirma o cluster que
criou. O passo remove a própria área apenas se cada ensaio confirmou a limpeza e a
inspeção do primeiro nível (sem seguir link nem abrir arquivo) não acha sobra: área de
ensaio, link ou entrada desconhecida. Prazo, interrupção, relatório ausente, sobra ou
inspeção incompleta preservam a área para diagnóstico e reprovam com
`work_preserved_cleanup_unproven`; ensaio sem limpeza
confirmada reprova com `drill_cleanup_unconfirmed`. Comandos manuais equivalentes:

```bash
PG_BIN=/usr/lib/postgresql/18/bin
W=$(mktemp -d)                                   # raiz nova, só do operador (0700)

# a) origem sintética: o ensaio exporta dump + manifesto
python -m app.ops.drill --pg-bin "$PG_BIN" --work-root "$W" \
    --report "$W/ensaio.json" --export-artifact "$W/origem"

# b) cópia verificada para o destino
python -m app.ops.offsite --source "$W/origem" --destination "$W/destino" \
    --expected-database cartorio_drill_origem

# c) a origem sai do fluxo
rm -rf -- "$W/origem"

# d) restauração a partir do destino (modo cópia)
CARIMBO=$(ls "$W/destino/geracoes" | tail -n 1)
CODIGO=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["record"]["finding_code"])' "$W/ensaio.json")
python -m app.ops.drill --pg-bin "$PG_BIN" --work-root "$W" \
    --report "$W/restauracao.json" \
    --from-manifest "$W/destino/geracoes/$CARIMBO/backup-$CARIMBO.json" \
    --expect-finding-id 1 --expect-finding-code "$CODIGO" \
    --expect-database cartorio_drill_origem
```

Evidência em `$W/restauracao.json`:
- digest: `artifact.verifier_evaluation=digest_verified`;
- banco: `artifact.database_matched`;
- leitura pela API do destino: `destination.api_app_name_confirmed` e
  `record.matched_on_destination`;
- limpeza: `cleanup.confirmed`;
- isolamento: `isolation`.

## 4. Motivos estáveis

**Importação** (`cartorio_system.ops.offsite_import` 1.1, sem caminho nem nome de banco):

| Veredito | Motivos |
|---|---|
| `published` (0) | `copy_verified` |
| `already_published` (0) | `same_copy_already_published` |
| `failed` (1) | os de `evaluate_publication` na origem (`database_mismatch`, `digest_mismatch`, `size_mismatch`, `manifest_incomplete`, `manifest_inconsistent`, `reference_outside_dir`, `recovery_point_in_future`…); `no_publication`, `publication_not_found`, `generation_collision`, `staged_copy_invalid`, `source_changed_during_copy`, `destination_write_failed`, `promotion_failed`, `source_unreadable`, `io_error` |
| `refused` (2) | `offsite_unsupported_platform`, `expected_database_invalid`, `stamp_invalid`, `source_missing`, `source_symlink`, `source_not_directory`, `destination_inside_source`, `source_inside_destination`, `destination_symlink`, `destination_not_directory`, `destination_not_canonical`, `destination_not_owned`, `destination_writable_by_others`, `destination_not_writable`, `destination_unusable` |

`detail.part` diz onde: `ancestor` (componente acima do destino), `root`, `geracoes` ou
`.preparo`.

### 4.1 Recusa × falha no destino (OPS-3)

- **Recusa (2)** — o destino, como configurado, não serve: link, não diretório ou `..` no
  caminho; dono, modo ou escrita impróprios; e erro de sistema `EACCES`, `EPERM`, `EROFS`
  ou `ENAMETOOLONG` ao abrir ou criar um componente (`destination_unusable`, com `part`,
  `error_class` e `errno`). Pai sem busca (`x`) cai aqui; antes da OPS-3 saía
  `failed/io_error`. Nada é escrito em diretório que já existia nem no alvo de um link;
  componentes que faltavam podem ter sido criados (`0700`) antes da recusa, como antes da
  OPS-3 — por exemplo num disco FAT, onde o `chmod` falha com `EPERM` depois do `mkdir`.
- **Falha (1)** — qualquer outro erro do sistema de arquivos: ao criar, `destination_write_failed`
  (por exemplo `ENOSPC`, `EIO`); ao abrir, `io_error`. Antes da OPS-3, qualquer erro ao
  criar o destino era `refused/destination_unusable`, inclusive disco cheio.
- Nenhum `OSError` vira recusa só por ser `OSError`: a classificação é pelo `errno`.
  `EROFS` é recusa porque o sistema de arquivos não distingue "montado só leitura pelo
  operador" de "remontado só leitura depois de erro"; destino existente nesse estado já
  era recusa antes (`destination_not_writable`). As duas saídas são diferentes de zero: um
  agendador que alerte só na 1 perde a 2.
- `detail.part` sai nos erros do caminho do destino; os mesmos motivos vindos da cópia do
  par (`destination_write_failed`) ou de um erro fora dos pontos previstos (`io_error`)
  trazem só `error_class` e `errno`.

### 4.2 Compatibilidade 1.0 → 1.1

| Item | 1.0 | 1.1 |
|---|---|---|
| `staging` | `used`, `removed` | os mesmos, mais `leftovers` (§2.2; `null` quando o destino não chegou a ser aberto ou `.preparo/` não pôde ser lido com segurança) |
| Link num ancestral | seguido; publicava no alvo | `refused/destination_symlink`, `part=ancestor` |
| `..` no destino | resolvido pelo sistema | `refused/destination_not_canonical` |
| Pai sem busca | `failed/io_error` | `refused/destination_unusable` (`EACCES`) |
| Disco cheio ou E/S ao criar o destino | `refused/destination_unusable` | `failed/destination_write_failed` |
| Ancestral que é arquivo | Linux: `failed/io_error` (`ENOTDIR` no `lstat`) | `refused/destination_not_directory`, `part=ancestor` |
| Raiz, `geracoes/` ou `.preparo/` de outro dono **sem leitura** para quem importa | `refused/destination_not_owned` | `refused/destination_unusable` (`EACCES`); com leitura, segue `destination_not_owned` |
| Raiz própria sem leitura (ex.: `0300`) | aceita | `refused/destination_unusable` (`EACCES`) |
| `detail` de `destination_unusable` | `part`, `error_class` | mais `errno` |
| `published`, `already_published`, `generation_collision`, códigos de saída, estrutura das gerações | — | inalterados |

Quem lê o relatório confere o maior da versão (`1`), como o observador faz com o
`cartorio_system.ops.check`.

**Observador** (`cartorio_system.ops.offsite_observation` 1.0):

| Sinal | Motivos |
|---|---|
| `application_signal` | `signal_fresh` · falha: `signal_missing`, `signal_invalid` (com `detail`), `signal_stale`, `signal_from_future` · inconclusivo: `signal_unreadable` |
| `last_check` | `check_ok`, `check_failed`, `check_inconclusive`; `check_unknown` (não avaliado) quando não há relatório válido |
| `offsite_copy` | `copy_fresh` · falha: `copy_missing`, `copy_no_valid`, `copy_latest_invalid`, `copy_stale`, `copies_layout_invalid` · inconclusivo: `copies_unreadable`, `expected_database_invalid` |

Estado geral: o mais grave (falha > inconclusivo > ok); motivo, o do primeiro sinal com
esse estado, na ordem acima. `last_valid_copy` (carimbo, ponto de recuperação, idade,
tamanho, SHA-256) sai sempre que existe uma cópia válida, qualquer que seja o resto.

Do relatório de entrada só passam códigos do contrato `cartorio_system.ops.check` 1.0:
em `last_check`, o `reported_reason` e, em cada item de `problems`, o nome da checagem, o
estado e o motivo. Qualquer outro valor, mesmo no formato de um código, sai como
`unrecognized`. `overall` que não é um dos três estados (inclusive lista ou objeto) é
`signal_invalid`, e a cópia é avaliada do mesmo jeito. Os limiares
(`--signal-max-age-minutes`, `--copy-max-age-hours`) precisam ser números finitos maiores
que zero; `nan`, `inf` ou valor grande demais são recusados como argumento (saída 2).

## 5. Cenários comprovados em bancada

Testes em `tests/test_ops_offsite.py` e `tests/test_ops_observer.py`.

| Cenário | Resultado |
|---|---|
| Caminho saudável | geração publicada idêntica à origem; origem intocada (modo, mtime, SHA-256); preparo vazio |
| Mesma cópia de novo | `already_published`, nada escrito |
| Colisão divergente e geração incompleta com o mesmo carimbo | `generation_collision`, existente intocada |
| Manifesto incompleto, de outro banco, digest ou tamanho errados, referência fora da raiz, carimbo incoerente, ponto futuro | `failed` com o motivo; geração anterior segue válida e legível |
| Falha de escrita no destino (sem espaço simulado) | `destination_write_failed` com `ENOSPC`; preparo removido |
| Corrupção durante a cópia; origem trocada no meio | `staged_copy_invalid`; `source_changed_during_copy` |
| Interrupção antes da promoção; restos de execução morta | nenhuma geração parcial; o leitor ignora o preparo e acusa a geração incompleta |
| Execuções sobrepostas | mesma cópia: a segunda termina `already_published`; conteúdo alheio: `generation_collision` |
| Destino compartilhado ou link, links na origem, modos `0700`/`0600` sob umask `022` | recusas sem tocar o alvo; modos conferidos — **testes POSIX, CI Linux** |
| Check saudável e fresco; check recente com falha | `ok`; `check_failed` com a checagem que falhou |
| Relatório inválido; sinal ausente, vencido ou do futuro | `signal_invalid` sem presumir check; `signal_missing`, `signal_stale` (mostrando o último check), `signal_from_future` |
| Cópia externa vencida | `copy_stale` pelo ponto de recuperação do manifesto, mesmo com mtime recente |
| Origem indisponível com cópia válida no destino | `signal_stale` e, ao mesmo tempo, `copy_fresh` com `last_valid_copy` |
| Sem configuração de banco no processo | o observador conclui com `DATABASE_URL` ausente |
| `overall` como lista ou objeto | `signal_invalid`; a cópia é lida e `last_valid_copy` mantida |
| Valor no formato de código fora do contrato (motivo, nome da checagem, estado) | `unrecognized`; o valor não sai no JSON nem na saída da CLI |
| Limiar `nan`, `inf` ou enorme | argumento recusado, saída 2 |
| Passo do CI: ensaio inconclusivo, prazo, interrupção, relatório ausente, `data` vinculado para fora, `postmaster.pid` sem token, sobra com confirmação contraditória (simulados) | área preservada e passo reprovado, nenhuma parada chamada pelo passo, link e alvo intactos; caso saudável remove a área e aprova — `tests/test_ops_offsite_gate.py` |
| OPS-3 — link no pai ou no avô do destino, inclusive com cópias válidas do outro lado | `destination_symlink` (`ancestor`); alvo intocado; `last_valid_generation` nulo — **POSIX** |
| OPS-3 — ancestral trocado por link no meio da cópia | geração publicada no diretório original; nada no alvo do link — **POSIX** |
| OPS-3 — `..` no destino | `destination_not_canonical`, nada criado |
| OPS-3 — pai sem busca ou sem escrita; destino de outro dono | `destination_unusable` (`EACCES`); `destination_not_owned` — **POSIX** |
| OPS-3 — `EACCES`/`EPERM`/`EROFS` × `EIO`/`ENOSPC` simulados ao abrir e ao criar | recusa × falha pelo `errno`; nada criado |
| OPS-3 — sobra de execução morta, com trava viva, de outra execução em curso, forjada, de outra máquina ou boot, link, aberta a todos, falha ao remover | `orphan` (só sai a pedido); `active`; `active`; `unproven`; `unproven`; `unexpected`; `unexpected`; `removal_failed` sem mudar o veredito — **POSIX** |
| OPS-3 — execução que não obtém a trava do próprio preparo; mtime não representável | nenhum marcador gravado (a sobra nunca vira `orphan`); idade `null`, sem derrubar a importação |
| OPS-3 — nome fora do formato, arquivo e sobra sem marcador em `.preparo/` | contados e intocados, também a pedido; nomes alheios não saem no relatório |
| OPS-3 — link num ancestral da raiz das cópias, no observador | `copies_layout_invalid`, sem `last_valid_copy` — **POSIX** |

## 6. Premissas da bancada e alcance da prova

- **Bancada:** Windows, sem PostgreSQL, Linux nem systemd. A lógica roda com a plataforma
  injetada, como os testes do modo cópia da OPS-1. Os testes POSIX (modos, links e
  travas) ficam pulados aqui e rodam no CI Linux depois da publicação (passo OPS-2 do
  `postgres-gate`). Fora do POSIX não há descritor de diretório nem `flock`: a bancada
  exercita a mesma lógica pelo caminho (`lstat` componente a componente), e a ancoragem
  por descritor só é provada no CI.
- **Dados:** só sintéticos. Nenhum dump real, nenhum acesso à homologação para o piloto.
- **Alcance:** contrato, verificação, publicação atômica, idempotência, colisão, falhas e
  leitura; a restauração ponta a ponta é provada pelo passo do CI (§3.1), não por esta
  bancada. **Não** prova transporte, desempenho com volume real, nem disco ou energia do
  equipamento de destino — isso é o aceite no PC dedicado.
- **Tempos** do ensaio são medição de bancada; não dimensionam RTO.

## 7. Escolha do destino

O **PC físico dedicado** é o primeiro candidato porque é hardware separado do host
Proxmox: a cópia sobrevive à perda do host e da VM, e o observador continua de pé quando
eles caem. Uma VM no mesmo Proxmox não serve, porque compartilha a disponibilidade do host.
A escolha depende de inventário e teste (§8). Mesmo aprovado, o PC fica no mesmo local
físico: a perda da serventia (incêndio, furto, inundação) exige uma cópia em outro local,
com planejamento próprio.

## 8. Lista para o dia em que o PC estiver disponível

A [ADR-016](../decisions/ADR-016-politica-de-protecao-do-banco.md) (*Aceito* em 09/11/2026)
decide o executor (o PC), o Transporte (puxado pelo PC, com identidade só do Cartório e só de
leitura na origem) e a Retenção da homologação (as 14 gerações mais recentes). Criptografia
para dado real segue sem decisão. A ADR não substitui a verificação de cada linha abaixo na
janela, e nada dela foi implantado.

| Item | O que verificar | Quem |
|---|---|---|
| Disco | saúde (SMART), espaço para N gerações, sistema de arquivos com `rename` atômico | operador, na janela |
| Sistema e executor Linux | SO; se Windows, onde roda o Linux da importação e da restauração (VM local, WSL2, dual boot) | João decide; operador instala |
| Energia e rede | nobreak ou tempo de autonomia; rota até a VM sem expor a rede da serventia | João (equipamento e rede) |
| Conta | usuário próprio, sem privilégio administrativo, dono do destino; só leitura na origem | operador, na janela |
| Criptografia | disco cifrado ou cópia cifrada; custódia da chave fora do PC | João decide |
| Transporte | como o par e o `last-check.json` chegam ao PC (puxado pelo PC ou enviado pela VM), com credencial mínima | João decide; etapa de implantação |
| Cópia com a origem indisponível | parar a VM (ou simular) e restaurar só a partir do destino (§3.1, item 3 do checklist) | operador, em janela própria |
| Canal de alerta | para onde vai a saída ≠ 0 do observador | João decide |
| Retenção | quantas gerações, quem apaga e com que registro | João decide |
| Custódia | quem tem acesso físico ao PC e às cópias; registro de acesso | João decide |
| Queda do próprio PC | o que avisa quando o observador para (batimento do PC para outro lugar, conferência manual com prazo) | João decide |
| Perda do host e do local | teste de perda do host: desligar o host com a cópia no PC (janela do item 4 do checklist); perda do local: exige cópia em outro endereço | João (decisão e janela) |

### 8.1 Sobras `unproven` em `.preparo/`: limpeza manual

Nenhum coletor apaga por nome ou idade. Para uma entrada `unproven` do relatório (nome no
formato `<carimbo>-<8 hex>`), como o usuário dono do destino, no próprio executor:

```bash
D=/srv/lab/copias                         # o mesmo --destination (canônico)
NOME=20260101T000000Z-0123abcd            # do relatório: staging.leftovers.entries[].name
X="$D/.preparo/$NOME"
if ! [[ "$NOME" =~ ^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$ ]]; then echo "PARE: nome fora do formato"
elif pgrep -f 'app\.ops\.offsite' >/dev/null; then echo "PARE: importação em curso"
elif [ -L "$X" ] || [ ! -d "$X" ]; then echo "PARE: não é diretório de verdade"
elif [ "$(stat -c %u -- "$X")" != "$(id -u)" ]; then echo "PARE: de outro dono"
elif ! flock -n "$X" -c true; then echo "PARE: trava presa (execução viva)"
else ls -la -- "$X"; echo "PODE REMOVER, depois de ler a listagem acima"; fi
```

Só se o bloco imprimiu `PODE REMOVER` e a listagem é a de um preparo (o par e, talvez, o
marcador):

```bash
rm -rf -- "$X"
```

Qualquer `PARE` encerra o procedimento sem remover nada. A geração publicada e as entradas
`unexpected` nunca entram nessa limpeza.

## 9. Lacunas para a implantação

- Transporte e credencial mínima entre VM e destino.
- Agenda da importação e do observador.
- Canal de alerta, retenção e criptografia.
- Batimento do próprio destino.
- Demonstração ponta a ponta em Linux com PostgreSQL 18 (§3.1).
- Testes POSIX no CI.
- A prova no `postgres-gate` (§3.1) só vale depois do primeiro run verde do PR, com os 32
  testes POSIX nominais e o resumo `cartorio_system.ops.offsite_gate` aprovado.
- Sobras `unproven` anteriores à OPS-3 (sem marcador) só saem pela limpeza manual (§8.1).
