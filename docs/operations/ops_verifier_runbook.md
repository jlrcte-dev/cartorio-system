# Runbook — verificador operacional e prova de recuperação (CARTORIO-OPS-1)

> Sprint `CARTORIO-OPS-1`, Fase 1 do [roadmap de infraestrutura](../infrastructure/infrastructure_roadmap.md).
> Decisão: [ADR-014](../decisions/ADR-014-verificacao-operacional-e-prova-de-recuperacao.md) (*Proposto*).
> Checklist da janela real: [`ops_window_checklist.md`](ops_window_checklist.md).
> Todos os valores deste documento são **de laboratório e fictícios**. Valores reais
> (limiar, unidades, caminhos, canal de alerta) são decisão de implantação e ficam fora do Git.

## 1. O que é — e o que não é

| Peça | Faz | Nunca faz |
|---|---|---|
| `python -m app.ops.cli check` | Lê processo/API, PostgreSQL, Alembic e backup; emite JSON versionado; sai 0/1/2 | Escrever no banco, aplicar migration, tocar o backup, chamar serviço externo |
| `python -m app.ops.cli alert` | Converte o último relatório em alerta no spool local | Decidir canal, deduplicar, apagar alerta |
| `python -m app.ops.cli render-units` | Gera `.service`/`.timer` a partir de `deploy/ops/*.in` | Instalar ou habilitar unidade |
| `python -m app.ops.drill` | Prova de recuperação em PostgreSQL **descartável**, criado pelo próprio ensaio | Receber DSN, restaurar em banco que não criou, rodar contra a VM |
| `scripts/ops/pg_gate.py` | Gate PostgreSQL: suíte do PR #5 + cenários do verificador + ensaio | Rodar em produção |

O verificador vive em `app/ops/`, fora dos módulos de domínio e sem importá-los. Não usa
`app.core.config` (que leria um `.env` implícito): só o ambiente do processo.

## 2. Comandos de bancada

```bash
# Gate oficial (inalterado): o mesmo do CI
python -m ruff format --check . && python -m ruff check . && python -m pytest -q

# Verificador contra uma bancada local (ex.: SQLite migrado + API em 127.0.0.1:8000)
export CARTORIO_OPS_CHECKS=api,database,alembic
export CARTORIO_OPS_HEALTH_URL=http://127.0.0.1:8000/api/v1/health
export DATABASE_URL=sqlite:////tmp/bancada.db CARTORIO_OPS_EXPECTED_DIALECT=sqlite
export CARTORIO_OPS_RELEASE_DIR="$PWD"
python -m app.ops.cli check --output /tmp/ops/last-check.json; echo "exit=$?"
python -m app.ops.cli alert --report /tmp/ops/last-check.json --spool /tmp/ops/alerts

# Raiz de trabalho: diretório novo e só do operador (mktemp -d cria em 0700)
TRABALHO=$(mktemp -d)

# Gate PostgreSQL de bancada — o MESMO comando do job `postgres-gate` do CI
python -m pip install -e ".[dev,postgres]"
python scripts/ops/pg_gate.py --pg-bin /usr/lib/postgresql/18/bin \
    --work-root "$TRABALHO" --publish-dir "$TRABALHO/pg-gate-liberados"
# O que o gate liberou para publicação, conferido de novo (o passo de seleção do CI)
python scripts/ops/pg_gate.py --list-released "$TRABALHO/pg-gate-liberados"

# Só o ensaio de recuperação (modo sintético), exportando a cópia gerada
python -m app.ops.drill --pg-bin /usr/lib/postgresql/18/bin --work-root "$TRABALHO" \
    --report "$TRABALHO/drill.json" --export-artifact "$TRABALHO/copia"

# Ensaio a partir de uma cópia existente (formato da recuperação pelo PC dedicado)
MANIFESTO="$TRABALHO/copia/backup-20260101T000000Z.json"  # o .json ao lado do .dump
ACHADO_ID=1; ACHADO_COD=DRILL-EXEMPLO     # registro conhecido na cópia
BANCO=cartorio_drill_origem               # banco da cópia, informado à parte (sintética: este)
python -m app.ops.drill --pg-bin /usr/lib/postgresql/18/bin --work-root "$TRABALHO" \
    --report "$TRABALHO/drill-copia.json" --from-manifest "$MANIFESTO" \
    --expect-finding-id "$ACHADO_ID" --expect-finding-code "$ACHADO_COD" \
    --expect-database "$BANCO"

# Unidades a partir dos modelos (parâmetros de laboratório)
python -m app.ops.cli render-units --templates deploy/ops --params deploy/ops/lab.params --out /tmp/units
```

