# Roadmap de Infraestrutura — Cartório Costa Teixeira

> Documento de planejamento técnico. Nenhuma configuração descrita aqui está
> implementada salvo indicação explícita.

Última atualização: 2026-05-04 · atualização parcial em 2026-11-07 (§3.4, §3.5 e §6,
sprint `CARTORIO-OPS-1`), em 2026-11-08 (§3.4 e §6, fechamento da `CARTORIO-OPS-1`) e em
2026-11-12 (§1, §6 e §8, checkpoint `DOC-INFRA-01`)

> **Estado consolidado:** o estado atual do host de homologação, das VMs 100, 101 e 102, da
> origem Engegraph, do backup e do hardware está em
> [`infrastructure_state.md`](infrastructure_state.md) (checkpoint de 12/11/2026). Este
> documento continua sendo o plano. As frentes abertas estão no §8.

---

## 1. Situação atual

> Levantamento de maio/2026 da operação da serventia (servidor físico Windows), mantido como
> base histórica. As linhas marcadas com *(11/11/2026)* foram corrigidas pelo inventário
> preliminar da origem, cujo resumo está no §6 de
> [`infrastructure_state.md`](infrastructure_state.md). As demais linhas não foram
> reverificadas; em particular, a linha "Disco de backup" pede reavaliação com os dados do
> inventário de 11/11 (no relatório privado).

| Componente | Estado | Risco |
|-----------|--------|-------|
| Servidor físico Windows | Em operação | Host único — ponto único de falha |
| Engegraph (ERP) | Operacional | Sem contingência documentada |
| Banco Engegraph | SQL Server 2022 Express, no mesmo computador da aplicação *(11/11/2026)*; local e tamanho dos bancos a confirmar | Backup sem dump confirmado; recuperação consistente não comprovada |
| Backup (Cobian Gravity) | Ativo, cópia de arquivos | Sem dump transacional; sem off-site |
| Cópia do fornecedor (Cofre Digital) *(11/11/2026)* | Fornece cópia mediante solicitação, segundo o operador; a restauração é manual, feita pela Engegraph | Contingência dependente de dois fornecedores; recuperação conjunta de base, GED e configuração não comprovada |
| Disco de dados | Espaço crítico | Risco de esgotamento |
| Disco de backup | Estado crítico | Risco de esgotamento |
| Rede | Sem segmentação | Wi-Fi clientes pode acessar rede admin |
| VPN | Inexistente | Acesso remoto não protegido |
| Nobreaks | Existem | Autonomia baixa; sem gerador |
| Firewall | Estado desconhecido | Possivelmente básico/inexistente |
| Antivírus/EDR | Estado desconhecido | Risco de infecção |
| MFA | Inexistente | Credenciais não protegidas por segundo fator |
| Permissões NTFS | Inadequadas | Documentos sigilosos acessíveis amplamente |

---

## 2. Arquitetura-alvo

A arquitetura-alvo evolui o servidor atual para um ambiente virtualizado com VMs
separadas por função. A virtualização é um **meio técnico** — não uma solução de
conformidade por si mesma. Ela viabiliza isolamento, testes, recuperação e
governança.

### 2.1 Host de virtualização

**Opção A — Servidor atual reestruturado**
- Instalar hipervisor no servidor físico atual
- Migrar serviços para VMs
- Risco: hardware existente pode não ter recursos suficientes (RAM, CPU, storage)
- Pré-requisito: inventário de hardware + avaliação de capacidade

**Opção B — Hardware dedicado novo**
- Adquirir servidor com especificação adequada para Classe 3
- Servidor atual pode virar laboratório/standby
- Maior investimento inicial; menor risco de capacidade

**Hipervisores candidatos**
- **Hyper-V** (nativo no Windows Server) — integração nativa com ambiente Microsoft
- **VMware ESXi** — maturidade, amplo suporte
- **Proxmox VE** — open source, sem custo de licença do hipervisor
- Decisão depende de: licenciamento, expertise interna/externa, suporte disponível

