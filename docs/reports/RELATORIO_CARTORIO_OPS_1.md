# Relatório — CARTORIO-OPS-1: continuidade operacional automatizada

- **Data:** 2026-11-07
- **Branch:** `sprint/cartorio-ops-1` (worktree isolado), a partir de `c49c6579`
- **Escopo:** verificador operacional somente leitura, alerta local, modelos systemd,
  gate PostgreSQL e prova de recuperação em bancada — Fase 1 do
  [roadmap de infraestrutura](../infrastructure/infrastructure_roadmap.md)
- **Decisão:** [ADR-014](../decisions/ADR-014-verificacao-operacional-e-prova-de-recuperacao.md) (*Proposto*)

## Veredito

**Bancada local: PARCIAL.** Validados localmente o verificador, o contrato JSON, os códigos
de saída, a avaliação do backup, o alerta (inclusive falha com relatório saudável anterior),
os modelos de unidade e os cenários de aceite que não exigem servidor PostgreSQL — entre
eles **API real respondendo 200 com PostgreSQL indisponível**, com o HTTP real da aplicação
e o driver real.

**Não executado localmente:** a suíte do PR #5 em PostgreSQL 18, os cenários do verificador
contra servidor real, a prova de recuperação e o `systemd-analyze verify`. A bancada local
(Windows) não tem PostgreSQL, Docker, WSL nem systemd, e a execução de binários PostgreSQL
baixados não foi autorizada nesta sessão. Em 07/11/2026 o operador autorizou publicar esta
branch e abrir PR em rascunho: **o aceite dessas provas é o CI do PR** (jobs
`quality-gate` e `postgres-gate`), registrado no próprio PR com run, revisão testada,
versão do PostgreSQL e relatório sanitizado do ensaio. Este arquivo não é reescrito a cada
run, para não mudar a revisão que o CI testou.

## Para revisão humana

1. **Evidência do CI no PR:** conferir o run, o SHA efetivamente testado e o artefato
   `pg-gate-reports` antes de qualquer decisão de merge.
2. **Decisões de implantação** ([runbook §9](../operations/ops_verifier_runbook.md)):
   limiar real de idade do backup, validade da restauração testada, canal de alerta,
   observador externo, usuário e DSN do verificador.
3. **Itens com acesso físico ou ativação na VM** ([checklist](../operations/ops_window_checklist.md)):
   2º disparo do timer, boot do convidado, boot do host, recuperação pela cópia no PC
   dedicado, instalação do verificador.
4. **Lacuna de RPO:** a rotina é diária; a meta Classe 3 é RPO ≤ 4 h. Aceitável em
   homologação com dado sintético; precisa de decisão antes de dado real.

## Baseline — por fonte

| Fonte | Fato | Como foi confirmado |
|---|---|---|
| Git | `origin/main` = `c49c6579cf97614323cd228f4b0c25825b40c2fe`, merge do PR #5 (06/11 19:11 UTC) | `git fetch`, `gh pr view 5` |
| Git | CI pós-merge `42277467291` — `completed/success` | `gh run list --commit c49c6579…` |
| Bancada | Gate no baseline: formatação 187 arquivos, lint limpo, **1360 passed / 7 skipped** | execução local no worktree |
| Relato operacional | Homologação em PostgreSQL 18 desde 07/11; release ativa `c49c6579`; backup diário com 1º disparo automático observado; boot real e recuperação pelo PC dedicado pendentes | runbook privado (fora do Git), §9e–9f |

**Divergências Git × implantado:** o ADR-013 (troca do banco ativo, aceito segundo o
relato) não está no Git; o script e as unidades da rotina de backup existem só na VM; o
roadmap geral não registrava a frente de infraestrutura (corrigido nesta sprint). O
checkout principal (outra branch, limpo) não foi tocado.

## Entregas

| Área | Arquivos |
|---|---|
| Verificador | `app/ops/{config,report,systemd,checks,backup,verifier,cli}.py` |
| Alerta e unidades | `app/ops/{alert,units}.py`, `deploy/ops/*.in`, `deploy/ops/lab.params`, `deploy/ops/ops.env.example` |
| Bancada PostgreSQL | `app/ops/{pgcluster,drill}.py`, `scripts/ops/pg_gate.py`, job `postgres-gate` em `.github/workflows/ci.yml` |
| Testes | `tests/ops_support.py`, `tests/test_ops_{contract,systemd,backup,cli,postgres,units,drill}.py` |
| Documentação | runbook, checklist da janela, ADR-014, roadmap geral (§ 2.1), roadmap de infraestrutura (§3.4, §3.5, §6), `how_to_run.md` § 9, `testing.md`, índices |

