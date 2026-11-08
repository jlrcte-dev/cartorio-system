# ADR-013 — Troca do banco ativo de homologação de SQLite para PostgreSQL

- **Status:** Aceito — autorizado explicitamente pelo responsável do projeto e **executado**
  na VM de homologação em 07/11/2026; desde então o serviço da aplicação de homologação roda em
  PostgreSQL. *Escopo da aceitação:* o banco ativo da **homologação**, com dados
  sintéticos e acesso só por loopback. Não cobre a serventia real nem dado real do
  cartório, que exigem decisão própria.
- **Data:** 2026-11-06 (proposta) · 2026-11-07 (execução) · 2026-11-08 (registro no Git)
- **Sprint:** `CARTORIO-SYSTEM-HOMOLOGACAO-VM-1`, Fase B, mais os ensaios de recuperação e
  migração
- **Módulos:** `alembic/`, `app/db/session.py`, `pyproject.toml`
- **Guia e contrato:** [`technical_decisions.md`](technical_decisions.md) D-03 (SQLite
  agora, PostgreSQL quando o sistema sair do laptop)
- **Origem deste arquivo:** a minuta ficou fora do Git de 06 a 08/11. Esta versão mantém
  os fatos publicáveis e deixa fora caminhos de máquina, nomes de papéis e o roteiro
  operacional, que continuam no dossiê privado do operador.

---

## Contexto

