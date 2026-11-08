# Checklist — janela de operação de continuidade (Cartório System)

> Preparado na sprint `CARTORIO-OPS-1` (07/11/2026). Executar numa janela própria, com
> o runbook [`ops_verifier_runbook.md`](ops_verifier_runbook.md) aberto. Evidências reais
> (saídas, relatórios, hashes) ficam **fora do Git**, no ambiente autorizado.

## Fontes de evidência (nunca misturar)

| Fonte | O que comprova | Situação em 07/11/2026 |
|---|---|---|
| **Git** | Código e documentos versionados | `origin/main` = `c49c6579` (PR #5); CI pós-merge `42277467291` verde. Esta sprint: branch local `sprint/cartorio-ops-1`, ainda sem push |
| **Relato operacional** | O que está implantado e foi observado na VM | Runbook privado de homologação (fora do Git), §9e–9f |
| **Bancada** | Prova local em recurso descartável, dado sintético | Relatório da sprint em [`../reports/RELATORIO_CARTORIO_OPS_1.md`](../reports/RELATORIO_CARTORIO_OPS_1.md) |
| **GitHub Actions** | Mesma prova no runner, por SHA | Pendente do push autorizado |

## Itens da janela

Marcação: **OK** (observado, com evidência) · **PENDENTE** (sem observação) ·
**PARCIAL** (configuração conferida, comportamento não observado).

### 1. Segundo disparo automático consecutivo do backup — PENDENTE

- Evidência disponível (relato): um disparo manual e o **primeiro disparo automático**
  observados em 07/11; o segundo, no dia seguinte, ainda não (`Persistent=true`). Horários
  e agenda reais ficam no runbook privado.
- Conferir: `systemctl list-timers` (LAST/NEXT do timer do backup); journal da unidade de
  backup desde o horário agendado do dia seguinte; novo par `.dump` + `.json` com o
  carimbo desse dia.
- Com o verificador instalado: `backup.last_attempt=last_run_succeeded`,
  `backup.integrity=digest_verified`, `backup.age.age_hours` < limiar, `overall=ok`.
- Fecha quando: dois disparos automáticos em dias consecutivos, cada um com manifesto
  válido. Um disparo manual não conta.

### 2. Partida da VM após reboot controlado do convidado — PARCIAL

- Evidência disponível (relato): ordem `After=`/`Wants=` da unidade do app em relação à
  instância do PostgreSQL conferida por leitura; **nunca observada num boot real**.
- Antes: verificador `overall=ok`; registrar o instante do comando de reboot.
- Depois: unidades do app e do PostgreSQL `active`/`running`; `/health` 200; **leitura de
  um registro conhecido pela API** (o `/health` não toca o banco); verificador após o
  `OnBootSec` (ou manual) com `api`, `database`, `alembic` e `backup` em `ok`.
- Medir: desligamento → boot → primeiro check saudável.

### 3. Recuperação a partir da cópia guardada no PC dedicado, em destino isolado — PENDENTE

- Evidência disponível (relato): equipamento ainda sem acesso; data prevista no runbook
  privado.
- Copiar `backup-<carimbo>.dump` e `.json` para o PC dedicado; conferir o SHA-256 contra o
  manifesto na origem e no destino da cópia.
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
  relatório guardado com seu SHA-256.

### 4. Separado: partida após reboot do **host físico** (Proxmox) — PENDENTE

- Evidência disponível (relato): "Start at boot" da VM configurado; nunca observado.
- Exige janela que não prejudique outras VMs do host. Depois do boot do host: a VM subiu
  sozinha? Repetir as conferências do item 2. Registrar à parte do item 2 — são provas
  diferentes (convidado × hipervisor).

### 5. Instalação do verificador na VM — PENDENTE

- Código e modelos prontos em bancada (esta sprint). Passos e reversão: runbook §7–§8.
- Com as quatro checagens (padrão), o backup é conferido contra o banco que a DSN do
  verificador abre de fato: ela precisa abrir o banco cujo nome a rotina grava no
  manifesto, e `CARTORIO_OPS_BACKUP_EXPECTED_DATABASE`, se usada, tem de coincidir
  (runbook §3).
- Decisões antes de instalar: runbook §9 (limiar real, canal, observador externo).

### 6. Gate PostgreSQL no GitHub Actions — PENDENTE

- Depende do push autorizado. Registrar SHA, run, versão do PostgreSQL testada e o
  relatório `pg-gate-reports` do run.

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

Metas Classe 3 (Provimento CNJ 213/2026): **RPO ≤ 4 h, RTO ≤ 8 h**. Com a rotina diária
atual, o RPO real pode passar de 24 h — lacuna conhecida, a decidir antes de dado real.
Tempo de bancada (base pequena, sintética) não dimensiona produção.

## Registro de evidência (PCN / PRD)

Para cada item executado, registrar fora do Git: data e hora (UTC) de início e fim,
executor, item e procedimento usado (seção do runbook), artefatos produzidos com SHA-256,
resultado (OK / PARCIAL / falhou), desvios observados, próxima ação, e assinatura do
responsável técnico — o mesmo conteúdo mínimo exigido no §3.5 do roadmap de infraestrutura.