Nenhuma alteração em contratos da API, modelos de domínio, migrations ou na rotina de
backup existente. O job SQLite do CI ficou intacto (o diff do workflow é só de inserções).

## Correções da revisão antes da publicação

1. **Falha com relatório saudável anterior silenciava o alerta.** Se a execução que falha
   não escreve relatório (venv quebrado, disco cheio, timeout do systemd), o
   `last-check.json` em disco é o da execução anterior; sendo saudável e recente, o alerta
   respondia "sem alerta" — reproduzido antes da correção. Agora a unidade de alerta chama
   `alert --expect-failure`, que nunca silencia; o `check` grava o `INVOCATION_ID` do
   systemd no relatório e o alerta o compara com o `MONITOR_INVOCATION_ID` entregue pelo
   `OnFailure=` (`report_not_from_failed_run` / `run_failed_but_report_healthy`, nível
   inconclusivo, sem listar problemas antigos como atuais). Quatro testes novos.
2. **Reversão do runbook.** O bloco anterior não funcionava (`<prefixo>` num bloco de shell
   é redirecionamento), usava `systemctl reset-failed` sem argumento (apagaria o estado de
   falha de todas as unidades do host, inclusive do backup), não removia o drop-in do teste
   de alerta, não protegia o `db.env` do app nem conferia o resultado. Reescrito com
   variáveis, `reset-failed` só nas unidades do verificador, guarda contra prefixo vazio,
   repetível e com conferência final. Corrigidos também o teste de alerta da instalação (um
   drop-in com `Environment=` não venceria o `EnvironmentFile=`) e os demais comandos com
   `<...>` no runbook e no checklist.
3. **`systemd-analyze verify` obrigatório no CI.** Passo próprio no `postgres-gate` com
   `CARTORIO_OPS_REQUIRE_SYSTEMD_ANALYZE=1`: sem a ferramenta o teste falha em vez de pular,
   e `-rA` deixa o `PASSED` nominal no log.
4. `apt-get update` antes da instalação do PGDG, para não depender do cache do runner.

## Correções da revisão do PR #6

Quatro achados da revisão, cada um com teste de regressão, em commits aditivos sobre
`95c0c27`. Ficaram intocados a API, o domínio, as migrations, a rotina de backup, as
proteções de identidade dos clusters e a correlação do alerta por execução do systemd.

| # | Achado | Correção | Testes |
|---|---|---|---|
| 1 | Sob umask `022`, o modo cópia deixava a cópia do dump em `0644` dentro de diretórios `0755`; o runbook sugeria `--work-root /tmp` | Diretórios `0700` e arquivos `0600` criados já com o modo (dump e manifesto copiados, `pgpass`, senha do `initdb`, marcador, identidade); ensaio e gate sob umask `077`; modos registrados no relatório (`isolation`); relatório com credencial gerada não é gravado (`secret_in_report`); **no Windows o modo cópia é recusado antes de copiar** (`copy_mode_unsupported_platform`); exemplos com `mktemp -d` | `test_copy_mode_is_private_under_umask_022_and_leaves_the_source_untouched`, `test_credentials_are_private_from_creation`, `test_area_kept_after_failure_stays_private` (POSIX); `test_copy_mode_is_refused_before_copying_where_isolation_is_unprovable`; `test_report_with_a_generated_credential_is_never_written`; no gate, modo cópia ponta a ponta sob umask `022` |
| 2 | Manifesto de outro banco passava como cópia válida | Banco esperado pelo nome inequívoco da DSN PostgreSQL e/ou `CARTORIO_OPS_BACKUP_EXPECTED_DATABASE` (coerentes; `dbname`/`service`/`servicefile` na query tornam a DSN ambígua; ausência ou ambiguidade é inconclusivo); comparação antes de a cópia contar como válida (`database_mismatch`, sem nomes no JSON); o ensaio usa a mesma validação, com `--expect-database` obrigatório no modo cópia | `test_ops_backup.py` (banco certo, banco estranho, cópia anterior correta mantida como último ponto válido, DSN ambígua, conflito, ausência, nome inválido); `test_copy_of_another_database_is_refused_before_restoring`; no gate, banco divergente recusado sem cluster |
| 3 | Parada que falhava ainda resultava em `passed`, saída 0, `clusters_stopped=false` e diretório removido; timeout na partida podia deixar postmaster ativo | Estado por cluster (não iniciado, parado confirmado, incerto); parada tentada em todos mesmo com falha ou exceção; remoção só com todas as paradas confirmadas por `pg_ctl status` — senão a área fica preservada, com diagnóstico; `passed` exige `cleanup.confirmed` (`cleanup_unconfirmed`); o gate só começa a prova de restauração depois da limpeza confirmada | Falhas induzidas em `test_ops_drill.py`: timeout na partida, exceção e falha na parada, remoção que falha, falha original preservada, ensaio completo com cluster possivelmente ativo e gate sem restauração |
| 4 | Com `--output` falhando e checagens saudáveis, o stdout dizia `ok`/0 e o processo saía 2 | Resultado final fechado antes de imprimir; bloco `output` no envelope; saudável vira `inconclusive`/`output_not_published` (2), falha continua `fail` (1); stdout igual ao arquivo quando publicado | `test_unpublished_output_keeps_stdout_and_exit_code_in_agreement` (saudável, falha e inconclusivo), `test_published_output_equals_stdout_and_exit_code`, `test_without_output_the_envelope_says_so` |

