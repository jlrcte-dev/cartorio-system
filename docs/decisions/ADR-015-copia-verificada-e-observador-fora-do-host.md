# ADR-015 — Cópia verificada e observador fora do host (piloto)

- **Status:** Proposto — piloto em bancada com dados sintéticos; sem implantação, sem
  transporte de rede e sem canal de alerta. O aceite depende do inventário e do teste do
  equipamento de destino e de uma janela própria.
- **Data:** 2026-11-08
- **Sprint:** `CARTORIO-OPS-2` (continuação da Fase 1 do roadmap de infraestrutura)
- **Código:** `app/ops/offsite.py`, `app/ops/observer.py`
- **Operação:** [`docs/operations/ops_offsite_pilot.md`](../operations/ops_offsite_pilot.md)

---

## Contexto

A [ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md) deixou dois limites
declarados:

1. **A cópia de backup só existe dentro da VM.** A rotina diária publica `pg_dump` +
   manifesto com SHA-256 num diretório local. Perder a VM, ou o host Proxmox, leva a cópia
   junto.
2. **O alerta é local.** O verificador e o `OnFailure=` vivem na VM: se a VM ou o host
   caem, nada alerta.

O PC físico dedicado da serventia é o primeiro candidato a destino da cópia e a executor
independente do Proxmox. Uma VM no mesmo Proxmox não serve para isso, porque compartilha a
disponibilidade do host. Uma cópia no mesmo local físico cobre a perda do host, não a da
serventia (incêndio, furto, inundação), que fica para planejamento próprio.

## Decisão

1. **Importação verificada** (`python -m app.ops.offsite`). A origem é só lida, e o
   contrato é o da rotina que a [ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md)
   já avalia (`backup-<carimbo>.dump` + `.json`). A publicação mais recente é avaliada por
   `evaluate_publication`:
   - manifesto regular e completo;
   - referência confinada ao diretório, sem link;
   - carimbo coerente;
   - ponto de recuperação legível e não futuro;
   - tamanho e SHA-256;
   - banco esperado informado **à parte** (`--expected-database`), nunca tirado do
     manifesto.

   Dump sem manifesto é publicação parcial e nunca é importado.
2. **Publicação por geração.** O par vai para `<destino>/geracoes/<carimbo>/`:
   - É copiado para um diretório de preparo novo (`<destino>/.preparo/`, no mesmo sistema
     de arquivos), com arquivos novos `0600` e `fsync`.
   - É conferido de novo ali, pela mesma função, e promovido por `rename` do diretório
     inteiro, de modo que quem lê vê a geração completa ou não a vê.
   - A mesma cópia repetida é idempotente.
   - O mesmo carimbo com outro conteúdo, ou uma geração inválida, é colisão visível e fica
     intocada, também quando duas execuções se sobrepõem.
   - Falha ou interrupção removem só o preparo da própria execução; nenhuma geração
     publicada muda.
   - Diretórios novos nascem `0700`. Destino existente é usado como está, se for diretório
     de verdade, do mesmo dono e sem escrita de grupo ou outros; senão é recusado sem ser
     tocado.
   - Destino dentro da origem (ou o contrário) é recusado.
   - Como o modo cópia do ensaio, só roda onde o isolamento é comprovável por modo POSIX.
3. **Observador** (`python -m app.ops.observer`). Consumidor separado da origem, que nunca
   acessa banco. Entrada: o último `cartorio_system.ops.check` 1.0 e as gerações da cópia.
   Três avaliações separadas:
   - `application_signal`: sinal ausente, inválido, vencido ou do futuro é falha. É o
     batimento que dispara mesmo sem `OnFailure=` na VM.
   - `last_check`: o que o último relatório válido disse, mesmo vencido.
   - `offsite_copy`: integridade e idade da cópia pelo ponto de recuperação do manifesto.

   A última cópia válida sai sempre à parte, como evidência independente. A saída
   `cartorio_system.ops.offsite_observation` 1.0 tem só estados e motivos estáveis: do
   relatório só passam nome de checagem, estado e motivo do vocabulário do contrato
   `cartorio_system.ops.check` 1.0, e o resto — mesmo no formato de um código — vira
   `unrecognized`; caminhos e nome de banco não saem. Limiares configuráveis, positivos e
   finitos, com valores de laboratório.
