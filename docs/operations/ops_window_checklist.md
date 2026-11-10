# Checklist — janela de operação de continuidade (Cartório System)

> Preparado na sprint `CARTORIO-OPS-1` (07/11/2026) e atualizado em 08/11/2026, depois do
> merge do PR #6. Executar numa janela própria, com o runbook
> [`ops_verifier_runbook.md`](ops_verifier_runbook.md) aberto. Evidências reais (saídas,
> relatórios, hashes) ficam **fora do Git**, no ambiente autorizado.

## Fontes de evidência (nunca misturar)

| Fonte | O que comprova | Situação em 08/11/2026 |
|---|---|---|
| **Git** | Código e documentos versionados | `origin/main` = `b22e1b6` (merge do PR #6, pais `c49c6579` e `7b92e4d`) |
| **GitHub Actions** | Mesma prova no runner, por SHA | ✅ CI do PR `42413480266` e pós-merge `42431949823` verdes — item 6 |
| **Relato operacional** | O que está implantado e foi observado na VM | Runbook privado de homologação (fora do Git), §9e–9f, e leitura somente leitura de 08/11 (unidades, journal, API) |
| **Bancada** | Prova local em recurso descartável, dado sintético | Relatório da sprint em [`../reports/RELATORIO_CARTORIO_OPS_1.md`](../reports/RELATORIO_CARTORIO_OPS_1.md) |

Marcação: **OK** (observado, com evidência) · **PENDENTE** (sem observação) ·
**PARCIAL** (parte da evidência existe — configuração conferida ou execução observada —,
mas o critério de fechamento ainda não foi cumprido).

## Itens operacionais da janela (1 a 5)

Cada item tem aceite próprio. O reboot do host (4) e a recuperação da cópia real (3) têm
janela e autorização próprias.

### 1. Segundo disparo automático consecutivo do backup — PARCIAL

Três evidências separadas, que não se substituem:

- **Execução — OK (relato, 08/11):** dois disparos automáticos consecutivos, em dias
  seguidos, terminaram com sucesso no journal da unidade de backup; o segundo coincide com
  o `LastTriggerUSec` do timer. A rotina registra no journal o arquivo e o SHA-256 de cada
  publicação. O disparo manual e a falha induzida de 07/11 não contam. Horários, agenda e
  hashes reais ficam no runbook privado.
- **Integridade — PARCIAL:** o manifesto do primeiro disparo automático (tamanho e SHA-256)
  foi guardado na evidência privada; o par do segundo não foi lido, porque o diretório de
  backups não é legível sem privilégio. Nenhum digest foi recalculado sobre os arquivos.
- **Restaurabilidade — PENDENTE:** só a cópia do disparo manual foi restaurada (07/11);
  nenhuma cópia automática.
- Conferir na janela, com privilégio: os dois pares `.dump` + `.json` (tamanho, SHA-256
  recalculado contra o manifesto, `pg_restore --list`). Com o verificador instalado:
  `backup.last_attempt=last_run_succeeded`, `backup.integrity=digest_verified`,
  `backup.age.age_hours` < limiar, `overall=ok`.
- Fecha quando: dois disparos automáticos em dias consecutivos, cada um com manifesto
  válido. Um disparo manual não conta. A restauração de uma cópia automática é o item 3.

### 2. Partida da VM após reboot controlado do convidado — PARCIAL

- Evidência disponível (relato): ordem `After=`/`Wants=` da unidade do app em relação à
  instância do PostgreSQL conferida por leitura; **nunca observada num boot real**. O
  último boot do convidado é anterior ao corte para PostgreSQL (leitura de 08/11).
- Antes: verificador `overall=ok`; registrar o instante do comando de reboot.
- Depois: unidades do app e do PostgreSQL `active`/`running`; `GET /api/v1/health` 200 (a
  rota `/health` na raiz responde 404); **leitura de um registro conhecido pela API** (o
  health não toca o banco); verificador após o `OnBootSec` (ou manual) com `api`,
  `database`, `alembic` e `backup` em `ok`.
- Medir: desligamento → boot → primeiro check saudável. Guardar à parte dos tempos de
  restart da aplicação.

### 3. Recuperação a partir da cópia guardada no PC dedicado, em destino isolado — PENDENTE

- Evidência disponível (relato): equipamento ainda sem acesso; data prevista no runbook
  privado.
- Copiar `backup-<carimbo>.dump` e `.json` para o PC dedicado; conferir o SHA-256 contra o
  manifesto na origem e no destino da cópia. Pelo `app.ops.offsite`, o `--destination` é o
  caminho canônico (sem link nem `..` em nenhum componente); conferir no relatório
  `staging.leftovers` — sobra `unproven` só sai pela limpeza manual do
  [guia do piloto](ops_offsite_pilot.md) §8.1.
- Restaurar em destino isolado criado pelo próprio ensaio (loopback, credencial gerada,
  sem acesso à rede da serventia). O modo cópia só roda em Linux: no Windows é recusado
  antes de copiar (`copy_mode_unsupported_platform`). Se o PC dedicado for Windows, o
  ambiente Linux da restauração é decisão desta janela. Valores de exemplo — troque pelos
  reais:

  ```bash
  PG_BIN=/usr/lib/postgresql/18/bin          # ferramentas da mesma versão principal do servidor
  TRABALHO=$(mktemp -d)                      # raiz nova, só do operador (0700)
  MANIFESTO=/srv/copias/backup-20260101T000000Z.json   # o .json ao lado do .dump copiado
  ACHADO_ID=1; ACHADO_COD=CODIGO-CONHECIDO   # registro que se sabe existir na cópia
  BANCO=cartorio_lab                         # banco de que a cópia precisa ser (à parte)
  python -m app.ops.drill --pg-bin "$PG_BIN" --work-root "$TRABALHO" \
      --report "$TRABALHO/restauracao-pc-dedicado.json" --from-manifest "$MANIFESTO" \
      --expect-finding-id "$ACHADO_ID" --expect-finding-code "$ACHADO_COD" \
      --expect-database "$BANCO"
  ```
- Fecha quando: `verdict=passed`, banco do manifesto conferido
  (`artifact.database_matched`), revisão Alembic igual à da release, registro conhecido
  conferido pela API do destino, `cleanup.confirmed`, área em `0700`/`0600` (`isolation`),
  relatório guardado com seu SHA-256. Id que não existe na cópia reprova com
  `record_mismatch` (`failure.record=absent`): conferir o id antes de repetir; `unexpected_error`
  é problema da bancada, não do registro.

### 4. Separado: partida após reboot do **host físico** (Proxmox) — PENDENTE

- Evidência disponível (relato): "Start at boot" da VM configurado; nunca observado.
- Exige janela que não prejudique outras VMs do host: registrar quais VMs o reboot afeta
  antes de pedir a autorização. Depois do boot do host: a VM subiu sozinha? Repetir as
  conferências do item 2. Registrar à parte do item 2 — são provas diferentes
  (convidado × hipervisor).

### 5. Instalação do verificador na VM — PENDENTE

- Evidência disponível (relato, 08/11): nenhuma unidade do verificador na VM, e a release
  ativa ainda é anterior a `app/ops`. A instalação começa por preparar e ativar a release
  com o verificador (passos 1 e 2 da sequência no
  [relatório](../reports/RELATORIO_CARTORIO_OPS_1.md#passos-da-janela-de-implantação)).
- Código e modelos prontos e provados no CI (item 6). Passos e reversão: runbook §7–§8.
- Com as quatro checagens (padrão), o backup é conferido contra o banco que a DSN do
  verificador abre de fato: ela precisa abrir o banco cujo nome a rotina grava no
  manifesto, e `CARTORIO_OPS_BACKUP_EXPECTED_DATABASE`, se usada, tem de coincidir
  (runbook §3).
- Decisões antes de instalar: runbook §9 (limite de idade, canal, observador externo,
  usuário e DSN).
- Fecha quando: release registrada por SHA, execução única e unidades aprovadas, timer
  ativo, execução saudável pela unidade, prova do alerta (§7.6) e reversão conhecida (§8).

## Evidência de engenharia — item 6

### 6. Gate PostgreSQL no GitHub Actions — OK (evidência de engenharia aprovada)

- **SHA:** `b22e1b6cd75022a828a2669b75a6ec61acf1f560`, merge do PR #6 em `main`. A árvore é
  a mesma da revisão testada pelo CI do PR (`8b269390`).
- **Runs:** [`42413480266`](https://github.com/jlrcte-dev/cartorio-system/actions/runs/42413480266)
  (PR) e [`42431949823`](https://github.com/jlrcte-dev/cartorio-system/actions/runs/42431949823)
  (pós-merge, `push` em `main`), cada um com `quality-gate` e `postgres-gate` verdes.
- **Versão testada:** PostgreSQL 18.6 (PGDG).
- **Resultado:** `quality-gate` com 1638 passed / 20 skipped, Ruff e Alembic aprovados;
  `postgres-gate` com 36 testes aprovados e zero pulados e unidades aprovadas no
  `systemd-analyze verify`.
- **Artefato:** [`pg-gate-reports`](https://github.com/jlrcte-dev/cartorio-system/actions/runs/42431949823/artifacts/13597826553),
  com os quatro relatórios liberados. Em ambiente sintético: digest verificado,
  restauração em cluster distinto, leitura pela API do destino, recusa da cópia de banco
  divergente e limpeza confirmada.
- **Segredos:** a varredura específica dos logs e do artefato não achou ocorrência; o
  Gitleaks não foi executado (dívida TD-10). São evidências separadas.
- Não substitui nenhum item operacional: é prova de código, não de implantação.

## Medição de RPO e RTO (formato do ensaio)

O relatório do ensaio (`cartorio_system.ops.restore_drill` 1.0) já traz os campos:

| Campo do relatório | Uso |
|---|---|
| `artifact.recovery_point_utc` | Ponto de recuperação. **RPO** = instante da falha − este valor |
| `recovery.started_at` | Início da recuperação (início do RTO) |
| `recovery.first_successful_query_at` | Serviço respondeu com o registro conhecido (fim do RTO) |
| `recovery.duration_seconds` / `phases_seconds` | **RTO medido** e onde o tempo foi gasto |
| `artifact.sha256`, `toc_entries`, `verifier_evaluation` | Integridade: a cópia restaurada é a publicada |
| `release.git_sha`, `release.alembic_heads` | Qual código fez a restauração |
| `destination.*` | Qual destino foi usado e como a identidade foi provada |
| `classification` | `bench_measurement` (sintético) ou `isolated_restore_measurement` (cópia) |

Metas Classe 3 (Provimento CNJ 213/2026): **RPO ≤ 4 h, RTO ≤ 8 h**. Duas decisões
distintas, que não se substituem:

- **Frequência efetiva de geração** — define o RPO. Com a rotina diária atual, o RPO real
  pode passar de 24 h, aquém da meta de 4 h. Lacuna conhecida, a decidir antes de dado
  real.
- **Limite de idade do verificador** (`CARTORIO_OPS_BACKUP_MAX_AGE_HOURS`) — só detecta
  atraso da rotina que existe; não melhora o RPO.

Tempo de bancada (base pequena, sintética) não dimensiona produção.

## Registro de evidência (PCN / PRD)

Para cada item executado, registrar fora do Git: data e hora (UTC) de início e fim,
executor, item e procedimento usado (seção do runbook), artefatos produzidos com SHA-256,
resultado (OK / PARCIAL / falhou), desvios observados, próxima ação, e assinatura do
responsável técnico — o mesmo conteúdo mínimo exigido no §3.5 do roadmap de infraestrutura.