**Antes e depois (bancada local, dados sintéticos, códigos de saída reais).** Antes da
correção:
- cópia de outro banco → `ok`;
- parada que falha → diretório removido com `clusters_stopped=false`;
- `--output` inválido → stdout `ok`/0 com saída real 2.

Depois:
- cópia de outro banco → `fail`/`database_mismatch`, sem nomes no JSON;
- com uma cópia anterior correta, `last_valid_copy` e `age` ficam `ok` e o `last_copy` falha;
- sem banco esperado → `inconclusive`/`expected_database_missing`;
- parada que falha → área preservada, `confirmed=false`, e um ensaio aprovado vira
  `failed`/`cleanup_unconfirmed`;
- `--output` inválido → stdout `inconclusive`/`output_not_published`/2, saída real 2;
- `--output` válido → saída 0, com o arquivo igual ao stdout;
- modo cópia nesta bancada Windows → `refused`/`copy_mode_unsupported_platform`, saída 2,
  nada criado na raiz e origem intocada.

Os modos `0700`/`0600` sob umask `022` só existem em POSIX: a prova é do CI Linux (testes
acima com `-rA` e o modo cópia do gate).

Prova local desta rodada:
- `ruff format --check` e `ruff check` limpos;
- `pytest -q` com **1576 passed, 17 skipped**: os 3 skips novos são os testes POSIX da área
  privada;
- Alembic em SQLite temporário: `upgrade`/`current`/`heads` em `f4a5b6c7d8e9`, e `check`
  sem operação pendente; `cartorio.db` ausente antes e depois.

O resultado do CI fica no PR.

## Decisões assumidas (reversíveis)

1. **Local do código:** `app/ops/` (vai junto com a release, sem importar módulos de
   domínio); orquestração de teste em `scripts/ops/`.
2. **Saída:** `0` saudável · `1` falha detectada · `2` inconclusivo (inclui uso inválido e
   erro interno). Falha vence inconclusivo. Checagem não selecionada é `skipped`; nenhuma
   executada é inconclusivo.
3. **Classificação:** `fail` = evidência de desvio (inclusive timeout); `inconclusive` =
   sem evidência (configuração do verificador, ferramenta ausente, permissão).
4. **DSN:** o verificador lê `DATABASE_URL` — apontar seu `EnvironmentFile` para o `db.env`
   do app prova a DSN em uso sem duplicar a credencial; papel próprio é alternativa.
5. **Somente leitura:** PostgreSQL em `SET TRANSACTION READ ONLY` com `statement_timeout`;
   SQLite em `mode=ro` + `query_only` (nunca cria o arquivo).
6. **Release consultada:** heads lidas do diretório `alembic/` da release, sem executar
   `env.py`; identidade pela pasta `releases/<sha>` ou variável.
7. **Backup:** formato do manifesto existente; idade pelo `gerado_em_utc`; integridade pelo
   SHA-256 recalculado; tolerância de relógio 5 min; carência de publicação parcial 10 min
   (pelo mtime, único uso dele); restauração testada como sinal próprio.
8. **systemd:** um `systemctl show` por unidade, `--timestamp=unix` (systemd ≥ 251);
   serviço persistente só passa em `active/running` — o guarda-chuva `postgresql.service`
   é recusado.
9. **Alerta:** `OnFailure=` → unidade de alerta (`--expect-failure`) → spool local; sem
   deduplicação; relatório com mais de 15 min conta como ausente.
10. **Ensaio:** nunca recebe DSN; identidade por token lido do diretório de dados pelo
    próprio servidor, `cluster_name`, porta, `listen_addresses` e `system_identifier`
    distinto; todo endereço passa pelo guarda de loopback; destino com marcador da
    execução e vazio; origem desligada antes da consulta.
