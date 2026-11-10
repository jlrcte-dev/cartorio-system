# ADR-016 — Política de proteção do banco: RPO, retenção, destino e executor da cópia fora do host

- **Status:** Aceito — decisão expressa do responsável do projeto em 09/11/2026, registrada
  em *Registro do aceite*. *Escopo da aceitação:* destino e executor, modelo de captura,
  transporte e identidade, retenção da homologação, regra de prova e a preservação das metas
  registradas para dado real. É aceite **documental**: nada foi implantado, e transporte,
  identidade, agenda, poda, alerta e ensaio a partir do PC têm janela e autorização
  próprias. Não declara aptidão para dado real nem cumprimento de RPO ou RTO. A retenção
  definitiva e a cifragem do regime de dado real seguem para decisão específica. O aceite
  não muda o status da ADR-014 nem o da ADR-015.
- **Data:** 2026-11-09 (proposta e aceite)
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

Dois regimes. A coluna Situação usa FATO (código ou documento versionado), META REGISTRADA,
PLANEJADO (roadmap), ACEITO (esta ADR, desde 09/11/2026 — aceito não é implantado) e
PROPOSTO (ainda sem decisão).

| Item | Homologação, dado sintético (hoje) | Dado real (corte futuro, não autorizado) | Situação |
| --- | --- | --- | --- |
| RPO e RTO | nenhum RPO novo; a rotina diária é parâmetro de laboratório e **não** cumpre a meta | as metas registradas, RPO ≤ 4 h e RTO ≤ 8 h, nenhuma comprovada | FATO / META REGISTRADA |
| Captura local | diária, sob responsabilidade da VM, 14 cópias em `recorrentes/`; as cópias de corte ficam fora da poda | `pg_dump` a cada 4 h, conforme o [roadmap de infraestrutura](../infrastructure/infrastructure_roadmap.md) §3.2 | FATO (laboratório) / PLANEJADO |
| Retenção no destino | as 14 gerações mais recentes; as cópias de corte ficam fora da poda recorrente; exclusão só com registro de quem, quando e o quê | a do roadmap de infraestrutura, da trilha regulatória e da política da serventia, sujeita a decisão específica | ACEITO / PLANEJADO |
| Regra comum de retenção | nunca apagar automaticamente a geração mais nova comprovadamente válida e restaurável (conferida e restaurada), nem arquivo que a poda não reconhece; a poda não roda junto de importação ou promoção | idem | ACEITO |
| Destino | o PC dedicado da serventia, exclusivo do domínio Cartório | idem, mais uma cópia em outro endereço físico | ACEITO (o PC) / PROPOSTO (outro endereço) |
| Executor | o próprio PC; importar e restaurar exigem sistema POSIX (`app/ops/offsite.py` recusa Windows) | idem | FATO (requisito) / ACEITO (o PC) |
| Transporte | puxado pelo PC, com identidade só do Cartório e só de leitura na origem; a VM não recebe credencial de escrita no PC | idem | ACEITO |
| Validação e idade | `evaluate_publication` na origem e no preparo; idade pelo ponto de recuperação do manifesto, nunca pelo `mtime` | idem | FATO (código; nada instalado) |
| Restauração | modo cópia do ensaio (`--from-manifest`); o passo OPS-2 do `postgres-gate` restaura só a partir do destino, com dado sintético; na homologação, a restauração a partir do PC segue pendente (item 3 do [checklist da janela](../operations/ops_window_checklist.md)) | idem, com teste de restauração completo no mínimo trimestral (roadmap de infraestrutura §3.5) | FATO / PLANEJADO |
| Custódia | PC exclusivo do domínio, sem chave, credencial ou permissão compartilhada com outro domínio | idem, mais registro de acesso | ACEITO / PROPOSTO (registro de acesso) |
| Cifragem | não exigida com dado sintético | exigida antes do corte: disco ou cópia cifrada, chave fora do PC | PROPOSTO, para a decisão do regime real |

**Cinco afirmações que não se substituem.** Aceitar esta ADR não comprova nenhuma das quatro
últimas:

| Afirmação | Hoje (09/11/2026) |
| --- | --- |
| Meta aprovada | homologação: nenhum RPO novo; dado real: RPO ≤ 4 h e RTO ≤ 8 h registrados |
| Idade observada da cópia local | a da rotina diária de laboratório; os disparos automáticos foram lidos no journal da VM, sem digest recalculado ([`ops_backup_routine.md`](../operations/ops_backup_routine.md)) |
| Idade observada da cópia fora do host | não existe: o PC ainda não está disponível |
| Restauração comprovada | na homologação, uma vez, no disparo manual da rotina, na própria VM; nenhuma a partir do PC. A bancada e o CI provam o mecanismo, com dado sintético |
| Cumprimento operacional de RPO e RTO | nenhum; a rotina de homologação não serve de prova para dado real |