### 2.2 Mapa de VMs sugeridas

```
HOST DE VIRTUALIZAÇÃO
│
├── VM-FileServer          [Alta prioridade]
│   Arquivos compartilhados, NTFS por grupo, auditoria de objetos
│
├── VM-CartorioSystem      [Alta prioridade]
│   FastAPI app + PostgreSQL (Cartório System)
│   Logs de domínio, backup incremental a cada 4h
│
├── VM-Backup-Monitor      [Alta prioridade]
│   Agente de backup, scheduler, logs centralizados, alertas
│   Destinos: local, off-site (nuvem/NAS externo)
│
├── VM-Engegraph-App       [Média — depende do fornecedor]
│   Aplicação Engegraph
│   Confirmar suporte a virtualização com o fornecedor
│
├── VM-Engegraph-DB        [Média — depende do fornecedor]
│   SQL Server com banco do Engegraph
│   Backup via SQL Server Agent (BACKUP DATABASE + BACKUP LOG)
│   Separar App/DB melhora backup e isolamento
│
├── VM-DC                  [Baixa — avaliação futura]
│   Active Directory / gestão de identidade
│   Só faz sentido se houver ≥5 colaboradores com domínio
│
└── VM-TestRestore         [Alta — essencial para evidências]
    Laboratório isolado para testes de restauração
    Homologação de procedimentos, simulação de desastre
    Nunca em produção
```

### 2.3 Segmentação de rede

```
REDE FÍSICA
│
├── VLAN 10 — Servidores
│   Host de virtualização, VMs de produção
│   Acesso restrito: apenas administradores via VPN
│
├── VLAN 20 — Administrativa
│   Estações dos colaboradores administrativos
│   Acesso ao FileServer, Engegraph, sistemas internos
│
├── VLAN 30 — Colaboradores (se separação fizer sentido)
│   Estações de colaboradores com acesso mais restrito
│
├── VLAN 40 — Visitantes/Clientes   [PRIORIDADE EMERGENCIAL]
│   Wi-Fi de clientes
│   Sem acesso a qualquer recurso interno
│   Apenas saída para internet
│
└── VLAN 50 — Impressoras/Scanners  [Pode ser posterior]
    Dispositivos de digitalização e impressão
    Acesso apenas ao FileServer (pasta de digitalização)
```

**Hardware necessário para VLANs:**
- Switch gerenciável (managed) com suporte a 802.1Q
- Access point com suporte a múltiplos SSIDs em VLANs distintas
- Firewall/roteador que entenda VLANs

---

## 3. Estratégia de backup

### 3.1 Metas Classe 3

| Métrica | Meta | Observação |
|---------|------|-----------|
| RPO | ≤ 4 horas | Backup incremental frequente |
| RTO | ≤ 8 horas | Restauração testada e documentada |

### 3.2 Política por sistema

| Sistema | Tipo | Frequência | Retenção | Destino |
|---------|------|-----------|---------|---------|
| Engegraph (banco) | Dump SQL completo | Diário (pós-expediente) | 30 dias local + 90 dias off-site | Local + off-site |
| Engegraph (banco) | Backup de log transacional | A cada 4h (se SQL Server) | 7 dias | Local |
| FileServer | Incremental | A cada 4h | 7 dias incrementais | Local |
| FileServer | Full | Semanal (domingo) | 4 semanas | Local + off-site |
| CartorioSystem (PostgreSQL) | Dump pg_dump | A cada 4h | 7 dias | Local |
| CartorioSystem (PostgreSQL) | Full | Diário | 30 dias | Local + off-site |
| VMs (config) | Backup de VM | Semanal | 4 versões | Local |
| Host de virtualização | Backup de config | Após toda mudança | Permanente | Off-site |

### 3.3 Destinos de backup

**Local (on-site):**
- Volume dedicado no servidor (separado do volume de dados)
- Ou NAS local dedicado ao backup