`--pg-bin` precisa das ferramentas `initdb`, `pg_ctl`, `pg_dump`, `pg_restore` (e `postgres`
para o gate) da **mesma versão principal**; o gate exige 18 (`--require-major`). No Windows,
`--work-root` precisa ser um caminho ASCII (o `initdb` recebe argv na página de código ANSI)
e o **modo cópia é recusado antes de copiar** (`copy_mode_unsupported_platform`), assim como
a exportação que o alimenta (`export_unsupported_platform`): lá o isolamento da cópia
dependeria da ACL herdada da raiz, que o ensaio não verifica. O gate inclui o modo cópia,
logo só aprova em Linux.

**Área privada desde a criação.** Os diretórios do ensaio nascem `0700` e os arquivos
`0600` já no `mkdir`/`open` (dump e manifesto copiados, `pgpass`, senha do `initdb`,
marcador), e ensaio e gate rodam sob umask `077`: um umask `022` do operador não abre
nada, e a área preservada após falha continua privada. O relatório registra os modos em
`isolation`. A cópia de origem só é lida. A exportação (`--export-artifact`) só existe no
modo sintético. Relatório que contenha credencial gerada pelo ensaio não é gravado: sai um
mínimo reprovado (`secret_in_report`).

**Destino da exportação.** Diretório novo nasce `0700` — também os pais que faltarem — e os
arquivos, `0600`. Diretório que já existe é usado como está, com modo, dono e conteúdo
preservados, desde que seja diretório de verdade, do próprio usuário, gravável por ele e
**sem escrita para grupo ou outros** (senão a cópia poderia ser trocada antes de o modo
cópia lê-la). Fora disso o ensaio é recusado antes de qualquer cluster, sem tocar no
destino nem no alvo de um link: `export_dir_symlink`, `export_dir_not_directory`,
`export_dir_not_owned`, `export_dir_writable_by_others`, `export_dir_not_writable`. Arquivo
de mesmo nome nunca é sobrescrito (`export_file_exists`). O relatório registra
`artifact.export_destination` (`created` ou `existing`).

**Modo cópia: banco esperado.** `--from-manifest` exige `--expect-database`, informado à
parte e nunca lido da cópia. O manifesto passa pela mesma validação do verificador (§5):
`database` divergente recusa o ensaio antes de qualquer cluster (`database_mismatch`, sem
nomes no relatório).

**Bancada descartável, sempre:** cada cluster nasce num diretório criado pelo ensaio,
escuta só em `127.0.0.1` numa porta livre, sem socket Unix, com `pg_hba` restrito a
`127.0.0.1/32` e senha gerada. A identidade é **comprovada** antes de qualquer escrita
(token plantado no diretório de dados e lido pelo próprio servidor, `cluster_name`, porta
e `listen_addresses`); o banco de destino precisa carregar o marcador desta execução e
estar vazio. `PGHOSTADDR`, `PGSERVICE`, `PGSERVICEFILE` e `PGOPTIONS` no ambiente recusam o
ensaio; nenhuma `PG*` chega aos subprocessos.