4. **Fora deste piloto:** transporte de rede entre VM e destino, agenda definitiva, envio
   de alertas, retenção com exclusão, troca da rotina de backup, imagens de VM e Engegraph.

### Adendo — endurecimento `CARTORIO-OPS-3` (2026-11-10)

Achados de um ensaio de laboratório com dados sintéticos. A decisão acima continua valendo;
o que muda é como ela é garantida:

- **Caminho do destino.** Link em qualquer componente do caminho — não só na raiz e em
  `geracoes/` — é recusado, e `..` também. No POSIX, a importação trabalha sobre os
  diretórios já abertos (`openat`, `mkdirat`, `renameat`), e não pelo caminho: um
  componente trocado por link no meio da execução não redireciona a escrita. O leitor e o
  observador também não atravessam link em nenhum componente.
- **Recusa × falha** pelo `errno`: permissão, sistema só de leitura e nome longo demais são
  recusa (2); os demais erros do sistema de arquivos são falha (1).
- **Preparo de execução interrompida.** "Falha ou interrupção removem só o preparo da
  própria execução" segue valendo para o caminho automático. Além disso, cada execução
  trava o próprio preparo e grava nele um marcador; toda importação relata as sobras de
  `.preparo/`, e só remove, quando pedido explicitamente (`--remove-orphan-staging`), a que
  prova ser órfã: marcador coerente, escrito nesta máquina neste boot, e trava livre. A
  trava só vale dentro do mesmo kernel; por isso a máquina e o boot entram na prova. Nome e
  idade nunca bastam.
- O relatório `cartorio_system.ops.offsite_import` passa a 1.1 (campo
  `staging.leftovers`). Detalhes e comparação 1.0 → 1.1 no
  [guia do piloto](../operations/ops_offsite_pilot.md) §2.1, §2.2 e §4.

## Consequências positivas

- A recuperação deixa de depender da VM estar de pé: o destino guarda pares verificados, e
  o modo cópia do ensaio restaura a partir deles (`--from-manifest`).
- A queda da VM ou do host passa a ser detectável de fora, pelo sinal que para de chegar.
- O formato de evidência é o mesmo da ADR-014: idade pelo manifesto, integridade pelo
  digest, banco esperado conferido.

## Consequências negativas

- Mais um equipamento a manter, com disco, energia, conta e criptografia próprios.
- O destino precisa de executor Linux para importar e restaurar. Se o PC for Windows, isso
  é planejamento à parte.
- A cópia no mesmo local físico não cobre a perda da serventia.
- Quem observa o observador continua em aberto: a queda do próprio PC precisa de outro
  sinal.

## Alternativas consideradas

- **`rsync`/`robocopy` do diretório de backup.** Copia sem conferir digest, banco e
  completude, e pode expor publicação parcial ao leitor.
- **VM de monitoramento no mesmo Proxmox** (`VM-Backup-Monitor` do roadmap). Cai junto com
  o host, que é justamente o cenário a cobrir.
- **Ferramenta de backup dedicada** (restic, borg). Traz criptografia e retenção, mas é
  dependência nova e outro formato de evidência; fica para a etapa de implantação.
- **Monitor externo pronto** (Uptime Kuma, Prometheus). Desproporcional para o piloto e
  sem a semântica de cópia válida; pode consumir o mesmo JSON depois.

## Referências

- [ADR-014](ADR-014-verificacao-operacional-e-prova-de-recuperacao.md) e o
  [checklist da janela da OPS-1](../operations/ops_window_checklist.md) (item 3: recuperação
  pelo PC dedicado)
- [`docs/operations/ops_offsite_pilot.md`](../operations/ops_offsite_pilot.md)
- [`docs/infrastructure/infrastructure_roadmap.md`](../infrastructure/infrastructure_roadmap.md) §3 e §6
