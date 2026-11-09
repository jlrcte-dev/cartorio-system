# Piloto — cópia verificada e observador fora do host (CARTORIO-OPS-2)

> **Estado:** piloto em bancada, com dados sintéticos. Nada instalado em lugar nenhum.
> Decisão: [ADR-015](../decisions/ADR-015-copia-verificada-e-observador-fora-do-host.md)
> (*Proposto*). Recuperação pelo destino: item 3 do
> [checklist da janela da OPS-1](ops_window_checklist.md). Todos os valores abaixo são de
> laboratório.

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
  grupo ou outros; senão é recusado sem ser tocado. Link na raiz, em `geracoes/` ou numa
  geração nunca é seguido.
- **Plataforma:** só roda onde o isolamento é comprovável por modo POSIX, como o modo
  cópia do ensaio (`offsite_unsupported_platform` no Windows).

## 3. Comandos — um por etapa

Valores de laboratório. Troque pelos decididos na implantação.

```bash
# 1. Importar a publicação mais recente (origem só lida, destino privado)
python -m app.ops.offsite --source /srv/lab/backups --destination /srv/lab/copias \
    --expected-database cartorio_lab
#    saída 0: published ou already_published · 1: failed · 2: refused

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
Roda antes os 13 testes POSIX com o nome de cada um no log. Reprova com teste pulado ou
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

**Importação** (`cartorio_system.ops.offsite_import` 1.0, sem caminho nem nome de banco):

| Veredito | Motivos |
|---|---|
| `published` (0) | `copy_verified` |
| `already_published` (0) | `same_copy_already_published` |
| `failed` (1) | os de `evaluate_publication` na origem (`database_mismatch`, `digest_mismatch`, `size_mismatch`, `manifest_incomplete`, `manifest_inconsistent`, `reference_outside_dir`, `recovery_point_in_future`…); `no_publication`, `publication_not_found`, `generation_collision`, `staged_copy_invalid`, `source_changed_during_copy`, `destination_write_failed`, `promotion_failed`, `source_unreadable`, `io_error` |
| `refused` (2) | `offsite_unsupported_platform`, `expected_database_invalid`, `stamp_invalid`, `source_missing`, `source_symlink`, `source_not_directory`, `destination_inside_source`, `source_inside_destination`, `destination_symlink`, `destination_not_directory`, `destination_not_owned`, `destination_writable_by_others`, `destination_not_writable`, `destination_unusable` |

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

## 6. Premissas da bancada e alcance da prova

- **Bancada:** Windows, sem PostgreSQL, Linux nem systemd. A lógica roda com a plataforma
  injetada, como os testes do modo cópia da OPS-1. Os testes POSIX (modos e links) ficam
  pulados aqui e rodam no CI Linux depois da publicação (passo OPS-2 do `postgres-gate`).
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

## 9. Lacunas para a implantação

- Transporte e credencial mínima entre VM e destino.
- Agenda da importação e do observador.
- Canal de alerta, retenção e criptografia.
- Batimento do próprio destino.
- Demonstração ponta a ponta em Linux com PostgreSQL 18 (§3.1).
- Testes POSIX no CI.
- A prova no `postgres-gate` (§3.1) só vale depois do primeiro run verde do PR, com os 13
  testes POSIX nominais e o resumo `cartorio_system.ops.offsite_gate` aprovado.