**Limpeza só com parada confirmada.** O ensaio tenta parar **todos** os clusters da
execução, mesmo que um falhe, e confirma cada parada por `pg_ctl status`; só então remove o
diretório com o marcador da execução — inclusive em falha. Parada incerta (por exemplo,
`pg_ctl start` estourou o prazo com o postmaster subindo: `cluster_start_timeout`) preserva
o diretório e reprova: `passed` exige `cleanup.confirmed`, e um ensaio que teria passado
sai `cleanup_unconfirmed`. O estado por cluster fica em `cleanup.clusters`, com o comando de
diagnóstico. O gate só começa a prova de restauração com o cluster dos testes confirmado
parado e o diretório dele removido (senão, `gate_cleanup_unconfirmed`).
`--keep-on-failure` preserva o diretório para diagnóstico.

**O gate a partir da cópia sintética exportada** roda o modo cópia sob umask `022`: o banco
esperado restaura com a área em `0700`/`0600`; um banco divergente é recusado sem cluster;
a cópia de origem sai intocada (modo, data e SHA-256). No cluster dos testes o gate cria
também os dois bancos da prova de vínculo ao banco efetivo (§3), na mesma revisão Alembic.

**Publicação do gate (CI público).** A saída dos subprocessos (log do pytest e, por ensaio,
log e relatório) fica numa área bruta privada, com marcador, e nada dela é impresso antes
de conferido. A conferência procura URL com senha, campo de senha/segredo/token com valor
em JSON, chave privada e as credenciais geradas pelo próprio gate. Log limpo é impresso;
com credencial, fica retido e só sai a categoria. Relatório limpo vai para a área liberada
(`--publish-dir`, que precisa não existir); com credencial, fica retido. Nos dois casos o
gate reprova (`credential_in_output`). O manifesto `pg-gate-liberados.json` (nome e
SHA-256 de cada arquivo liberado) é gravado por último, e a área bruta é removida. O
workflow publica só o que `--list-released` devolve: os arquivos do manifesto, conferidos
de novo. Divergência ou manifesto ausente não publica nada, e nada do diretório temporário
entra por glob. Relatórios liberados: `pg-gate-report.json` e
`pg-gate-report-{drill,copy,copy-foreign}.json`. O relatório do gate registra a
conferência em `publication` e `secret_scan`, e o Gitleaks em `gitleaks` (não executado).

## 3. Parâmetros do verificador (ambiente)

| Variável | Checagem | Obrigatória | Laboratório |
|---|---|---|---|
| `CARTORIO_OPS_CHECKS` | todas | não (padrão: as quatro) | `api,database,alembic,backup` |
| `CARTORIO_OPS_TIMEOUT_SECONDS` | todas | não (padrão 5; máx. 60) | `5` |
| `CARTORIO_OPS_HEALTH_URL` | api | sim, ou `UNITS` | `http://127.0.0.1:8000/api/v1/health` |
| `CARTORIO_OPS_EXPECTED_APP_NAME` | api | não | `Cartorio System - Laboratorio` |
| `CARTORIO_OPS_UNITS` | api | não | `cartorio-lab.service:service,postgresql@18-main.service:service` |
| `DATABASE_URL` | database, alembic | sim | via `db.env` do app (nunca copiar) |
| `CARTORIO_OPS_EXPECTED_DIALECT` | database, alembic | não (padrão `postgresql`) | `postgresql` |
| `CARTORIO_OPS_RELEASE_DIR` | alembic | sim | `/opt/cartorio-lab/current` |
| `CARTORIO_OPS_RELEASE_ID` | relatório | não (deduzido de `releases/<sha>`) | — |
| `CARTORIO_OPS_BACKUP_DIR` | backup | sim | `/var/lib/cartorio-lab-backups/recorrentes` |
| `CARTORIO_OPS_BACKUP_MAX_AGE_HOURS` | backup | **sim, sem padrão** | `26` |
| `CARTORIO_OPS_BACKUP_EXPECTED_DATABASE` | backup | sim no backup isolado sem DSN PostgreSQL e na bancada SQLite; nos demais casos, opcional (se definida, precisa coincidir) | `cartorio_lab` |
| `CARTORIO_OPS_BACKUP_SERVICE_UNIT` / `_TIMER_UNIT` | backup | não | `cartorio-lab-backup.service` / `.timer` |
| `CARTORIO_OPS_RESTORE_EVIDENCE` / `_MAX_AGE_DAYS` | backup | não | relatório do último ensaio / `35` |
| `CARTORIO_OPS_SYSTEMCTL` | api, backup | não | `systemctl` |

