# Estado da infraestrutura: checkpoint de 12/11/2026

> **Data de referência:** checkpoint de infraestrutura com corte principal em 12/11/2026 e
> atualização complementar de 13/11/2026 referente à `CARTORIO-TESTRESTORE-2`. Nessa atualização
> (etapa R5), a janela está `TR2_WINDOW_BLOCKED`: **não foi autorizada nem executada**, o
> critério de aceite (emenda A1) está pendente de decisão do operador e o isolamento da VM 101
> **não está comprovado**.
>
> **Natureza:** registro do estado conhecido. Não é plano nem decisão. O plano está no
> [roadmap de infraestrutura](infrastructure_roadmap.md) (§8 traz as frentes) e a
> arquitetura-alvo em [`target_infrastructure.md`](target_infrastructure.md).
>
> **Sprint:** `DOC-INFRA-01`, exclusivamente documental. A sprint não acessou o Proxmox, as VMs
> nem o servidor da serventia.
>
> **Repositório público.** Este texto é um resumo sanitizado. Endereços, nomes de máquina e de
> conta, hashes de configuração, regras de filtragem, caminhos internos, capturas e logs ficam
> só nos relatórios privados, fora do Git. Quando um detalhe não pode ser versionado, o texto
> aponta a fonte privada em vez de reproduzi-lo.

## 0. Fontes e marcação

| Marca | Significado |
|---|---|
| **Git/CI** | Código e documentos versionados, e execução do GitHub Actions por SHA |
| **Relato** | Observação registrada, com data, num relatório privado de homologação |
| **Previsão** | Expectativa técnica ainda não comprovada |
| **Decisão pendente** | Depende do operador ou do fornecedor |

Fontes privadas, fora do Git:

- Relatórios da sprint `INFRA-VM102`: homologação técnica G5-A e encerramento G5-B (12/11/2026),
  registro de pendências, procedimento de operação segura e proposta de sprint do Engegraph.
- Relatório técnico de vistoria da serventia e de retomada do laboratório (11/11/2026). Foi a
  única versão localizada em 12/11/2026. O documento não traz marca de aprovação formal, e a
  aprovação fica a confirmar pelo operador.
- Dossiês das sprints `CARTORIO-TESTRESTORE-1` e `CARTORIO-TESTRESTORE-2`, incluindo o relatório
  de retomada de 12/11/2026, e o runbook privado de homologação da VM-CartorioSystem.

**Corte temporal:** o estado do host é o verificado por leitura no G5-A, em 12/11/2026. Nada
aqui afirma o estado posterior a essa leitura, exceto onde a data é indicada. A situação da
`CARTORIO-TESTRESTORE-2` considera o relatório da etapa R5, de 13/11/2026.

---

## 1. Resumo

| Frente | Situação (12/11/2026, exceto onde indicado) |
|---|---|
| Host Proxmox | Em operação para homologação e laboratório. Há reboot pendente, com troca de kernel, e a persistência das proteções depois dele não foi comprovada |
| VM 100: Cartório System | Homologação com dados sintéticos em PostgreSQL 18 e backup local diário. Na última leitura registrada (08/11), o verificador da `CARTORIO-OPS-1` não estava instalado. O código da OPS-2 e da OPS-3 está em `main`, sem implantação registrada |
| VM 101: TestRestore | Laboratório sintético de recuperação, homologado com ressalva (`CARTORIO-TESTRESTORE-1`). O isolamento de rede não está provado: a janela da `CARTORIO-TESTRESTORE-2` **não foi executada** e, na etapa R5 (13/11), foi considerada bloqueada por um critério de aceite pendente de decisão do operador |
| VM 102: laboratório Windows | **Concluída e homologada** (`INFRA-VM102`, G5-A e G5-B). Está desligada, sem Engegraph e sem dado real |
| Origem Engegraph | Inventário preliminar de 11/11 identificou o banco. Faltam o local e o tamanho dos bancos, a build efetiva e as confirmações do fornecedor |
| Backup e recuperação do Engegraph | A cópia do fornecedor existe como contingência. A recuperação consistente não foi comprovada |
| Computador candidato a backup | Inventário preliminar. **Não homologado** |
| Placa de rede adicional do host | Identificada pela embalagem. A detecção no host não foi confirmada |
| Investigação do Engegraph | **Não iniciada.** A instalação do Engegraph exige sprint e autorização próprias (§10) |