A homologação rodava em SQLite, como previa a D-03 desde a fundação do projeto ("Postgres
é o destino quando o sistema sair do laptop"). A Fase B da homologação pediu a evidência
necessária para considerar a troca, ainda sem executá-la.

Quatro frentes foram ensaiadas em bancada PostgreSQL 18.6 descartável, sempre a partir do
commit integrado pelo PR #5 (`c49c6579cf97614323cd228f4b0c25825b40c2fe`, CI pós-merge
[`42277467291`](https://github.com/jlrcte-dev/cartorio-system/actions/runs/42277467291)
`success`):

1. **Compatibilidade de código (PR #5):** URL do Alembic, constraint `GLOB`, cinco defaults
   booleanos e suíte protegida contra desvio de identidade ou ambiente.
2. **`pg_dump`/`pg_restore`:** recuperação de uma bancada sintética.
3. **Migração SQLite → PostgreSQL:** paridade dos dados da homologação e uma segunda rodada
   sintética cobrindo valor monetário, booleanos, timestamps e FK. Inclui o ensaio de
   retorno ao SQLite antes e depois de o PostgreSQL receber escrita nova.
4. **Papéis, bloqueio de escrita, rotina de backup e gate monetário:** três papéis com
   privilégios distintos (migração, aplicação, backup), alternância real entre escrita
   bloqueada e liberada, backup com papel mínimo e migração tipada de valores nos limites
   de `NUMERIC(14,2)`.

Depois dos ensaios veio a **execução na homologação (07/11/2026)**. Foi feito, nesta ordem:

- congelamento dos escritores;
- snapshot final;
- carga tipada;
- paridade exata;
- backup testado e restaurado;
- evidência apresentada e autorização explícita;
- escrita liberada;
- persistência confirmada depois de um restart controlado.

## Decisão

**A troca foi executada no ambiente de homologação em 07/11/2026.** Esta ADR registra o
que ficou provado, o que foi executado e o que continua pendente. Inclui o que faltaria
para estender a decisão a dados reais da serventia, que é uma decisão própria, posterior e
maior.

### Provado

- O código roda em PostgreSQL 18.6 sem alteração de contrato (Fase B, PR #5 integrado).
- `pg_dump --format=custom` mais `pg_restore --single-transaction --no-owner
  --no-privileges` preservam:
  - a revisão Alembic;
  - as tabelas e as contagens;
  - os registros de referência, inclusive FK e booleanos;
  - o estado das sequências: uma escrita nova depois da restauração avança sem colisão.
- **Carga tipada SQLite → PostgreSQL.** A migração segue `Base.metadata.sorted_tables`
  (ordem de FK). Preserva:
  - IDs, FKs, booleanos, enums e datas;
  - timestamps, convertidos para UTC explícito; nenhum timestamp ambíguo apareceu neste
    SHA;
  - a precisão decimal dos valores monetários, convertidos por string formatada e nunca
    por `Decimal(float)`.

  A paridade é exata nas 16 tabelas de aplicação: contagem, conjunto de chaves primárias
  e conteúdo normalizado.
- **Faixa monetária.** `financial_entries.amount` é `NUMERIC(14,2)` com
  `CHECK (amount > 0)`, a única coluna monetária do schema. Foram testados `0,01`,
  `1.234,56`, `50.000,05` e `999.999.999.999,99`. Os quatro valores voltam **idênticos**
  pela leitura do papel de migração e pela do papel de aplicação.
- **Achado: o tipo da coluna, sozinho, não recusa três casas decimais.** Um `INSERT`
  direto com `1234.567` é **aceito e arredondado em silêncio** para `1234.57`:
  `NUMERIC(14,2)` arredonda, não rejeita.
  - A recusa ficou na camada de importação: o valor escalado por `10^escala` é comparado
    ao inteiro mais próximo. Recusa `1234.567`, `1234.565` e `100.001` e aceita os
    quatro valores de fronteira.
  - Negativo, zero e estouro de precisão o próprio PostgreSQL já recusa.
- **Separação de papéis.** Três papéis, nenhum superusuário:
  - **migração** é dono do banco, aplica o Alembic e é o único com `TRUNCATE`, `TRIGGER`
    e `REFERENCES`;
  - **aplicação** tem `SELECT`, `INSERT`, `UPDATE` e `DELETE`, sem DDL;
  - **backup** tem `SELECT`.

  A matriz foi conferida em `information_schema.table_privileges`.
- **Bloqueio de escrita como controle real.** Com o papel de aplicação ainda sem
  `INSERT`/`UPDATE`/`DELETE`, uma escrita de teste falhou com `permission denied`. Depois
  do `GRANT`, a mesma escrita foi aceita.
- **Achado: backup com papel mínimo.** `pg_dump` pelo papel de backup falhou na primeira
  tentativa (`failed to get data for sequence`). O papel precisa de `USAGE, SELECT` também
  nas **sequences**; `SELECT` nas tabelas não basta. Corrigido e revalidado, o papel
  continua sem privilégio de escrita.
- **Retorno ao SQLite antes de qualquer escrita nova no PostgreSQL** é trivial e sem
  perda, porque o PostgreSQL ainda é só uma cópia. Isso foi comprovado duas vezes.
- **As duas pilhas simultâneas na VM de homologação** (06/11): o PostgreSQL 18 recém-criado,
  sem dados, ocupou ~96 MiB de RAM e 56 MB de disco, sem pressão de memória. É o número do
  servidor **ocioso**; carga real exige medição própria.

### Pendente

- **Papéis de produção.** O padrão migração/aplicação/backup está validado. Falta
  instanciá-lo com nomes, credenciais e rotação de produção. Os papéis dos ensaios eram
  descartáveis e foram destruídos.
- **Destino de backup fora da VM.** Nenhum ensaio usou destino externo. A cópia para
  fora do host (a futura VM-Backup-Monitor ou equivalente) ainda não existe e precede
  qualquer corte com dado real. O piloto dessa cópia é tema da OPS-2 (ADR-015, ainda
  não integrado).
- **Reconciliação pós-corte.** Depois que o PostgreSQL recebe escrita nova, voltar ao
  SQLite sem reconciliar perde essa escrita. O mecanismo não foi construído: identificar
  as linhas novas, replicá-las respeitando FK e sequências e decidir o destino dos
  recursos exclusivos do PostgreSQL. É item de design da janela de corte real.
- **Volume e desempenho reais.** As bancadas tinham poucos registros, e os tempos
  medidos (centésimos de segundo) não dimensionam um corte com dado real.
- **Rotina de backup versionada.** A rotina diária da homologação existe e roda (ver
  [ops_backup_routine.md](../operations/ops_backup_routine.md)), mas o script e as
  unidades ainda vivem só na VM.

## Consequências positivas

- A base técnica para migrar foi testada ponta a ponta: compatibilidade de schema,
  recuperação por dump/restore e migração linha a linha com conversão de tipo explícita.
- A janela "antes de escrever no PostgreSQL" é reversível sem custo. Isso permite cortar
  em etapas (migrar, validar e só então liberar escrita) em vez de um corte único e
  irreversível.

## Consequências negativas

- Estender a decisão a dado real exige trabalho não coberto aqui: papéis de produção,
  reconciliação (se o corte não for instantâneo), volume real e destino externo de
  backup.
- O PostgreSQL acrescenta um processo e uma superfície de configuração (cluster,
  `pg_hba.conf`, papéis) que o SQLite não tem.

## Alternativas consideradas

- **Não migrar agora.** Manteria a D-03 como estava; a evidência já reunida ficaria só
  registrada.
- **Corte único por dump e carga.** Mais simples, mas exige parar as escritas durante toda
  a operação, o que impede validar antes de cortar.
- **Replicação contínua numa janela de transição.** Resolveria a reconciliação, mas exige
  infraestrutura (CDC ou escrita dupla) que não existe e não foi desenhada.

## Referências

- [`technical_decisions.md`](technical_decisions.md) D-03
- PR #5: <https://github.com/jlrcte-dev/cartorio-system/pull/5>
- CI pós-merge: <https://github.com/jlrcte-dev/cartorio-system/actions/runs/42277467291>
- [ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md): verificação
  operacional e prova de recuperação
- Evidências, plano de corte e roteiro operacional: dossiê privado do operador, fora do
  Git