11. **CI:** PostgreSQL 18 do PGDG sem cluster padrão; o gate cria os seus. Teste pulado
    reprova.
12. **Modo cópia no Windows:** recusado antes de copiar, em vez de verificar ACL — lá o
    isolamento da cópia dependeria da ACL herdada da raiz escolhida.

## Comandos e resultados (prova local, não é resultado de GitHub Actions)

| Comando | Resultado |
|---|---|
| `ruff format --check .` | 208 arquivos formatados |
| `ruff check .` | limpo |
| `pytest -q` | **1529 passed, 14 skipped** (+169 testes sobre o baseline; +7 skips explicados abaixo) |
| `alembic upgrade head / current / heads / check` em SQLite temporário | `f4a5b6c7d8e9 (head)`; "No new upgrade operations detected."; `cartorio.db` ausente antes e depois |
| `pytest tests/test_ops_postgres.py` (com driver, sem servidor) | 1 passed, 5 skipped (exigem servidor) |
| `python -m app.ops.cli check` sem configuração | saída 2, cada checagem `config_missing` |
| `render-units` com `lab.params` | 3 unidades geradas |
| YAML do workflow | 2 jobs; `quality-gate` com os mesmos 7 passos |
| `bandit` 1.9.4 (venv isolado) em `app/ops` + `scripts/ops` | 11 baixos (B404×4, B603×6, B607×1 — subprocesso por lista, sem shell), 0 médio, 0 alto |
| `bandit -r app` | além dos acima, 2 preexistentes em arquivos não tocados: B324 alto em `drive_capture/collector.py:348`, B108 médio em `retention/rules.py:103` |
| `pip-audit` 2.10.1 sobre o ambiente `.[dev,postgres]` | nenhuma vulnerabilidade conhecida |

Os 14 skips locais: 5 da suíte do PR #5 e 5 de `test_ops_postgres.py` (exigem
`CARTORIO_TEST_POSTGRES_URL`), Drive (dependência opcional ausente), `chmod` e link
simbólico (privilégio no Windows) e `systemd-analyze verify` (inexistente no Windows; no
CI roda em passo próprio e obrigatório).

## Varredura de segredos e dados privados executada

- **Repositório público.** A revisão considerou que tudo o que for publicado — inclusive o
  histórico de commits — fica legível por qualquer pessoa.
- **Escopo:** o diff inteiro a publicar (`git diff c49c6579..HEAD` da branch — os 37
  arquivos adicionados ou alterados), o patch de cada commit e as mensagens dos commits.
- **Método:** script Python local, sem dependência externa, com três famílias:
  1. padrões de segredo — DSN com senha (exceto os marcadores fictícios dos testes), chave
     privada PEM, chave de acesso AWS, token do GitHub e atribuição literal de
     `password`/`senha`/`secret`/`token`;
  2. **valores reais conhecidos do ambiente privado** — 13 itens: IP e impressão digital da
     chave SSH da VM, usuário de acesso, nomes de unidades, papéis e banco da homologação,
     prefixos de SHA-256 de dumps reais e nomes de arquivos privados. A lista em si fica
     fora do Git;
  3. caminho de perfil de usuário Windows e endereços de e-mail.
- **Leitura humana** de todo o diff, incluindo a lista de caminhos absolutos, IPs e
  horários concretos das linhas adicionadas: caminhos só de laboratório ou genéricos; IPs
  só de loopback ou fictícios usados em testes de recusa.
- **Retirado por ser detalhe operacional real, sem valor de revisão num repositório
  público** (não eram segredos, e a varredura por padrão não os pegaria): horários e
  agenda da rotina de backup da homologação, o nome real de um dump e a contagem real do
  seu TOC usados como amostra num teste, a versão exata do servidor da homologação e a
  janela prevista de acesso físico ao equipamento. Datas de marco foram mantidas porque
  separam o que está no Git do que está implantado. Como nada havia sido publicado, o
  histórico local foi refeito para que esses detalhes não entrem em nenhum commit.
- **Resultado:** 0 ocorrências. Antes, a varredura também apontou um caminho de exemplo
  com nome de usuário real num teste, já substituído. Os valores fictícios propositais dos
  testes (como a senha usada para provar que nada vaza) foram conferidos um a um.

## Status do Gitleaks

**Não executado.** Localmente, exigiria baixar e executar um binário da internet — a
mesma classe de ação que não foi autorizada nesta sessão para o PostgreSQL —, então não
foi tentado. No CI ele não está integrado (dívida TD-10, sprint própria), e este PR não
acrescenta ferramenta de segurança ao CI. A varredura acima é substituta **específica**
(padrões conhecidos e valores reais deste ambiente), não equivalente ao conjunto de regras
do Gitleaks (entropia, centenas de formatos de provedor). Para fechar, em ambiente
autorizado: `gitleaks git --log-opts="c49c6579..sprint/cartorio-ops-1"`.

