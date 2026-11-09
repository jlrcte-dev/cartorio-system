# ADR-016 — Política de proteção do banco: RPO, retenção, destino e executor da cópia fora do host

- **Status:** Proposto — aguardando decisão do responsável do projeto. Nenhum valor marcado
  como proposta vale antes do aceite registrado aqui. Para aceite: (1) destino e executor;
  (2) direção do transporte e identidade; (3) retenção no destino e a regra comum; (4) regra
  de prova e cadência do ensaio; (5) cifragem e custódia como condição para dado real.
- **Data:** 2026-11-09
- **Sprint:** `CARTORIO-BACKUP-POLICY-1` (documental; nenhum código, rotina ou unidade muda)
- **Relação:** reúne os parâmetros de backup da
  [ADR-013](ADR-013-troca-banco-ativo-sqlite-postgresql.md), da
  [ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md) e da
  [ADR-015](ADR-015-copia-verificada-e-observador-fora-do-host.md)
- **Operação:** [`ops_backup_routine.md`](../operations/ops_backup_routine.md),
  [`ops_offsite_pilot.md`](../operations/ops_offsite_pilot.md)

---

## Contexto

As peças de proteção do banco já existem, mas nenhuma política diz qual RPO perseguir,
quanto guardar, onde fica a cópia fora do host, quem a transporta e como se prova que ela
restaura:

- **Rotina local diária** da homologação: 14 cópias, `pg_dump` publicado só depois do
  `pg_restore --list` e manifesto com SHA-256. São parâmetros de laboratório, com dado
  sintético ([`ops_backup_routine.md`](../operations/ops_backup_routine.md)).
- **Verificador e prova de recuperação em bancada**
  ([ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md)). A evidência de
  restauração é opcional: sem ela, o sinal fica `NOT_CONFIGURED` e não pesa no resultado, de
  modo que o verificador pode dizer `ok` sem nenhum teste de restauração.
- **Cópia verificada fora do host, em piloto**
  ([ADR-015](ADR-015-copia-verificada-e-observador-fora-do-host.md)): importação conferida,
  gerações promovidas por `rename` e observador que mede a idade pelo manifesto. Transporte
  de rede, agenda, retenção e alerta ficaram como etapas posteriores (`app/ops/offsite.py`).
