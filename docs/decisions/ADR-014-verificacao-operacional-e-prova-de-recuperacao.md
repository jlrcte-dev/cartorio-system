# ADR-014 — Verificação operacional somente leitura e prova de recuperação em bancada

- **Status:** Proposto — integrado em `main` e provado com dados sintéticos na bancada local
  e no CI. O aceite depende da instalação e da evidência numa janela própria
  ([checklist](../operations/ops_window_checklist.md), itens 1 a 5).
- **Evidência de engenharia (08/11/2026):** PR #6 integrado como merge `b22e1b6` (pais
  `c49c6579` e `7b92e4d`), com árvore igual à da revisão testada no PR. CI do PR
  `42413480266` e pós-merge `42431949823` verdes, com PostgreSQL 18.6: 36 testes do gate
  aprovados, nenhum pulado, `systemd-analyze verify` aprovado e quatro relatórios liberados.
  Não substitui o aceite operacional.
- **Data:** 2026-11-07
- **Sprint:** `CARTORIO-OPS-1` (Fase 1 do roadmap de infraestrutura)
- **Código:** `app/ops/`, `deploy/ops/`, `scripts/ops/pg_gate.py`, job `postgres-gate`
- **Operação:** [`docs/operations/ops_verifier_runbook.md`](../operations/ops_verifier_runbook.md)

---

## Contexto

A homologação do Cartório System passou a rodar em PostgreSQL 18 numa VM do Proxmox em
07/11/2026, segundo o relato operacional (a decisão correspondente, ADR-013, existe como
minuta local e ainda não foi integrada ao Git). Uma rotina local de backup diário passou a
publicar `pg_dump` + manifesto com SHA-256. A própria minuta do ADR-013 deixou
"backup contínuo e monitoramento" como pendência, e a janela de corte registrou dois fatos
que tornam monitoramento por "processo de pé" insuficiente:

1. `GET /api/v1/health` responde sem tocar o banco, e a engine é preguiçosa: uma DSN
   quebrada sobe o serviço e passa no `/health`.
2. O `postgresql.service` do Debian/Ubuntu é guarda-chuva — reporta `active` mesmo com o
   cluster parado.

Não existia forma automatizada de dizer, a qualquer momento, se API, banco, revisão do
schema e backup estavam simultaneamente saudáveis — nem prova repetível de que uma cópia
publicada de fato restaura.

## Decisão

1. **Verificador somente leitura** (`python -m app.ops.cli check`) em `app/ops/`, fora dos
   módulos de domínio e sem importá-los, configurado só pelo ambiente. Quatro checagens
   independentes, cada uma com prazo e isolamento de falha: processo/API (unidades systemd
   por tipo — persistente, oneshot, timer — e `/health`), PostgreSQL (consulta real em
   transação somente leitura, dialeto conferido), Alembic (revisão do banco contra as heads
   da release consultada, sem aplicar migration) e backup.
2. **Contrato de saída** `cartorio_system.ops.check` 1.0, com instante UTC, estado geral,
   estado e motivo estável por checagem. Códigos: `0` saudável (todas as obrigatórias
   comprovadas), `1` falha detectada, `2` inconclusivo. Precedência: falha > inconclusivo
   > ok. Nada de DSN, host, usuário, mensagem de exceção ou conteúdo do banco na saída.
   O JSON impresso é o resultado final, igual ao arquivo publicado; se a publicação falhar
   com as checagens saudáveis, o resultado é inconclusivo (`output_not_published`).
3. **Backup avaliado pela evidência que a rotina já publica**, sem alterar a rotina: a idade
   vem do ponto de recuperação do manifesto (nunca do mtime); a integridade é o digest
   recalculado contra o manifesto do mesmo artefato; publicação parcial é indisponível, e
   além de uma carência curta vira falha (`unverifiable_copy`); referência fora do
   diretório é recusada; a publicação precisa ser do banco esperado — com a checagem do
   banco na mesma execução em PostgreSQL, o que a conexão abriu de fato
   (`current_database()`), com o nome explícito e o da DSN coerentes com ele; isolada, o que
   a DSN abriria, lido como o driver a lê, e/ou o nome explícito, coerentes. Sem identidade
   comprovada a checagem nunca é saudável, mas as falhas que independem dela continuam
   visíveis. Cópia recente, integridade verificada e restauração testada são sinais
   distintos; tentativa nova falha e cópia anterior válida aparecem juntas.