1. **Regra de prova (aceita).** Cada geração importada é conferida antes de promovida:
   digest e manifesto, pela `evaluate_publication`. Ela só conta como proteção depois de
   restaurada a partir do PC — com o arquivo importado lá, não com uma cópia que ficou na
   VM —, em ambiente isolado, com a revisão do schema conferida. O manifesto não traz revisão,
   que só se prova na restauração. `pg_restore --list` confere o dump e não é restauração, e
   `ok` do verificador sem evidência de restauração não conta. Cada ciclo ensaia a
   restauração isolada quando for tecnicamente viável e registra a evidência; falha preserva
   a última geração válida. Ciclo que não puder ensaiar registra o motivo, a última geração
   conferida, a última restauração comprovada, a idade dessa evidência e a pendência de
   validação. Ensaios periódicos de recuperação completa ficam planejados; para dado real, no
   mínimo trimestrais.
2. **Separação por domínio (aceita).** O PC guarda só cópias do Cartório System e não recebe
   cópia de nenhum outro sistema. Banco ou cópia deste sistema não vai para equipamento
   pessoal nem de outro domínio. A identidade que lê a origem é exclusiva deste domínio, e
   nenhuma chave, credencial ou permissão é compartilhada com outro domínio.
3. **Responsabilidades (aceitas).** A origem (a VM) captura — a rotina local da homologação
   continua dela —, publica o par só depois de validá-lo, declara o ponto de recuperação e o
   digest, e não escreve no destino. O PC inicia a transferência, não dispara captura na
   VM, importa só o que a origem publicou, confere de novo no preparo, promove por `rename`
   e preserva a última geração válida.
4. **Fora desta ADR.** Transporte, identidade e regras de acesso, agenda da importação e do
   observador, poda, canal de alerta, cifragem e a rotina de 4 h são implementações com
   janela e autorização próprias. Esta ADR não muda código, rotina, manifesto nem unidade, e
   aprovar a retenção não autoriza apagar nenhum arquivo.

## Registro do aceite

Em 09/11/2026 o responsável do projeto aprovou expressamente:

| # | Decisão | Aceito |
| --- | --- | --- |
| 1 | Destino, executor e custódia | o PC dedicado exclusivamente ao domínio Cartório; nenhum banco ou cópia do Cartório em equipamento pessoal; nada compartilhado entre domínios |
| 2 | Modelo de captura | a VM captura e mantém a rotina local da homologação; o PC transporta, importa e confere as cópias publicadas |
| 3 | RPO | homologação mantém a rotina e os parâmetros de laboratório; dado real mantém RPO ≤ 4 h e RTO ≤ 8 h registrados, sem cumprimento declarado |
| 4 | Retenção | homologação: 14 gerações na VM e 14 no destino, cópias de corte fora da poda; dado real: sem política definitiva, sujeita a decisão específica; a regra comum |
| 5 | Transporte e identidade | pull pelo PC; identidade só do Cartório, só de leitura das cópias publicadas |
| 6 | Prova de recuperação | conferência de cada geração importada, restauração isolada a partir do PC por ciclo quando viável, última geração válida preservada; ensaio completo no mínimo trimestral para dado real |

Pendentes, cada um com evidência e aceite próprios: o PC disponível e conferido (§8 do
[guia do piloto](../operations/ops_offsite_pilot.md)), identidade restrita na origem,
transporte, agenda, poda, canal de alerta, primeira restauração a partir do PC e as decisões
do regime de dado real.

## Consequências positivas

- Executor, transporte e retenção da homologação, que a §8 do
  [guia do piloto](../operations/ops_offsite_pilot.md) deixava ao responsável do projeto,
  ficam decididos num lugar só.
- A rotina diária deixa de parecer RPO: fica explícito que ela não serve para dado real.
- "A cópia existe" e "a cópia restaura" viram afirmações separadas, e a segunda vira o
  critério.

## Consequências negativas

- Puxar pelo PC exige uma conta de leitura na origem. Hoje a pasta de backups não é legível
  pelo usuário de observação ([`ops_backup_routine.md`](../operations/ops_backup_routine.md)).
- O PC no mesmo local cobre a perda do host, não a da serventia. Dado real pede cópia em
  outro endereço, com planejamento próprio.
- Cumprir RPO ≤ 4 h com dado real exige rotina nova, não ajuste de parâmetro.
- Até a implantação, a homologação continua sem cópia fora do host: o aceite decide, não
  protege.

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