**Banco esperado do backup.**

- **Modo combinado** (`database` e `backup` na mesma execução, em PostgreSQL — o padrão):
  o manifesto se vincula ao banco que a conexão somente leitura abriu de fato
  (`current_database()`, overrides da libpq incluídos). O nome da variável e o lido da DSN,
  quando existem, precisam coincidir com ele (`expected_database_conflict`). Se a conexão
  não chegou a observá-lo, o resultado é `expected_database_unproven`.
- **Backup isolado ou bancada SQLite:** vale o nome lido da DSN como a conexão o abriria
  — o banco do caminho e, por cima, `dbname` da querystring; valor vazio é descartado — e/ou
  a variável, coincidentes. A variável sozinha só vale sem DSN PostgreSQL.
- **Ambíguo** (`expected_database_ambiguous`, mesmo com a variável): perfil de serviço
  (`service`/`servicefile`), DSN sem banco, ou `dbname` repetido ou inválido. Sem observar
  a conexão, não há identidade verificável.

Sem banco comprovado a checagem nunca é saudável, mas as falhas que independem dele
continuam aparecendo: cópia ausente, todas vencidas ou corrompida. Nenhuma cópia é dada
como a última válida. O nome do banco nunca aparece no JSON: o sinal `expected_database`
diz só a origem (`expected_database_from_connection`, `_from_dsn`, `_explicit`) ou o
motivo, e `database` registra `identity_observed`.

Tipos de unidade: `service` (persistente: só `active`/`running` passa — configure
`postgresql@18-main.service`, nunca o guarda-chuva `postgresql.service`, que reporta
`active` com o cluster parado), `oneshot` (inativo depois de sucesso é o esperado) e `timer`.

## 4. Interpretação

**Saída:** `0` todas as checagens obrigatórias comprovadas · `1` falha detectada · `2`
diagnóstico inconclusivo (inclui uso inválido e erro interno do próprio verificador).
**Precedência:** `fail` > `inconclusive` > `ok` — uma falha comprovada vence a falta de
evidência, e as inconclusivas continuam no JSON. Checagem fora de `CARTORIO_OPS_CHECKS` é
`skipped` (não obrigatória); nenhuma executada é inconclusivo, nunca saudável.

**JSON** (`cartorio_system.ops.check` 1.0): `generated_at` (UTC), `invocation_id` (o
`INVOCATION_ID` do systemd daquela execução, ou `null` fora dele), `overall`, `reason`,
`exit_code`, `release`, `config_errors` (só nomes de variáveis), `output` e `checks.<nome>`
com `status`, `reason`, `duration_ms` e `signals`. O motivo da checagem é o do primeiro
sinal com o estado mais grave. Nunca há DSN, host, usuário, mensagem de exceção ou conteúdo
do banco: só motivo estável, classe do erro e SQLSTATE quando o servidor o enviou.

**Publicação (`--output`).** O resultado final é fechado antes de imprimir: o JSON do
stdout e o código de saída sempre concordam e, quando o arquivo é publicado, são iguais a
ele (`output.published: true`). Se a publicação falha, `output` traz `published: false`,
`reason: output_not_published` e a classe do erro; com as checagens saudáveis, o resultado
vira `inconclusive`/`output_not_published` (saída 2) — sem o arquivo, a unidade não teria
evidência; falha detectada continua `fail` (saída 1). Sem `--output`: `{"requested": false}`.