---

## 2. Host Proxmox

| Item | Estado | Fonte |
|---|---|---|
| Plataforma | Proxmox VE 9.2, nó único, em hardware dedicado | Relato (G5-A) |
| Papel | Ambiente de **homologação e laboratório**. Não hospeda a operação da serventia | Relato |
| CPU | 6 núcleos e 12 threads | Relato (inventário de 05/11 e G5-A) |
| Memória | 16 GB físicos, cerca de 15,4 GiB visíveis ao host. A placa tem só dois slots | Relato |
| Armazenamento das VMs | Thin pool de cerca de 141 GiB, com cerca de 104 GiB provisionados aos discos das VMs 100 e 102, sem overcommit. O armazenamento de imagens e ISOs tem cerca de 51 GiB livres. O inventário de hardware lista um SSD NVMe de 250 GB e um HD de 2 TB. As fontes desta sprint não descrevem o disco da VM 101 nem o uso do HD | Relato (G5-A e inventário de 05/11) |
| Rede física | Uma porta em uso, ligada à LAN da serventia, sem VLAN. A placa adicional de duas portas não foi confirmada no host (§8.2) | Relato |

### 2.1 Bridges e separação entre redes

| Bridge | Papel | Uplink físico | Endereço do host | Situação |
|---|---|---|---|---|
| `vmbr0` | LAN da serventia: gestão do host e VMs 100 e 101 | Sim | Sim | Sem segmentação (ver §1 do [roadmap de infraestrutura](infrastructure_roadmap.md)) |
| `vmbr1` | Rede interna da VM 101 (laboratório de recuperação) | Não | Sem IPv4 | Achado em tratamento (P10); isolamento não provado (§4) |
| `vmbr2` | Rede exclusiva da VM 102 (laboratório Windows) | Não | Nenhum, com IPv6 desligado | Isolada e testada (§5) |

- A operação da serventia (servidor do Engegraph e estações) não roda em nenhuma VM deste host.
- O host e as VMs 100 e 101 estão na LAN da serventia. As redes de laboratório (`vmbr1` e
  `vmbr2`) não têm uplink.
- A proteção da VM 102 é própria: filtro de camada 2 no host e trava de partida (§5). Ela não
  depende do firewall do Proxmox e vale só para a `vmbr2`.

### 2.2 Capacidade medida em 12/11

| Situação | Memória disponível no host |
|---|---|
| VMs 100 e 101 ligadas, VM 102 desligada | Cerca de 8,4 GiB |
| As três VMs ligadas | Cerca de 3,1 a 3,3 GiB (medido no G4-B) |

Recomendação dos relatórios da `INFRA-VM102`: iniciar a VM 102 só com pelo menos 5 GiB
disponíveis e evitar as VMs 101 e 102 ligadas juntas por longos períodos.

### 2.3 Reboot pendente

- Há um kernel mais novo instalado, que só entra em uso no próximo boot do host.
- As fontes desta sprint não registram reboot do host depois da criação da VM 102 e das suas
  proteções. A persistência delas está comprovada por configuração, log e ensaio isolado,
  **não por boot real** (Previsão).
- Antes do primeiro uso da VM 102 depois desse reboot, a revalidação é obrigatória (pendência
  P15). Os critérios estão no relatório privado do G5-A.
- Se a proteção não voltar, a trava impede a partida da VM 102. O efeito esperado é
  indisponibilidade, não exposição.
- O mesmo reboot é o item 4 do [checklist da janela](../operations/ops_window_checklist.md):
  a partida automática da VM 100 depois do boot do host, nunca observada.

---

## 3. VM 100: Cartório System (`VM-CartorioSystem`)

