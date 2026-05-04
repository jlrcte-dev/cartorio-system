# Arquitetura-alvo — Infraestrutura Virtualizada

> Documento de proposta técnica. Nenhuma das configurações aqui descritas
> está implementada. Este documento serve como referência de decisão e planejamento.

Última atualização: 2026-05-04

---

## Objetivo

Evoluir o ambiente atual (servidor físico único, sem segmentação, sem VMs) para uma
arquitetura que suporte:

- Segregação de funções por VM (isolamento de falhas)
- RPO ≤ 4h e RTO ≤ 8h (Classe 3)
- Testes de restauração sem afetar produção
- Gestão formal de acessos e auditoria
- Escalabilidade gradual sem reescrita de ambiente

A virtualização é um **meio técnico**, não uma solução de conformidade por si mesma.
A conformidade vem das políticas, dos processos e das evidências — a virtualização
as viabiliza tecnicamente.

---

## Diagrama de arquitetura-alvo

```
┌─────────────────────────────────────────────────────────────┐
│                    HOST DE VIRTUALIZAÇÃO                    │
│                  (Hyper-V / VMware / Proxmox)               │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │  VM-FileServer   │  │VM-CartorioSystem  │                 │
│  │  Windows Server  │  │  FastAPI + PgSQL  │                 │
│  │  NTFS + auditoria│  │  RPO ≤4h (dump)  │                 │
│  └────────┬─────────┘  └────────┬──────────┘                │
│           │                     │                           │
│  ┌────────┴─────────┐  ┌────────┴──────────┐                │
│  │VM-Engegraph-App  │  │  VM-Engegraph-DB   │                │
│  │  (se aprovado)   │  │  SQL Server        │                │
│  │  Aguarda confirm.│  │  dump + log backup │                │
│  └──────────────────┘  └───────────────────┘                │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │VM-Backup-Monitor │  │  VM-TestRestore   │                 │
│  │  Agente de backup│  │  Lab isolado      │                 │
│  │  Logs, alertas   │  │  Nunca em prod.   │                 │
│  └──────────────────┘  └──────────────────┘                 │
│                                                             │
│  ┌──────────────────┐                                       │
│  │     VM-DC        │                                       │
│  │  Active Directory│                                       │
│  │  (se decidido)   │                                       │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ VLAN 10            │ VLAN 20             │ VLAN 40
    Servidores          Administrativo         Clientes/Wi-Fi
                                                  (isolado)
```

---

## Especificação das VMs

### VM-FileServer

| Atributo | Detalhe |
|----------|---------|
| Função | Compartilhamento de arquivos centralizado |
| SO | Windows Server |
| Armazenamento | Volume dedicado (separado do sistema) |
| Permissões | NTFS por grupo/perfil; sem acesso genérico |
| Auditoria | Auditoria de objetos habilitada nas pastas críticas |
| Backup | Incremental a cada 4h; full semanal; off-site diário |
| Acesso | Apenas via VLAN 20 (administrativa); não acessível da VLAN 40 |
| Prioridade | Alta — primeira a migrar (menor risco) |

### VM-CartorioSystem

| Atributo | Detalhe |
|----------|---------|
| Função | Aplicação Cartório System (FastAPI) + PostgreSQL |
| SO | Linux (Ubuntu Server LTS recomendado) ou Windows Server |
| Portas | API: 8000 (interno); banco: 5432 (não exposto externamente) |
| Backup | Dump `pg_dump` a cada 4h; off-site diário |
| Logs | `/var/log/cartorio/` com rotação e retenção ≥5 anos |
| Acesso | API via VPN; banco apenas local à VM |
| Prioridade | Alta — sistema próprio em desenvolvimento |

### VM-Engegraph-App

| Atributo | Detalhe |
|----------|---------|
| Função | Aplicação Engegraph |
| Pré-requisito | **Confirmar com fornecedor Engegraph** suporte a virtualização |
| SO | Windows Server (versão a confirmar com fornecedor) |
| Portas | A confirmar com fornecedor |
| Acesso | Apenas via VLAN 20 |
| Prioridade | Média — depende de confirmação do fornecedor |

### VM-Engegraph-DB

| Atributo | Detalhe |
|----------|---------|
| Função | Banco de dados do Engegraph (provável SQL Server) |
| Pré-requisito | **Confirmar com fornecedor Engegraph** separação App/DB |
| Backup | `BACKUP DATABASE` completo diário + `BACKUP LOG` a cada 4h |
| Ferramenta | SQL Server Agent ou ferramenta compatível com VSS |
| Snapshots | **Não substituem backup** — usar apenas para rollback de mudanças planejadas |
| Prioridade | Média — separar App/DB melhora backup; depende do fornecedor |

### VM-Backup-Monitor

