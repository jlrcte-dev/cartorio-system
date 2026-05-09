# Roadmap de Infraestrutura — Cartório Costa Teixeira

> Documento de planejamento técnico. Nenhuma configuração descrita aqui está
> implementada salvo indicação explícita.

Última atualização: 2026-05-04

---

## 1. Situação atual

| Componente | Estado | Risco |
|-----------|--------|-------|
| Servidor físico Windows | Em operação | Host único — ponto único de falha |
| Engegraph (ERP) | Operacional | Sem contingência documentada |
| Banco Engegraph | Provavelmente SQL Server | Backup sem dump confirmado |
| Backup (Cobian Gravity) | Ativo, cópia de arquivos | Sem dump transacional; sem off-site |
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

### Fase 2 — FileServer e identidade (120 a 180 dias)

4. `VM-FileServer` — migrar compartilhamento de arquivos com permissões NTFS
5. `VM-DC` (se decidido) — criar Active Directory para gestão centralizada de identidade

### Fase 3 — Engegraph (180 dias em diante)

6. `VM-Engegraph-DB` — somente após confirmação com fornecedor e testes em lab
7. `VM-Engegraph-App` — após banco migrado e validado

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