**Off-site:**
- Opção 1: Nuvem (Azure Backup, AWS S3/Glacier, Backblaze B2)
- Opção 2: NAS em localização física diferente (casa do gestor, outro imóvel)
- Opção 3: Fita (menos prático, mas aceito como evidência)

**Critérios de escolha do off-site:**
- Custo mensal compatível com o volume de dados
- Suporte a retenção de 90 dias ou mais
- Criptografia dos dados em trânsito e em repouso
- Verificação de integridade (checksums)

### 3.4 Monitoramento

- Alerta automático em caso de falha de backup (e-mail ou SMS)
- Log de cada execução: início, fim, tamanho, status
- Dashboard ou relatório semanal revisado pelo gestor
- Registro de cada alerta recebido e ação tomada

> **Estado em 2026-11-08 (VM-CartorioSystem, só o Cartório System):** está em `main`
> (PR #6, merge `b22e1b6`, CI do PR e pós-merge verdes) um verificador somente leitura que
> separa processo/API, PostgreSQL, revisão Alembic e backup — idade pelo ponto de
> recuperação, integridade pelo digest do manifesto, última tentativa e timer —, com saída
> JSON versionada e alerta num spool local por `OnFailure=`. Provado com dados sintéticos
> na bancada e no CI; ainda não instalado na VM. Canal definitivo (e-mail, mensageria),
> observador externo (VM ou host fora do ar) e instalação na VM continuam pendentes. Ver
> [`../operations/ops_verifier_runbook.md`](../operations/ops_verifier_runbook.md).

### 3.5 Teste de restauração

**Frequência:** mínimo trimestral (idealmente mensal)
**Ambiente:** VM-TestRestore (isolada de produção)
**O que restaurar:** ao menos um sistema crítico por teste (Engegraph DB ou FileServer)
**Documentação obrigatória:**
- Data e hora do início e fim
- Versão de backup restaurada (data do backup)
- Procedimento utilizado (passo a passo)
- Resultado: sucesso/parcial/falha
- Tempo total de restauração (para validar RTO)
- Hash dos arquivos restaurados (quando aplicável)
- Assinatura do responsável técnico

> **Formato de ensaio disponível (2026-11-07):** `python -m app.ops.drill` restaura em
> PostgreSQL descartável — origem e destino criados pelo próprio ensaio, identidade
> comprovada — e grava um relatório com integridade, release, ponto de recuperação, início,
> fim e duração até a primeira consulta bem-sucedida. O mesmo formato serve à recuperação
> de uma cópia guardada fora da VM (`--from-manifest`, em Linux e com o banco esperado
> informado à parte). Tempos de bancada não valem como
> RTO de produção. Itens da primeira janela real:
> [`../operations/ops_window_checklist.md`](../operations/ops_window_checklist.md).

---

## 4. Estratégia de acesso remoto

### 4.1 Situação atual

- Acesso remoto do gestor: método atual desconhecido / provavelmente sem VPN
- Acesso remoto do suporte Engegraph: via link enviado por e-mail (método a auditar)
- Possível RDP exposto diretamente na internet (verificar no roteador)

### 4.2 Arquitetura-alvo

```
Internet
    │
    │  VPN (WireGuard / OpenVPN)
    │
Roteador/Firewall
    │
    ├── VLAN 20 (Administrativa) — acesso do gestor via VPN
    │
    └── VLAN 10 (Servidores) — acesso administrativo apenas via jump host ou VPN
```

**RDP deve ser bloqueado na internet.** Acesso administrativo ao servidor ocorre
apenas após estabelecimento de VPN.

### 4.3 Acesso de suporte Engegraph

- Fluxo atual: link de conexão recebido por e-mail após abertura de chamado
- Softwares candidatos (a confirmar): AnyDesk, TeamViewer, Splashtop, tool própria
- Auditoria necessária: verificar serviço persistente, permissões, logs de sessão
- Procedimento interno: gestor autoriza explicitamente; registra data/hora/motivo
- Log de chamados mantido na pasta `_VISTORIA/acesso_remoto/`

---

## 5. Contingência energética

| Componente | Situação atual | Meta |
|-----------|---------------|------|
| Nobreaks | Existem; autonomia baixa | Revisar baterias; documentar autonomia |
| Gerador | Não existe | Avaliar viabilidade (custo x risco) |
| Procedimento de desligamento seguro | Não documentado | Criar POP de desligamento em queda de energia |

**Ação imediata:**
- Medir autonomia atual dos nobreaks (tempo real, não nominal)
- Verificar data de última substituição de baterias
- Criar procedimento: se energia não retornar em X minutos, desligar servidor controlado

**Avaliação de gerador:**
- Um gerador pequeno (<5 kVA) pode cobrir servidor + switches
- Alternativa: contrato com empresa de UPS/gerador para eventos críticos

---

## 6. Plano de migração para virtualização

### Fase 0 — Pré-requisitos (antes de virtualizar)

1. Inventário completo de hardware do servidor atual
2. Avaliação de capacidade (RAM, CPU, storage disponível)
3. Confirmação com Engegraph de suporte a virtualização
4. Backup válido e testado do ambiente atual inteiro
5. Escolha do hipervisor
6. Avaliação de licenciamento (Windows, SQL Server)
7. Aprovação do gestor

### Fase 1 — Primeiras VMs (90 a 120 dias)

Prioridade: serviços que mais se beneficiam do isolamento e que são mais fáceis de migrar.

1. `VM-TestRestore` — criar primeiro; sem dados de produção; base para testes
2. `VM-CartorioSystem` — novo sistema, não há migração de dados legados complexa
3. `VM-Backup-Monitor` — agente de backup centralizado

**Estado de execução da Fase 1 (2026-11-12).** Separado por fonte — Git e CI, relato
operacional (runbook e relatórios privados, fora do Git), bancada e aceite real. Detalhe por
VM em [`infrastructure_state.md`](infrastructure_state.md):

| Item | Situação | Fonte |
|---|---|---|
| Host Proxmox + `VM-CartorioSystem` em homologação, dados sintéticos | Em operação desde 05–06/11 | Relato |
| Banco ativo em PostgreSQL 18 | Desde 07/11; decisão no [ADR-013](../decisions/ADR-013-troca-banco-ativo-sqlite-postgresql.md) | Relato |
| Compatibilidade PostgreSQL do código | PR #5 em `main` (`c49c6579`), CI verde | Git |
| Backup local diário (`pg_dump` + manifesto SHA-256) | Dois disparos automáticos consecutivos observados no journal (08/11); integridade do 2º par e restauração de cópia automática pendentes | Relato |
| Verificador operacional, alerta local, gate PostgreSQL, prova de recuperação — código | Em `main` (PR #6, merge `b22e1b6`); CI do PR `42413480266` e pós-merge `42431949823` verdes; PostgreSQL 18.6, gate sem teste pulado | Git e CI + bancada |
| Verificador operacional — implantação | Não instalado na VM; release ativa anterior a `app/ops` (leitura de 08/11) | Relato |
| Verificador operacional — aceite real | Pendente: itens 1 a 5 do [checklist](../operations/ops_window_checklist.md) | — |
| Partida após reboot (convidado e host), cópia no PC dedicado, restauração dela | Pendentes de janela | — |
| Cópia verificada fora do host e observador externo (piloto `CARTORIO-OPS-2`, [ADR-015](../decisions/ADR-015-copia-verificada-e-observador-fora-do-host.md)) | Piloto em `main` (PR #8, merge `6059df2`), CI verde; endurecimento `CARTORIO-OPS-3` em `main` (PR #11, merge `cb9fec9`, 11/11/2026; CI pós-merge `42949087241` verde), sem implantação; computador candidato a PC dedicado com inventário preliminar (11/11), não homologado | Git e CI + bancada + relato |
| `VM-TestRestore` (VM 101), laboratório sintético de recuperação | Em operação. Ciclo `CARTORIO-TESTRESTORE-1` homologado com ressalva (10/11). Isolamento de rede não provado: a janela da `CARTORIO-TESTRESTORE-2` não foi executada e está bloqueada desde a etapa R5 (13/11), por critério de aceite pendente de decisão. Ciclo da OPS-3 no SHA novo sem registro de execução | Relato |
| Laboratório Windows isolado (VM 102), preparação da Fase 3 | Concluído e homologado (`INFRA-VM102`, 12/11). Desligado, sem Engegraph e sem dado real. Revalidação depois do reboot do host pendente | Relato |
| `VM-Backup-Monitor` | Não iniciado. A ADR-015 e a ADR-016 preferem destino e observador fora do host | — |

### Fase 2 — FileServer e identidade (120 a 180 dias)

4. `VM-FileServer` — migrar compartilhamento de arquivos com permissões NTFS
5. `VM-DC` (se decidido) — criar Active Directory para gestão centralizada de identidade

### Fase 3 — Engegraph (180 dias em diante)

6. `VM-Engegraph-DB` — somente após confirmação com fornecedor e testes em lab
7. `VM-Engegraph-App` — após banco migrado e validado

> **Nota de 2026-11-12 (`DOC-INFRA-01`).** O inventário preliminar da origem mostrou
> aplicação e SQL Server 2022 Express no mesmo computador. Por isso, a primeira avaliação de
> laboratório deve verificar se aplicação e motor SQL podem ser reproduzidos **numa única VM
> Windows isolada**, com dados sintéticos. Isso não é decisão de produção: a separação dos
> itens 6 e 7 continua como alvo, dependente do fornecedor. Nenhuma etapa da investigação
> começou. As etapas propostas (`ENGEGRAPH-LAB`, E0 a E4) estão no §8.

**Rollback em cada fase:**
- Servidor físico original continua operacional durante toda a migração
- Migração ocorre em `VM-TestRestore` primeiro
- Go-live da VM de produção somente após validação completa em lab
- Plano de rollback documentado: como reverter para servidor físico em ≤ RTO

---

## 7. Evidências para dossiê técnico

Para cada componente implementado, gerar evidências:

| Evidência | Formato | Onde guardar |
|-----------|---------|-------------|
| Diagrama de rede (atual e alvo) | PNG/PDF | `_VISTORIA/rede/` |
| Configuração de VLANs | Screenshot + export | `_VISTORIA/rede/vlans/` |
| Configuração de firewall | Screenshot + regras exportadas | `_VISTORIA/firewall/` |
| Configuração VPN | Screenshot (sem credenciais) | `_VISTORIA/vpn/` |
| Logs de backup (30 dias) | Arquivo de log | `_VISTORIA/backup/logs/` |
| Ata de teste de restauração | PDF assinado | `_VISTORIA/backup/testes/` |
| Inventário de ativos | Planilha | `_VISTORIA/ativos/` |
| Configuração de auditoria Windows | Screenshot | `_VISTORIA/auditoria/` |
| Configuração MFA | Screenshot (sem credenciais) | `_VISTORIA/acesso/` |
| Hash SHA-256 dos documentos críticos | Arquivo .sha256 | `_VISTORIA/hashes/` |

---

## 8. Frentes de infraestrutura (checkpoint de 2026-11-12)

> Acrescentado na sprint documental `DOC-INFRA-01`. O estado de cada item e as pendências com
> ID estão em [`infrastructure_state.md`](infrastructure_state.md), que os §9 e §10 detalham.
> Este checkpoint apenas registra o estado das frentes apresentadas. Sua inclusão no roadmap não
> constitui autorização para executar novas etapas.

### 8.1 Concluídas

| Frente | Encerramento | Observação |
|---|---|---|
| Implantação e homologação da VM 102 (laboratório Windows isolado, `INFRA-VM102`) | 12/11/2026 (G5-A e G5-B) | Windows 10 Pro 22H2, sem Engegraph e sem dado real |
| Proteção e testes reais de isolamento da VM 102 | 12/11/2026 | Persistência depois do reboot do host não comprovada (P15) |
| Checkpoint do inventário preliminar da origem Engegraph | 11/11/2026 (vistoria) e 12/11/2026 (este registro) | Preliminar. O relatório-fonte não tem marca de aprovação formal. Local e tamanho dos bancos, build efetiva e confirmações do fornecedor pendentes |

### 8.2 Em andamento ou pendentes

| Frente | Situação | Depende de |
|---|---|---|
| Evolução OPS do Cartório System: instalação do verificador, itens 1 a 5 do [checklist](../operations/ops_window_checklist.md), homologação da OPS-3 na VM 101 | Código em `main` até a OPS-3. Nenhuma implantação registrada desde a leitura de 08/11 | Janelas e autorizações próprias; liberação da VM 101 |
| Revalidação depois do reboot do host (P15 e item 4 do checklist) | Pendente. Kernel novo instalado, aguardando o boot | Janela de reboot autorizada |
| Qualificação do computador candidato a backup | Inventário preliminar; **não homologado**. Seu uso para backups do Engegraph **não está autorizado** (BKP-2: a ADR-016, vigente, o restringe ao Cartório System; mudança de escopo exige nova decisão arquitetural). Nenhum mecanismo de backup recorrente do Engegraph foi aprovado | Bancada (partida, memória, discos, rede, energia, recuperação sintética) |
| Isolamento da VM 101 (`CARTORIO-TESTRESTORE-2`) | Janela bloqueada na etapa R5 (13/11); não autorizada nem executada | Decisão do operador sobre o critério de aceite; depois, autorização da janela |
| Achado de rede na bridge interna da VM 101 (P10) | Mudança mínima proposta, não executada. Enquanto existir, o isolamento só fecha com ressalva | Mudança própria autorizada, com janela e acesso pelo console |
| Levantamento de requisitos do Engegraph | Não iniciado; é a E0 abaixo | Fornecedor e operador |
| Política de licenciamento (P2) e de entrada de mídias (P20) | Pendentes | Decisão do operador |
| Plano de recuperação consistente do Engegraph (base SQL, GED e configuração) | Não comprovado | Fornecedor (procedimento e ponto consistente); fonte de referência definida |

### 8.3 Próxima frente proposta: `ENGEGRAPH-LAB`

Cada etapa exige autorização própria. Concluir uma etapa não autoriza a seguinte.

| Etapa | Escopo | Toca a infraestrutura? |
|---|---|---|
| **E0. Levantamento documental e matriz de requisitos** | Perguntas ao fornecedor e ao operador: versão, Windows homologado, runtimes, versão do SQL suportada e tamanho da base, licenciamento (chave, dongle, servidor ou ativação online), hardware, periféricos, privilégios, dados de teste, horário e portas | Não |
| **E1. Análise de compatibilidade** | Conflitos com o isolamento, capacidade do nó (o dimensionamento preliminar não está aprovado), versão do Windows. Parecer go/no-go | Não (leitura, se necessário) |
| **E2. Preparação autorizada** | Procedimento de entrada de mídias, dados sintéticos, snapshot de base (frente independente), relógio e licença, conforme a E1 | Só o autorizado |
| **E3. Instalação controlada** | Instalação no laboratório isolado, registrando o que o instalador muda | Sim, só no laboratório |
| **E4. Homologação funcional** | Testes com dados sintéticos e nova verificação do isolamento | Leitura e testes |

Pré-condições comuns a todas as etapas: [`infrastructure_state.md`](infrastructure_state.md)
§10. Backup e recuperação da origem ficam **fora** desta frente.