| Checagem | `fail` | `inconclusive` |
|---|---|---|
| `api` | `unit_not_running`, `unit_not_enabled`, `unit_not_found`, `last_run_failed`, `timer_inactive`, `http_status`, `unexpected_body`, `app_mismatch`, `unreachable`, `timeout` | `systemd_unavailable`, `systemctl_timeout`, `systemctl_failed`, `config_*` |
| `database` | `dialect_mismatch`, `unavailable`, `timeout`, `auth_failed`, `database_missing`, `query_failed` | `config_missing`, `config_invalid` (`url_unparseable`, `driver_unavailable`) |
| `alembic` | `revision_behind` (pendente de migration), `revision_unknown` (banco à frente ou outra linhagem) | `version_table_missing`, `version_table_unreadable`, `database_unavailable`, `release_unreadable` |
| `backup` | `backup_missing`, `no_verifiable_copy`, `manifest_incomplete`, `manifest_inconsistent`, `reference_outside_dir`, `recovery_point_in_future`, `recovery_point_unreadable`, `database_mismatch`, `artifact_missing`, `size_mismatch`, `digest_mismatch`, `unverifiable_copy`, `no_valid_copy`, `backup_stale`, `last_attempt_failed`, `timer_inactive`, `timer_not_enabled`, `restore_test_failed`, `restore_test_stale` | `expected_database_missing`, `expected_database_ambiguous`, `expected_database_conflict`, `expected_database_unproven`, `backup_dir_unavailable`, `backup_dir_unreadable`, `artifact_unreadable`, `restore_evidence_*`, `systemd_*` |
| geral | — | `output_not_published` (checagens saudáveis, relatório não publicado) |

Observações: `/health` saudável **não** prova o banco (a engine é preguiçosa: DSN quebrada
sobe o processo e responde `/health`) — por isso `database` é checagem separada. Porta
fechada aparece como `unavailable` no Linux e como `timeout` no Windows (o driver só
desiste no prazo); os dois são falha. `alembic check` (deriva de schema) é prova de
bancada/CI, não do verificador, que só lê `alembic_version` em transação somente leitura.

## 5. Backup: como a evidência é avaliada

O verificador lê o formato que a rotina existente já publica, sem alterá-la:
`backup-<AAAAMMDDTHHMMSSZ>.dump` + `backup-<carimbo>.json` (`arquivo`, `sha256`,
`tamanho_bytes`, `gerado_em_utc`, `database`). Sinais separados em `checks.backup.signals`:

| Sinal | Pergunta |
|---|---|
| `expected_database` | De que banco as cópias precisam ser, e de onde veio essa identidade (§3)? |
| `last_copy` | Qual é a última publicação completa, e o manifesto dela é utilizável? |
| `integrity` | O SHA-256 recalculado agora bate com o manifesto (mesmo artefato)? |
| `publications` | Há cópia mais nova sem manifesto/ilegível além da carência de 10 min? |
| `last_valid_copy` | Qual a cópia mais nova que passou em tudo (pode ser anterior à última)? |
| `age` | Idade da última cópia válida pelo **ponto de recuperação** (`gerado_em_utc`) |
| `last_attempt` | Resultado da última execução da unidade de backup (desde o boot) |
| `timer` | Timer do backup ativo e habilitado? |
| `restore_test` | Há restauração **efetivamente testada** recente (relatório do ensaio)? |

- A data de modificação do arquivo é só auxiliar (e mede a carência de publicação parcial).
- Horário futuro (além de 5 min de folga) ou ilegível invalida a evidência.
- Referência com separador, `..`, link simbólico ou fora do diretório é recusada.
- Manifesto de outro banco (`database` diferente do banco esperado, §3) é
  `database_mismatch`: a cópia não conta como válida, e uma cópia anterior correta continua
  sendo o último ponto válido. Os nomes dos bancos não aparecem no JSON.
- **Cadências diferentes:** a validação estrutural (`pg_restore --list`) roda na cadência
  da rotina, antes de o digest ser gravado; o verificador recalcula o digest na cadência
  dele. Enquanto o digest bater, a validação da publicação continua valendo para aquele
  artefato; a restauração testada é outro sinal, com validade própria (`RESTORE_MAX_AGE_DAYS`).
- Tentativa nova que falhou e cópia anterior válida aparecem juntas: `last_attempt=fail`
  e `last_valid_copy`/`age` com a cópia anterior.