## Evidência dos cenários de aceite (bancada local)

| Cenário | Prova | Resultado local |
|---|---|---|
| API 200 com PostgreSQL indisponível | `test_api_200_with_postgres_unavailable_fails_overall`: uvicorn real, psycopg real, porta fechada, CLI em processo próprio | ✅ saída 1; `api` ok com HTTP 200; `database` `fail` (no Windows o driver só desiste no prazo → `timeout`; no Linux, `unavailable`); senha ausente da saída. Variante SQLite também ✅, sem criar o arquivo |
| Backup vencido com artefato presente | `test_stale_copy_with_artifact_present_reports_delay` (relógio fixo: 30,0 h > 26 h); `test_stale_backup_triggers_the_local_test_alert` | ✅ `backup_stale`; relatório publicado; alerta no spool com `backup: backup_stale` |
| Cópia ausente, incompleta, corrompida ou sem evidência | `test_ops_backup.py` | ✅ `backup_missing`, `size_mismatch`, `digest_mismatch`, `manifest_incomplete`, `no_verifiable_copy`, `unverifiable_copy`; referência fora do diretório, ponto futuro e ilegível recusados |
| Última tentativa falhou, cópia anterior válida | `test_failed_attempt_and_previous_valid_copy_appear_together` (+ variante CLI) | ✅ `last_attempt_failed` com `last_copy`, `integrity` e `age` em ok no mesmo relatório |
| Falha com relatório saudável anterior | `test_failure_with_previous_healthy_report_still_alerts` e os três vizinhos | ✅ alerta gravado com `run_failed_but_report_healthy` ou `report_not_from_failed_run`; problemas antigos não aparecem como atuais |
| Revisão Alembic divergente | `test_alembic_divergence_is_reported_without_applying_migrations` | ✅ (SQLite) `revision_behind`, banco intocado; `revision_unknown` também. Variante PostgreSQL: CI |
| Backup restaurado | `python -m app.ops.drill` via `pg_gate.py` | ⏳ CI. Provados sem servidor: recusas de alvo (inclusive endereço fora do loopback), contrato do relatório, leitura do TOC, cliente HTTP do ensaio contra a API real |
| Configuração saudável e completa | `test_healthy_and_complete_configuration_returns_zero` | ✅ saída 0 com API real, SQLite real, Alembic real, backup sintético e systemd sintético. Variante PostgreSQL: CI |

## Pendências reais

| Prova | Comando | Causa | Impacto |
|---|---|---|---|
| Gate PostgreSQL completo e `systemd-analyze verify` | job `postgres-gate` (localmente: `python scripts/ops/pg_gate.py --pg-bin "$PG_BIN" --work-root "$TRABALHO" --report "$RELATORIO"`) | sem PostgreSQL nem systemd na bancada local | aceite depende do CI do PR; é a primeira execução desses passos |
| Gitleaks | ver seção acima | binário externo não autorizado; fora do CI (TD-10) | coberto por varredura específica, não pela ferramenta |
| Itens da janela real | [checklist](../operations/ops_window_checklist.md) | acesso à VM, ao host e ao PC dedicado | aceite real inexistente — esta sprint é código e bancada |

## Observações de risco

- **Verificador e alerta vivem dentro da VM:** queda da VM ou do host não alerta.
- **Rotina de backup e ADR-013 fora do Git:** a revisão e a reprodução dependem do
  ambiente privado. Versioná-los é tarefa própria — esta sprint não altera a rotina.
- **Comportamentos de plataforma achados na bancada:** no Windows, recusa de conexão em
  loopback chega como `ConnectionTimeout` do psycopg; `initdb` exige diretório ASCII.
- **Tempos de bancada não são RTO:** o ensaio registra os tempos como medição de bancada.
- **Modo cópia só em Linux:** se o PC dedicado for Windows, a restauração isolada do
  item 3 do checklist precisa de um ambiente Linux, decidido na janela.

## Passos da janela de implantação

Na ordem: (1) merge e implantação da release pelo procedimento por SHA; (2) arquivo de
configuração com os valores decididos; (3) execução única via `systemd-run`; (4) unidades
geradas, verificadas e instaladas; (5) timer habilitado; (6) prova opcional da cadeia de
alerta; (7) itens 1–4 do checklist com evidência fora do Git. Detalhe e reversão:
[runbook §7–§8](../operations/ops_verifier_runbook.md).