**Finalidade:** homologação do Cartório System com dados sintéticos. É o item 2 da Fase 1 do
roadmap de infraestrutura. Não recebe dado real da serventia: o corte para dado real não está
autorizado ([ADR-013](../decisions/ADR-013-troca-banco-ativo-sqlite-postgresql.md) e
[ADR-016](../decisions/ADR-016-politica-de-protecao-do-banco.md)).

| Item | Estado | Fonte |
|---|---|---|
| Sistema | Ubuntu Linux. A aplicação roda sob systemd, com Python isolado do Python do sistema | Relato (05 e 06/11) |
| Histórico | Fase A em SQLite homologada em 05 e 06/11. Compatibilidade com PostgreSQL integrada pelo PR #5. Troca do banco ativo em 07/11, com paridade conferida, backup restaurado e smoke | Git/CI e Relato |
| Banco ativo (decisão vigente) | **PostgreSQL 18** desde 07/11/2026, só para homologação. ADR-013 *Aceito*. A recuperação é restaurar o PostgreSQL do próprio backup, e o SQLite congelado fica como último recurso | Git e Relato |
| Backup local | Diário, com manifesto SHA-256 e retenção de 14 cópias. Dois disparos automáticos consecutivos foram observados em 08/11. A integridade do segundo par e a restauração de uma cópia automática estão pendentes. Contrato em [`ops_backup_routine.md`](../operations/ops_backup_routine.md) | Relato |
| Release ativa | Última leitura registrada em 08/11, anterior a `app/ops`. Não há registro de implantação posterior | Relato |
| Partida automática | Configurada. Não há observação registrada de partida depois do corte, nem por reboot do convidado nem por reboot do host (itens 2 e 4 do checklist) | Relato |
| Disco | 40 GiB no thin pool do host | Relato (G5-A) |

**Relação com as frentes OPS:**

| Frente | Git/CI | Implantação e aceite |
|---|---|---|
| `CARTORIO-OPS-1`: verificador, alerta local, gate PostgreSQL e prova de recuperação | Em `main` pelo PR #6 (`b22e1b6`), com CI verde | Não instalado. Itens 1 a 5 do [checklist](../operations/ops_window_checklist.md) |
| `CARTORIO-OPS-2`: cópia verificada e observador fora do host ([ADR-015](../decisions/ADR-015-copia-verificada-e-observador-fora-do-host.md)) | Em `main` pelo PR #8 (`6059df2`), com CI verde | Não implantado. Depende do PC dedicado da ADR-016, que ainda não existe como equipamento aceito (há um candidato, §7.3) |
| `CARTORIO-OPS-3`: endurecimento da cópia e da recuperação | Em `main` pelo PR #11 (merge `cb9fec9`, 11/11/2026). CI pós-merge `42949087241` verde | Não implantado. A repetição do ciclo do laboratório de recuperação (VM 101) no SHA novo tem plano privado e **não tem registro de execução** |

---

## 4. VM 101: TestRestore (`VM-TestRestore`)

**Finalidade:** laboratório de **homologação de procedimentos de recuperação** com dados
sintéticos, em Ubuntu Linux. Ele prova o código de continuidade e os passos de restauração.

**Não é infraestrutura de backup.** A VM 101 roda no mesmo host e cai junto com ele. As cópias
que protegem dados ficam fora do host, conforme a
[ADR-015](../decisions/ADR-015-copia-verificada-e-observador-fora-do-host.md) e a
[ADR-016](../decisions/ADR-016-politica-de-protecao-do-banco.md).