- Retenção continua sendo da rotina existente; o verificador nunca apaga nada.

## 6. Alerta

`check` não alerta sozinho: a unidade do verificador sai ≠ 0, fica `failed` e o
`OnFailure=` dispara a unidade de alerta, que roda `cli alert` sobre o `last-check.json`.
O alerta (`cartorio_system.ops.alert` 1.0: `level`, `reason`, `problems`, `summary`,
`failed_run`) vai para o **spool local de teste** (`alerts/alert-*.json` no diretório de
estado). Também alerta quando não há relatório utilizável (ausente, ilegível ou mais velho
que 15 min) — o caso em que o verificador quebrou antes de escrever.

**Falha com relatório saudável anterior.** Se a execução que falhou não chegou a escrever
(venv quebrado, disco cheio, `TimeoutStartSec`), o `last-check.json` em disco é o da
execução anterior — talvez saudável. Por isso a unidade de alerta chama
`alert --expect-failure`: nesse modo o comando **nunca** responde "sem alerta". O systemd
(≥ 251) entrega `MONITOR_INVOCATION_ID`, `MONITOR_SERVICE_RESULT` e `MONITOR_EXIT_STATUS` à
unidade acionada. Se o `invocation_id` do relatório não é o da execução que falhou, o
motivo é `report_not_from_failed_run`; se é, mas o relatório diz `ok`,
`run_failed_but_report_healthy`. Nos dois casos o nível é `inconclusive`, os problemas do
relatório antigo não são listados como atuais, e `failed_run` traz o que o systemd informou.
Fora do `OnFailure=` (uso manual, sem a flag), relatório saudável continua sem alerta.

**Ponto de integração com o canal futuro:** `app.ops.alert.build_alert` produz o payload
e `write_alert` o entrega. O canal (mensageria, e-mail) consome o spool ou substitui a
entrega; o verificador não muda. Deduplicação e retenção do spool são decisão do canal.
**Limite conhecido:** tudo isso roda dentro da VM — se a VM ou o host cair, nada alerta.
Um observador externo (batimento a partir de outra máquina) é decisão de implantação.

## 7. Instalação na VM (janela própria)

Pré-requisitos: release com `app/ops` publicada pelo procedimento por SHA; systemd ≥ 251.
Os comandos rodam como root. Os valores são de laboratório — troque pelos decididos.

```bash
set -eu
PREFIXO=cartorio-lab-ops                 # UNIT_PREFIX do arquivo de parâmetros
ESTADO=cartorio-lab-ops                  # STATE_DIR_NAME -> /var/lib/$ESTADO
RELEASE=/opt/cartorio-lab/current        # RELEASE_DIR
PY="$RELEASE/.venv/bin/python"           # PYTHON
CONF=/etc/cartorio-lab/ops.env           # CONFIG_FILE (do verificador)
DBENV=/etc/cartorio-lab/db.env           # DB_ENV_FILE: do APP, só leitura — nunca editar
USUARIO=cartorio-lab; GRUPO=cartorio-lab # SERVICE_USER / SERVICE_GROUP
PARAMS=/root/cartorio-ops.params         # parâmetros reais, fora do Git
UNITS=/root/cartorio-ops-units           # saída do render, conferida antes de instalar

# 1. Configuração do verificador (editar os valores depois de copiar)
install -m 0640 -o root -g "$GRUPO" "$RELEASE/deploy/ops/ops.env.example" "$CONF"

# 2. Uma execução sem instalar nada, com a mesma semântica de EnvironmentFile
systemd-run --wait --pipe --uid="$USUARIO" --gid="$GRUPO" -p WorkingDirectory="$RELEASE" \
    -p EnvironmentFile="$CONF" -p EnvironmentFile="$DBENV" "$PY" -m app.ops.cli check
#    esperado: "overall": "ok" e saída 0

# 3. Unidades: gerar, verificar, instalar
"$PY" -m app.ops.cli render-units --templates "$RELEASE/deploy/ops" --params "$PARAMS" --out "$UNITS"
SYSTEMD_UNIT_PATH="$UNITS:" systemd-analyze verify "$UNITS"/*
install -m 0644 "$UNITS"/* /etc/systemd/system/
systemctl daemon-reload

# 4. Primeira execução pela unidade
systemctl start "$PREFIXO-check.service"
journalctl -u "$PREFIXO-check.service" -n 60 --no-pager
cat "/var/lib/$ESTADO/last-check.json"

# 5. Agenda
systemctl enable --now "$PREFIXO-check.timer"
systemctl list-timers "$PREFIXO-check.timer" --no-pager
```