4. **Alerta por código de saída**: agenda própria (independente do timer do backup) e
   `OnFailure=` para uma unidade que converte o relatório em alerta num spool local. O
   canal definitivo é decisão de implantação, sobre o mesmo payload.
5. **Prova de recuperação só em bancada descartável** (`python -m app.ops.drill`): o ensaio
   nunca recebe DSN; cria origem e destino próprios, em loopback, com credencial gerada, e
   comprova a identidade antes de qualquer escrita. Recusa alvo externo, reaproveitado ou
   sem identidade comprovada; limpa só o que criou, inclusive em falha, e só depois de
   confirmar a parada de todos os clusters (parada incerta preserva a área e reprova). A
   área de trabalho é privada desde a criação, e a exportação nunca altera um destino que
   já existe (recusa o que não protege a cópia). O modo cópia exige o banco esperado
   informado à parte e só roda em Linux, como a exportação que o alimenta.
6. **Gate PostgreSQL separado** no CI (`postgres-gate`, PostgreSQL 18 do PGDG), com o mesmo
   comando local (`scripts/ops/pg_gate.py`): suíte do PR #5 + cenários do verificador +
   ensaio de recuperação. Prova obrigatória pulada reprova o gate. O gate SQLite fica como
   estava. Num repositório público o log do CI também é público: a saída dos subprocessos
   é conferida antes de qualquer impressão, e o artefato é só o que o gate libera
   explicitamente, conferido de novo na seleção.

## Consequências positivas

- "Serviço de pé" deixa de ser confundido com "sistema saudável": banco, schema e backup
  passam a ter evidência própria e motivo legível por automação.
- A evidência de backup passa a ter idade, integridade e restaurabilidade separadas — o
  formato serve de registro para a medição de RPO/RTO exigida para a Classe 3.
- A prova de recuperação deixa de depender de sessão manual na VM: é repetível em qualquer
  bancada com PostgreSQL 18 e no CI.

## Consequências negativas

- Mais uma superfície de configuração na VM (arquivo de ambiente, três unidades).
- O alerta é local: VM ou host fora do ar não alertam. Observador externo continua pendente.
- O verificador usa a mesma DSN do app (ou um papel próprio, a decidir): com a DSN do app,
  o processo do verificador detém uma credencial com escrita, contida pela transação
  somente leitura e pelo código revisado.
- O job `postgres-gate` acrescenta alguns minutos e uma dependência do repositório PGDG.

## Alternativas consideradas

- **`/ready` aprofundado na própria API.** Mudaria o contrato público da API e não cobriria
  backup nem timer; o verificador não precisa do app de pé para diagnosticar o app.
- **Pilha de monitoramento (Prometheus/exporters).** Desproporcional para uma VM de
  homologação com um serviço; pode vir depois, consumindo o mesmo JSON.
- **Script de shell com `cron`.** Sem contrato versionado, sem testes, sem separação entre
  falha e falta de evidência.
- **Contêiner de serviço do GitHub para o PostgreSQL do CI.** Credencial estática no YAML e
  impossível de reproduzir igual na bancada local; o gate cria o próprio cluster.

## Referências

- PR #5 (compatibilidade PostgreSQL): https://github.com/jlrcte-dev/cartorio-system/pull/5
- PR #6 (esta decisão): https://github.com/jlrcte-dev/cartorio-system/pull/6 — CI pós-merge:
  https://github.com/jlrcte-dev/cartorio-system/actions/runs/42431949823
- [`docs/infrastructure/infrastructure_roadmap.md`](../infrastructure/infrastructure_roadmap.md) §3.4–3.5 e §6
- [`docs/operations/ops_window_checklist.md`](../operations/ops_window_checklist.md)
- [`docs/reports/RELATORIO_CARTORIO_OPS_1.md`](../reports/RELATORIO_CARTORIO_OPS_1.md)