| Item | Estado | Fonte |
|---|---|---|
| `CARTORIO-TESTRESTORE-1` (09 e 10/11) | Ciclo completo com dados sintéticos e sem desvio: suíte, gate PostgreSQL, gate da cópia fora do host, ensaios de recuperação e cadeia da OPS-2. A homologação sintética tem uma **ressalva**: o estado do firewall do convidado em dois instantes foi inferido por critério fixado antes da execução, e aceitar essa inferência é decisão pendente do operador | Relato |
| Achados de contrato | Nove achados (S1 a S9). Cinco foram corrigidos pela OPS-3 (S1, S2, S3, S4 e S6). S5, S7, S8 e S9 aguardam decisão ou sprint própria | Relato e Git (PR #11) |
| `CARTORIO-TESTRESTORE-2` (isolamento de rede) | Plano pronto em 11/11. A retomada de 12/11 foi somente leitura. A etapa R5 (13/11), também somente leitura, concluiu que a janela está **bloqueada**: o critério de aceite pré-registrado reprova a verificação inicial por efeito de atualizações automáticas do sistema da VM 101, e a emenda depende de decisão do operador. A janela **não foi autorizada nem executada**, e nada foi alterado na rede | Relato (R5, 13/11) |
| Isolamento | **Não provado.** Há um achado em tratamento (P10, detalhe só no registro privado). Enquanto ele existir, o isolamento só poderá ser declarado com ressalva | Relato (`INFRA-VM102`; retomada de 12/11; R5) |
| Tratamento | P10 exige mudança própria, com autorização, janela e leitura do host antes e depois. Uma mudança mínima foi proposta e **não foi executada**. A homologação da OPS-3 na VM 101 espera a `CARTORIO-TESTRESTORE-2` liberar a VM | Relato |

A `INFRA-VM102` e esta sprint não alteraram a VM 101: a configuração foi conferida contra a
baseline no G5-A.

---

## 5. VM 102: laboratório Windows (`VM-Engegraph-Lab`)

Sprint `INFRA-VM102`, de 10 a 12/11/2026: **concluída e homologada**. A homologação G5-A foi
aprovada e o encerramento G5-B, autorizado pelo operador em 12/11/2026.

| Item | Estado |
|---|---|
| Sistema | Windows 10 Pro 22H2 x64 pt-BR |
| Firmware | UEFI com Secure Boot ativo |
| Drivers e agentes | Drivers VirtIO assinados (disco, serial, balão, firmware e rede). QEMU Guest Agent e BalloonService em execução automática |
| Recursos virtuais | 2 vCPU, 4 GiB de RAM com balão mínimo de 2 GiB e disco de 64 GiB (cerca de 10 GiB em uso) |
| Rede | Uma única placa virtual, na `vmbr2` |
| Partida | Desligada e sem início automático |
| Conteúdo | Sem Engegraph, sem dado real e sem software de terceiros além dos drivers e agentes |
| Ativação | Windows **não ativado**, em modo de notificação. O licenciamento regular está pendente (P2) |
| Desligamento | Normal, pelo Guest Agent, testado sem ação forçada |

**Proteção em camadas:**

1. bridge sem uplink;
2. host sem endereço na bridge, com IPv6 desligado nela e sem encaminhamento;
3. filtro **nftables** de camada 2 no host, que descarta todo quadro entre a bridge e o host nos
   dois sentidos;
4. trava de partida **fail-closed**: a VM não inicia se a rede, o filtro ou a configuração dela
   divergirem do aprovado;
5. VM com uma única placa e sem partida automática.

**Testes reais, aprovados:**

- Isolamento (12/11): a partir do Windows, não houve conexão com o host, o gateway, a internet
  ou o DNS, em IPv4 e IPv6, nem forçando uma rota temporária para o host.
- Isolamento (12/11): no host, 100% dos quadros da VM foram descartados antes da pilha de rede.
  O host enviou zero quadros à VM, e a interface física registrou zero quadros do laboratório.
- Trava (11/11): passou no teste negativo (a partida foi abortada quando a proteção faltava) e
  na integração com uma partida real.

**Limites que continuam valendo:**

- A persistência do isolamento **depois de um reboot do host não foi comprovada** (P15, §2.3).
- A trava verifica **só na partida**. Durante o uso, a proteção depende das regras operacionais
  e da conferência antes e depois de cada uso.
- O Windows está sem atualizações de segurança e sem internet, e o relógio não sincroniza (P18).
- Não há snapshot de base (P19). Voltar ao estado limpo exige reinstalar.
- **A instalação do Engegraph exige autorização independente**, em nova sprint (§10).
- O baseline técnico detalhado (configuração, hashes e procedimento de partida e desligamento)
  fica só na documentação privada.

**Decisões do operador (12/11/2026):**

- a VM fica desligada fora de uso;
- nenhum dado real entra nela;
- o Windows 10 serve só como laboratório legado;
- o isolamento é verificado antes de cada partida;
- a trava e o filtro só mudam com revisão específica;
- backups, snapshots e recuperação ficam em frentes independentes;
- Windows 11 ou Windows Server serão avaliados no futuro;
- o Engegraph será investigado em nova sprint.

---

## 6. Origem Engegraph (servidor da serventia)

Inventário **preliminar** de 11/11/2026: consultas interativas de metadados, somente leitura, no
console do servidor, mais as confirmações do operador sobre o uso das unidades. Não há aqui dado
de base, conteúdo de documento nem dado pessoal.

| Item | Estado |
|---|---|
| Sistema operacional | Windows 10 Pro, 64 bits |
| Banco do Engegraph | SQL Server 2022 **Express**, x64, instância local |
| Topologia | Aplicação Engegraph e motor SQL **no mesmo computador**, confirmado pelo operador |
| Organização dos dados | Volumes lógicos distintos para sistema, aplicação, GED, arquivos gerais e cópias |

**Pendente de confirmação:**

- o local efetivo e o tamanho dos bancos: o volume da aplicação não confirma onde ficam os
  arquivos de dados;
- a build carregada pelo serviço SQL: só a versão do executável em disco foi lida;
- com o fornecedor: suporte, dependências, Windows homologado e licenciamento da aplicação;
- a situação de atualizações da origem (detalhe só no relatório privado);
- escopo, rotina e restauração das cópias locais existentes, inclusive as da ferramenta de backup
  levantada em maio/2026 ([roadmap de infraestrutura](infrastructure_roadmap.md) §1).

O tamanho real a copiar e restaurar (base, GED e configuração, no formato de backup) não foi
medido. Os volumes exatos ficam no relatório privado.

**Limites públicos da edição Express**, segundo a documentação da Microsoft: por instância, usa
no máximo um soquete ou quatro núcleos, o que for menor, e cada banco relacional tem até 10 GB.
Esses limites contam para dimensionar o laboratório. O tamanho real das bases não foi medido.

### 6.1 Conclusão arquitetural (para avaliação, não decisão)

A primeira avaliação do laboratório Engegraph deve verificar se é possível reproduzir aplicação e
motor SQL **numa única VM Windows isolada**, com dados sintéticos, espelhando a topologia da
origem. A separação entre `VM-Engegraph-App` e `VM-Engegraph-DB` continua como alvo
([`target_infrastructure.md`](target_infrastructure.md)) e depende do fornecedor.

### 6.2 Capacidade: nada aprovado

- Não está comprovado que a VM 102, com os recursos atuais, reproduza a operação produtiva.
- O dimensionamento preliminar do relatório de 11/11 (4 vCPU, 12 GiB de RAM e discos de 128 e
  64 GiB, 192 GiB no total) **não está aprovado**.
- Pela medição de 12/11, ele **não cabe no nó sem mudança**. Com as VMs 100 e 101 ligadas sobram
  cerca de 8,4 GiB de memória, menos que 12 GiB. Isso basta para a conclusão. No disco, o thin
  pool tem cerca de 37 GiB sem provisionar, menos que 192 GiB; o restante do armazenamento do
  host, inclusive o HD de 2 TB, não está descrito nas fontes. Esta é uma conta sobre a medição,
  não um teste.
- Qualquer redimensionamento depende da análise de compatibilidade (E1) e de uma decisão sobre
  capacidade: mais memória, outro armazenamento ou desligar outras VMs.

---

## 7. Backup e recuperação

Esta frente é **separada** do laboratório Engegraph e da VM 102.

### 7.1 Cartório System (VM 100)

A política está na [ADR-016](../decisions/ADR-016-politica-de-protecao-do-banco.md) (*Aceito*), e
o estado, no §3. Nada da ADR foi implantado: falta o PC, o transporte, a agenda e a primeira
restauração a partir do PC.

### 7.2 Engegraph: Cofre Digital

- O fornecedor de cópia (Cofre Digital) copia dados do Engegraph, o GED e a base de dados, por
  procedimento dele.
- Ele não executa a recuperação completa sozinho. Numa recuperação, a serventia pede a cópia ao
  Cofre Digital e aciona a Engegraph, que restaura manualmente.
- A restauração depende de dois fornecedores. Por isso a cópia fica como **contingência**.
- A recuperação consistente, no mesmo ponto, de base SQL, GED e configuração **não foi
  comprovada**.
- A fonte de referência para o laboratório será escolhida pelo procedimento e pela evidência de
  restauração. As cópias locais existentes precisam de origem, escopo e teste antes de entrar
  nessa escolha.
- Nenhum mecanismo de backup recorrente do Engegraph foi aprovado por esta frente (ver BKP-2).

### 7.3 Computador candidato a backup

| Item | Estado preliminar |
|---|---|
| Equipamento | Desktop legado, com placa e firmware de cerca de 2010 |
| CPU e RAM | 2 núcleos (arquitetura de 64 bits a confirmar no boot) e cerca de 6 GiB detectados na partida (leitura de detecção, não teste) |
| Discos | HD interno de 500 GB, para o sistema, e HD externo de 1 TB |
| Partida | A partida pede intervenção manual: perde data e parâmetros (CMOS). A partida autônoma não está comprovada |
| Memória | O firmware registrou falha de treinamento da memória num boot anterior. A estabilidade não foi testada |
| Situação | **Não homologado** para operação recorrente |

- A ocupação conjunta da aplicação e do GED do Engegraph já excede o HD interno. Duas cópias
  integrais excederiam o HD externo.
- Para um primeiro piloto, a avaliação é como **destino leve de cópias**. Se o Proxmox Backup
  Server entrar na avaliação, o equipamento chegaria no máximo ao mínimo de avaliação publicado
  (2 núcleos de 64 bits, com a arquitetura ainda a confirmar), abaixo da recomendação para
  produção.
- **Critério inicial de aceite**, proposto no relatório privado:
  - duas partidas a frio sem intervenção, com data e parâmetros preservados;
  - duas passagens completas de teste de memória sem erro;
  - SMART dos dois discos;
  - rede e retorno de energia;
  - recuperação de um conjunto sintético com manifesto, restaurado em ambiente isolado.
- **Divergência de planejamento com a ADR-016 (BKP-2, pendente de decisão).** A ADR-016
  continua *Aceita* e vigente, e esta sprint não a modifica. Ela define como destino e executor
  das cópias do Cartório System "o PC dedicado da serventia, exclusivo do domínio Cartório", com
  executor POSIX, e aceitou a regra de que "o PC guarda só cópias do Cartório System e não
  recebe cópia de nenhum outro sistema". O relatório de 11/11 trata este computador como
  candidato a destino de cópias também do Engegraph. As fontes não dizem se ele é o PC dedicado
  da ADR-016. Estado:
  - o computador candidato **não está homologado**;
  - a sua utilização para backups do Engegraph **não está autorizada**;
  - qualquer mudança de escopo exigirá nova decisão arquitetural;
  - **nenhum mecanismo de backup recorrente do Engegraph foi aprovado** nesta frente.

---

## 8. Hardware e rede

### 8.1 Host

Ver o §2. A memória (16 GB, em dois slots) limita o crescimento do laboratório.

### 8.2 Placa de rede adicional

- Placa Vinik PRV2P1000E, PCIe x1, com duas portas RJ45 Gigabit. O fabricante declara chipset
  Intel 82571EB, atendido no Linux pelo driver `e1000e`, que faz parte do kernel.
- **Não confirmados:** detecção PCI no host, driver efetivamente carregado e associação entre
  porta física e interface.
- **Não é dependência da VM 102**, que não usa uplink.
- Só entra num plano se um laboratório precisar falar com outro equipamento numa rede física
  segregada. A disponibilidade da placa e o isolamento do laboratório são verificações distintas.

---

## 9. Pendências e riscos

Os IDs `Pnn` são do registro privado da `INFRA-VM102`. Os demais IDs são deste checkpoint. O
risco aparece só quando a fonte o classifica. Nenhuma pendência tem data-limite.

| ID | Pendência | Frente | Risco (fonte) | Fecha quando | Status |
|---|---|---|---|---|---|
| P15 | Revalidar a proteção da `vmbr2` depois do reboot do host, antes do primeiro uso da VM 102 | Host e VM 102 | Médio (fail-closed) | Revalidação somente leitura aprovada depois do primeiro reboot autorizado | Aberta |
| CHK-4 | Partida automática da VM 100 depois do reboot do host | VM 100 | — | Item 4 do [checklist](../operations/ops_window_checklist.md) | Pendente |
| CHK-1/2/3/5 | Integridade e restauração de cópia automática, partida após reboot do convidado, recuperação a partir do PC e instalação do verificador | VM 100 | — | Itens 1, 2, 3 e 5 do checklist | Pendente ou parcial |
| P10 | Achado de rede na bridge interna da VM 101 (detalhe só no registro privado) | VM 101 | Médio | Mudança autorizada, com leitura do host antes e depois | Aberta. Mudança mínima proposta, não executada |
| TR2 | Isolamento de rede da VM 101 (`CARTORIO-TESTRESTORE-2`) | VM 101 | — | Decisão do operador sobre o critério de aceite; depois, janela executada com isolamento provado (com ressalva enquanto a P10 existir) | Janela bloqueada na R5 (13/11). Não autorizada nem executada |
| TR1-R | Aceitar ou não a inferência do estado do firewall na `CARTORIO-TESTRESTORE-1` | VM 101 | — | Decisão do operador | Aberta |
| OPS3-H | Repetir o ciclo do laboratório de recuperação no SHA de `main` com a OPS-3 | VM 101 | — | Ciclo sem desvio, depois da `CARTORIO-TESTRESTORE-2` | Aberta |
| TR1-S | Achados S5, S7, S8 e S9 | Código de continuidade | — | Decisão ou sprint própria | Aberta |
| P2 | Licenciamento e ativação regular do Windows da VM 102 | VM 102 | Baixo/médio | Licença regular e método compatível com o isolamento | Aberta |
| P11 | Decidir sobre o acesso de diagnóstico ao host (detalhe só no registro privado) | Host | Baixo/médio | Decisão do operador | Aberta |
| P18 | Relógio do Windows sem rede | VM 102 | Baixo | Método definido | Aberta |
| P19 | Snapshot de base da VM 102 | Backup (frente independente) | Médio | Autorização específica | Aberta |
| P20 | Procedimento de entrada de arquivos e mídias no laboratório | Laboratório | Médio | Procedimento aprovado, antes de qualquer carga | Aberta |
| P21 | Avaliar Windows 11 ou Windows Server | Laboratório | Baixo | Requisitos do fornecedor | Aberta |
| P22 | Investigar o Engegraph | `ENGEGRAPH-LAB` | Baixo | Sprint nova (§10) | Aberta, sem início |
| P23 | Endurecimento opcional do Windows (descoberta de rede, nome da máquina) | VM 102 | Baixo | Decisão do operador | Aberta |
| P24 | Retenção das evidências guardadas no host | Host | Baixo | Decisão do operador | Aberta |
| ENG-1 | Local efetivo e tamanho dos bancos da origem | Origem | — | Confirmação do operador ou do fornecedor | Aberta |
| ENG-2 | Build do SQL carregada pelo serviço | Origem | — | Leitura autorizada | Aberta |
| ENG-3 | Suporte, dependências, Windows homologado e licenciamento da aplicação | Origem | — | Resposta do fornecedor | Aberta |
| ENG-4 | Escopo, rotina e restauração das cópias locais existentes | Origem e backup | — | Identificação e teste | Aberta |
| ENG-5 | Situação de atualizações da origem | Origem | — | Registro com evidência (privado) | Aberta |
| BKP-1 | Recuperação consistente de base SQL, GED e configuração do Engegraph | Backup | — | Procedimento definido com o fornecedor e ensaio em ambiente isolado | Aberta |
| BKP-2 | Divergência de planejamento: o relatório de 11/11 trata o computador candidato como destino também do Engegraph, e a ADR-016 (vigente) o restringe ao Cartório System. Uso para o Engegraph **não autorizado** | Backup | — | Nova decisão arquitetural (§7.3) | Aberta, pendente de decisão |
| HW-1 | Computador candidato: CMOS e partida autônoma | Backup | — | Duas partidas a frio sem intervenção | Aberta |
| HW-2 | Computador candidato: estabilidade da memória | Backup | — | Teste de memória sem erro | Aberta |
| HW-3 | Computador candidato: discos, rede, energia e recuperação sintética | Backup | — | Critérios do §7.3 | Aberta |
| HW-4 | Placa de rede adicional: detecção e associação de portas | Host | — | Leitura no host, em janela autorizada | Aberta |
| CAP-1 | Capacidade do nó para o laboratório Engegraph | Host e laboratório | — | Decisão na E1 (§6.2) | Aberta |

---

## 10. Pré-condições para investigar o Engegraph

Valem para toda a frente `ENGEGRAPH-LAB`, proposta no
[roadmap de infraestrutura](infrastructure_roadmap.md) §8. **Nenhuma etapa dela começou.**

Os itens vêm das decisões do operador de 12/11 e das recomendações dos relatórios privados. O
item marcado *(proposta)* é deste checkpoint e depende de confirmação do operador.

1. **Sprint e autorização próprias.** Cada etapa, de E0 a E4, depende de autorização própria.
   Concluir uma etapa não autoriza a seguinte.
2. **A E0 é só documental.** Não toca o Proxmox, a VM 102 nem o servidor da serventia. Ela
   produz a matriz de requisitos, com as respostas do fornecedor e do operador sobre:
   - versão do Engegraph e Windows homologado;
   - arquitetura (32 ou 64 bits) e runtimes;
   - banco: versão do SQL suportada, tamanho e procedimento de ponto consistente;
   - licenciamento: chave, dongle USB, servidor de licença ou ativação online;
   - hardware e periféricos;
   - privilégios e serviços em segundo plano;
   - dados de teste;
   - horário e sincronização;
   - portas e protocolos.
3. **Servidor de produção** *(proposta)*. Nenhuma coleta nova sem autorização expressa. Quando
   houver, coletar só metadados, pelo operador, sem dado de base, documento ou dado pessoal.
4. **Dados.** Só sintéticos, ou anonimizados com aprovação. Nenhum dado real da serventia.
5. **Antes de cada uso da VM 102:**
   - revalidação P15, se o host foi reiniciado;
   - verificação do isolamento antes da partida;
   - pelo menos 5 GiB de memória disponível no host (recomendação).
6. **Licenciamento e isolamento.** Exigência de rede, internet ou dongle USB conflita com o
   isolamento atual. Quem decide é a E1. Um desenho novo exige nova análise de risco e nova
   homologação.
7. **Entrada de mídias.** Nenhum instalador entra sem procedimento aprovado, com origem e hash
   conferidos (P20).
8. **Snapshot de base.** É recomendado antes de software de terceiros (P19), em frente
   independente.
9. **Capacidade.** Nenhum redimensionamento sem a revisão do §6.2.
10. **Separação de frentes.** Backup e recuperação da origem ficam fora do laboratório.
11. **Trava e filtro.** As proteções da VM 102 não mudam sem revisão específica, em etapa própria.

---

## 11. O que esta sprint não fez

- Não acessou o Proxmox, as VMs nem o servidor de produção.
- Não alterou código, migrations nem CI, e não fez deploy.
- Não alterou, moveu nem copiou para o repositório os relatórios privados.
- Não decidiu nada: as decisões citadas são do operador e têm data. As pendências continuam
  abertas.

## 12. Histórico deste documento

| Data | Mudança |
|---|---|
| 2026-11-12 | Criação: checkpoint `DOC-INFRA-01` |