**6. (Opcional, seguro) Provar a cadeia de alerta.** O drop-in precisa de um
`EnvironmentFile=` **adicional**. `Environment=` não serve: no systemd, `EnvironmentFile=`
vence `Environment=`, e o limiar de `$CONF` prevaleceria sem nenhum erro visível.

```bash
TESTE="/etc/systemd/system/$PREFIXO-check.service.d"
install -d "$TESTE"
echo "CARTORIO_OPS_BACKUP_MAX_AGE_HOURS=0.001" > "$TESTE/limiar-teste.env"
printf '[Service]\nEnvironmentFile=%s/limiar-teste.env\n' "$TESTE" > "$TESTE/override.conf"
systemctl daemon-reload
systemctl start "$PREFIXO-check.service" || true   # sai 1 -> OnFailure= -> alerta
ls -l "/var/lib/$ESTADO/alerts/"                    # um alert-*.json novo: backup_stale
rm -r -- "$TESTE"
systemctl daemon-reload
systemctl start "$PREFIXO-check.service"            # volta a sair 0
```

Evidência a guardar (fora do Git): JSON do check, saída de `list-timers`, arquivo de alerta.

## 8. Reversão

O verificador não altera app, banco nem backup: reverter é retirar as unidades **dele**,
e nada mais. Como root, com os mesmos valores do §7:

```bash
set -u   # sem -e: a reversão precisa poder ser repetida, ou rodar após instalação parcial
PREFIXO=cartorio-lab-ops
: "${PREFIXO:?defina PREFIXO}"   # sem prefixo, os caminhos abaixo apontariam para outra coisa

systemctl disable --now "$PREFIXO-check.timer"                             # 1. para a agenda
systemctl stop "$PREFIXO-check.service" "$PREFIXO-alert.service"           # 2. nada em curso
systemctl reset-failed "$PREFIXO-check.service" "$PREFIXO-alert.service"   # 3. só as nossas
rm -f -- "/etc/systemd/system/$PREFIXO-check.service" \
         "/etc/systemd/system/$PREFIXO-check.timer" \
         "/etc/systemd/system/$PREFIXO-alert.service"                      # 4. unidades
rm -rf -- "/etc/systemd/system/$PREFIXO-check.service.d"                   # 5. drop-in do §7.6
systemctl daemon-reload

# 6. Conferência: nada do verificador carregado nem agendado
systemctl list-unit-files "$PREFIXO-*" --no-pager                 # esperado: 0 unit files listed
systemctl list-timers --all --no-pager | grep -c -- "$PREFIXO" || true   # esperado: 0
```

- **Nunca** rode `systemctl reset-failed` sem nomear as unidades: ele apaga o estado de
  falha de todas as unidades do host — inclusive a falha do backup, que é evidência.
- **Não remova o `db.env` do app**: as unidades do verificador só o leem; ele pertence ao
  serviço da aplicação.
- O arquivo de configuração do verificador e o diretório de estado (`last-check.json`,
  `alerts/`) ficam como evidência. Removê-los é decisão separada, depois de guardar o que
  interessa.

## 9. Decisões de implantação pendentes

Limiar real de idade (a rotina hoje é diária; a meta Classe 3 é RPO ≤ 4 h) · validade da
restauração testada · canal de alerta definitivo e deduplicação · observador externo ·
usuário do verificador (o do app, ou um próprio no mesmo grupo) · DSN do verificador (a do
app, que prova a credencial em uso, ou um papel só de leitura).