- **Metas registradas** para a serventia: RPO ≤ 4 h e RTO ≤ 8 h
  ([`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md)
  §14), e a D-22 põe o banco de produção no PRD com RPO ≤ 4 h. São metas, não conformidade
  declarada.
- A [ADR-013](ADR-013-troca-banco-ativo-sqlite-postgresql.md) exige o destino fora da VM
  antes de qualquer corte com dado real.
- A serventia tem uma política de backup própria no programa de adequação à LGPD (ação
  AC-14), cujo conteúdo não está neste repositório
  ([relatório](../analysis/lgpd_module_context_report.md)). Esta ADR cobre só o banco do
  Cartório System.

São duas proteções, que não se substituem. A **cópia local**, no disco da VM, desfaz erro
lógico e corrupção e se perde com a VM ou o host. A **cópia fora do host** sobrevive a essa
perda e só existe se o transporte rodar. Cada uma tem a sua idade.

## Decisão

Proposta em dois regimes. A coluna Situação usa FATO (código ou documento versionado), META
REGISTRADA, PLANEJADO (roadmap) e PROPOSTO (esta ADR, sem aceite).

| Item | Homologação, dado sintético (hoje) | Dado real (corte futuro, não autorizado) | Situação |
| --- | --- | --- | --- |
| RPO | nenhum RPO novo; a rotina diária é parâmetro de laboratório e **não** cumpre a meta | a meta registrada, RPO ≤ 4 h | FATO / META REGISTRADA |
| Captura local | diária, 14 cópias em `recorrentes/`; as cópias de corte ficam fora da poda | `pg_dump` a cada 4 h, conforme o [roadmap de infraestrutura](../infrastructure/infrastructure_roadmap.md) §3.2 | FATO (laboratório) / PLANEJADO |
| Retenção no destino | as 14 gerações mais recentes; exclusão só com registro de quem, quando e o quê | a do roadmap de infraestrutura e da trilha regulatória, ainda em aberto | PROPOSTO / PLANEJADO |
| Regra comum de retenção | nunca apagar a geração conferida e restaurada mais nova | idem | PROPOSTO |
| Destino | o PC dedicado da serventia, exclusivo do domínio Cartório | idem, mais uma cópia em outro endereço físico | PROPOSTO |
| Executor | o próprio PC; importar e restaurar exigem sistema POSIX (`app/ops/offsite.py` recusa Windows) | idem | FATO (requisito) / PROPOSTO (o PC) |
| Transporte | puxado pelo PC, com identidade só do Cartório e só de leitura na origem | idem | PROPOSTO |
| Validação e idade | `evaluate_publication` na origem e no preparo; idade pelo ponto de recuperação do manifesto, nunca pelo `mtime` | idem | FATO (código; nada instalado) |
| Restauração | modo cópia do ensaio (`--from-manifest`); o passo OPS-2 do `postgres-gate` restaura só a partir do destino, com dado sintético; na homologação, a restauração a partir do PC segue pendente (item 3 do [checklist da janela](../operations/ops_window_checklist.md)) | idem, com teste de restauração no mínimo trimestral (roadmap de infraestrutura §3.5) | FATO / PLANEJADO |
| Cifragem e custódia | não exigidas com dado sintético | exigidas antes do corte: disco ou cópia cifrada, chave fora do PC, registro de acesso | PROPOSTO |

1. **Regra de prova (proposta).** Uma geração só conta como proteção depois de restaurada a
   partir do PC, em ambiente isolado, com a revisão do schema conferida. O manifesto não traz
   revisão, que só se prova na restauração. `ok` do verificador sem evidência de restauração
   não conta.
2. **Separação por domínio (proposta).** O PC guarda só cópias do Cartório System e não
   recebe cópia de nenhum outro sistema. A identidade que lê a origem é exclusiva deste
   domínio. Cópias deste banco não vão para equipamento de outro domínio.
3. **Responsabilidades.** A origem (a VM) publica o par só depois de validá-lo, declara o
   ponto de recuperação e o digest, e não escreve no destino. O destino importa só o que a
   origem publicou, confere de novo no preparo, promove por `rename` e preserva a última
   geração válida.
4. **Fora desta ADR.** Transporte, agenda da importação e do observador, poda, canal de
   alerta, cifragem e a rotina de 4 h são implementações com janela e autorização próprias.
   Esta ADR não muda código, rotina, manifesto nem unidade.

## Consequências positivas

- As decisões que a §8 do [guia do piloto](../operations/ops_offsite_pilot.md) deixa ao
  responsável do projeto passam a ter uma proposta única para aceitar, ajustar ou recusar.
- A rotina diária deixa de parecer RPO: fica explícito que ela não serve para dado real.
- "A cópia existe" e "a cópia restaura" viram afirmações separadas, e a segunda vira o
  critério.

## Consequências negativas

- Puxar pelo PC exige uma conta de leitura na origem. Hoje a pasta de backups não é legível
  pelo usuário de observação ([`ops_backup_routine.md`](../operations/ops_backup_routine.md)).
- O PC no mesmo local cobre a perda do host, não a da serventia. Dado real pede cópia em
  outro endereço, com planejamento próprio.
- Cumprir RPO ≤ 4 h com dado real exige rotina nova, não ajuste de parâmetro.

## Alternativas consideradas

- **Usar o PC também para cópias de outros sistemas.** Mistura domínios num equipamento da
  serventia e amplia quem precisa de acesso a ele.
- **Enviar pela VM (push).** A origem passaria a guardar credencial de escrita no destino, e
  uma VM comprometida alcançaria também a cópia.
- **VM de backup no mesmo host.** Cai junto com o host, que é o cenário a cobrir
  ([ADR-015](ADR-015-copia-verificada-e-observador-fora-do-host.md)). A
  [ADR-013](ADR-013-troca-banco-ativo-sqlite-postgresql.md) ainda a menciona como destino
  possível; esta ADR segue a ADR-015.
- **RPO de 24 h também para dado real.** Fica abaixo da meta registrada.

## Referências

- [ADR-013](ADR-013-troca-banco-ativo-sqlite-postgresql.md),
  [ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md) e
  [ADR-015](ADR-015-copia-verificada-e-observador-fora-do-host.md)
- [`technical_decisions.md`](technical_decisions.md), D-22
- [`CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md`](../../CARTORIO_SYSTEM_PROJECT_CONFIGURATION.md), §14
- [Roadmap CNJ 213](../regulatory/cnj_213/roadmap.md) e
  [roadmap de infraestrutura](../infrastructure/infrastructure_roadmap.md), §3
- [`ops_backup_routine.md`](../operations/ops_backup_routine.md),
  [`ops_offsite_pilot.md`](../operations/ops_offsite_pilot.md) e
  [`ops_window_checklist.md`](../operations/ops_window_checklist.md), item 3