| Atributo | Detalhe |
|----------|---------|
| Função | Agente de backup centralizado, scheduler, logs, alertas |
| SO | Linux ou Windows Server |
| Software | A definir: Veeam, Bacula, Duplicati, Restic, ou solução comercial |
| Alertas | E-mail ou SMS em caso de falha; relatório semanal ao gestor |
| Destinos | Local (volume dedicado) + off-site (nuvem ou NAS externo) |
| Prioridade | Alta — crítico para RPO/RTO |

### VM-TestRestore

| Atributo | Detalhe |
|----------|---------|
| Função | Laboratório de testes de restauração e homologação |
| Isolamento | **Nunca conectada a VMs de produção** |
| Uso | Testes de restauração, simulações de desastre, validação de procedimentos |
| SO | Variado (espelha os sistemas de produção) |
| Prioridade | Alta — essencial para evidências do dossiê técnico |

### VM-DC (avaliação futura)

| Atributo | Detalhe |
|----------|---------|
| Função | Active Directory — gestão centralizada de identidades |
| Quando faz sentido | ≥5 colaboradores; quando NTFS local não for suficiente |
| Benefício | Controle de políticas (GPO), senhas, MFA via AD, auditoria centralizada |
| Prioridade | Baixa — avaliar após estabilização das outras VMs |

---

## Segmentação de rede

### VLANs planejadas

| VLAN | Nome | Dispositivos | Acesso a outras VLANs |
|------|------|-------------|----------------------|
| 10 | Servidores | Host + VMs de produção | Apenas via firewall + VPN |
| 20 | Administrativa | Estações dos colaboradores | VLAN 10 via firewall (controlado) |
| 30 | Colaboradores | Estações de colaboradores com acesso restrito | VLAN 20 limitado |
| 40 | Clientes/Visitantes | Wi-Fi de clientes | **Apenas internet; sem acesso interno** |
| 50 | Impressoras | Impressoras, scanners | Apenas VLAN 20 (FileServer) |

### Hardware necessário

| Componente | Requisito |
|-----------|-----------|
| Switch | Managed, suporte 802.1Q (VLANs) |
| Access Point | Suporte a múltiplos SSIDs com VLAN tagging |
| Firewall/Roteador | Suporte a VLANs, stateful, IPS/IDS (ou separado) |

**Opções de firewall:**
- pfSense / OPNsense (open source, robusto, gratuito)
- Fortinet FortiGate (comercial, suporte)
- Cisco ASA/FTD (comercial)
- MikroTik CHR/RouterOS (custo-benefício)

---

## Estratégia de snapshot

> Snapshots não substituem backup. Esta distinção é crítica.

| Situação | Snapshot | Backup |
|---------|----------|--------|
| Antes de mudança planejada (patch, config) | ✅ Usar | ✅ Fazer antes também |
| Backup de RPO ≤4h | ❌ Não usar | ✅ Obrigatório |
| Banco SQL Server | ❌ Snapshot de VM não garante consistência | ✅ BACKUP DATABASE |
| Recuperação de desastre | ❌ Pode não funcionar se host falhou | ✅ Backup off-site |

**Política de snapshots:**
- Criar snapshot apenas antes de mudanças planejadas
- Remover snapshots após validação (snapshots antigos degradam performance)
- Nunca manter snapshot como único meio de proteção de dados

---

## Plano de restauração (referência para PRD)

### Cenário: falha total do servidor

1. Acionar suporte do fornecedor de virtualização
2. Provisionar novo host (hardware reserva ou cloud temporária)
3. Restaurar VMs críticas em ordem de prioridade:
   - VM-Engegraph-DB → VM-Engegraph-App (operação cartorial)
   - VM-FileServer (arquivos)
   - VM-CartorioSystem (gestão)
4. Validar integridade dos dados restaurados (hashes)
5. Comunicar colaboradores e gestor
6. Registrar incidente

**Meta RTO:** ≤ 8 horas para sistemas críticos (Engegraph)
**Meta RPO:** ≤ 4 horas (última cópia válida)

### Cenário: falha de uma VM isolada

1. Identificar VM afetada
2. Restaurar a partir do backup mais recente em VM-TestRestore (validação)
3. Se válido, restaurar em produção
4. Tempo esperado: 1-3h (a medir e documentar em testes)

### Cenário: corrupção de dados (não hardware)

1. Identificar a data/hora da corrupção pelos logs de auditoria
2. Restaurar backup anterior ao evento
3. Validar integridade
4. Avaliar impacto nos dados entre backup e corrupção

---

## Dependências com o Engegraph

| Decisão | Quem decide | Prazo sugerido |
|---------|-------------|---------------|
| Virtualização suportada? | Engegraph (fornecedor) | 30 dias |
| Separação App/DB suportada? | Engegraph (fornecedor) | 30 dias |
| Procedimento de backup do banco | Engegraph (fornecedor) | 30 dias |
| Versão compatível do Windows Server | Engegraph (fornecedor) | 30 dias |
| Licenciamento em VM | Engegraph + fornecedor Windows | 45 dias |
| Portas de rede utilizadas | Engegraph (fornecedor) | 30 dias |
