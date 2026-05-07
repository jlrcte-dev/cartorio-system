# Roadmap Estratégico — Provimento CNJ nº 213/2026 (Classe 3)

> **Aviso:** Este documento é um plano de adequação e não constitui declaração
> de conformidade jurídica. A serventia está em processo de diagnóstico e
> adequação. Nenhuma afirmação deste documento deve ser interpretada como
> certificação de conformidade.

Última atualização: 2026-05-07

---

## 1. Sumário executivo

O projeto Cartório System passa a operar em dois eixos simultâneos:

**Eixo 1 — Desenvolvimento do sistema próprio (Cartório System)**
Backend independente da serventia para gestão financeira, gerencial e
operacional. Evolução incremental em módulos, com testes e ruff limpos a cada etapa.

**Eixo 2 — Adequação técnica e regulatória (Provimento CNJ nº 213/2026)**
A Serventia Cartório Costa Teixeira foi classificada como **Classe 3**. Isso impõe
exigências específicas de infraestrutura, segurança, continuidade, governança,
documentação e rastreabilidade, com prazo inicial mais curto e metas de RTO/RPO
mais exigentes do que classes inferiores.

**Prioridade imediata:** a serventia será vistoriada em breve. A frente emergencial
(0 a 7 dias) e o ciclo de 30 e 90 dias representam as ações mais urgentes e estruturantes
para a vistoria e para a segurança operacional imediata.

**Metas mínimas Classe 3:**
- RPO máximo: **4 horas**
- RTO máximo: **8 horas**
- Prazo global de adequação: **24 meses a partir da publicação do Provimento**

---

## 2. Premissas

| # | Premissa |
|---|----------|
| P-01 | Serventia classificada como **Classe 3** conforme Provimento CNJ nº 213/2026 |
| P-02 | O Provimento CNJ nº 213/2026 é a referência normativa central |
| P-03 | O Engegraph é o sistema legado crítico de produção documental |
| P-04 | O banco do Engegraph é provavelmente SQL Server (a confirmar) |
| P-05 | O Cartório System é o sistema próprio em desenvolvimento (FastAPI + SQLite em desenvolvimento / PostgreSQL planejado para produção) |
| P-06 | A integração futura com o Atlas ocorre por dados estruturados, sem acoplamento direto |
| P-07 | O servidor atual é físico, Windows, hospedando Engegraph, arquivos e backup |
| P-08 | O backup atual (Cobian Gravity) copia arquivos sem dump transacional confirmado |
| P-09 | Não há VPN, MFA, segmentação de rede ou controle formal de permissões |
| P-10 | Há risco crítico de irrecuperabilidade do banco do Engegraph em falha de disco |
| P-11 | A serventia possui plano de continuidade operacional inicial (a revisar/formalizar) |
| P-12 | A adequação é um processo gradual; nenhuma ação isolada garante conformidade total |

---

## 3. Trilhas do roadmap

O roadmap é organizado em seis trilhas paralelas com dependências explícitas.

| Trilha | Nome | Objetivo principal |
|--------|------|--------------------|
| **A** | Governança e conformidade | PSI, LGPD, inventário, contratos, responsabilização |
| **B** | Infraestrutura, rede e continuidade | Correção de riscos críticos, virtualização, backup, RTO/RPO |
| **C** | Segurança da informação | Acesso, autenticação, firewall, endpoint, auditoria |
| **D** | Fluxos operacionais | Diagnóstico e padronização dos fluxos internos da serventia |
| **E** | Cartório System | Evolução do sistema próprio alinhada à conformidade |
| **F** | Dossiê técnico e vistoria | Evidências, matrizes, documentos para vistoria |

---

## 4. Plano emergencial — 0 a 7 dias

> Ações que devem ser iniciadas imediatamente, antes de qualquer outra etapa.

### B — Infraestrutura

- [ ] Verificar logs do Cobian Gravity dos últimos 30 dias (sucesso/falha/tamanho)
- [ ] Confirmar se há backup válido e recuperável disponível hoje
- [ ] Auditar espaço em disco no servidor: volume de dados, volume de backup, sistema
- [ ] Liberar/expandir espaço no disco de backup (medida de emergência)
- [ ] Auditar disco D: identificar o que ocupa espaço e qual o risco de esgotamento
- [ ] Verificar status dos nobreaks: autonomia atual, alarmes, data da última bateria
- [ ] Documentar topologia atual de rede (mesmo que informal, em papel/foto)

### C — Segurança

- [ ] Levantar todos os acessos administrativos ao servidor (usuários locais, contas de domínio se houver)
- [ ] Verificar se há porta RDP exposta diretamente na internet (roteador)
- [ ] Verificar se o Wi-Fi de clientes está isolado logicamente da rede administrativa
- [ ] Bloquear ou restringir acesso remoto inseguro até implantação de VPN formal
- [ ] Identificar software de acesso remoto do suporte Engegraph (verificar se deixa serviço persistente)

### A — Governança

- [ ] Criar pasta restrita no servidor para documentos sigilosos e suspeitos (acesso apenas ao gestor)
- [ ] Iniciar inventário de ativos (planilha simples: servidor, estações, impressoras, roteador, nobreaks)
- [ ] Listar contratos ativos: Engegraph, internet, e-notariado, outros fornecedores de TI

### F — Dossiê

- [ ] Criar pasta `_VISTORIA/` na rede local para centralizar evidências

  > **Nota:** A pasta `_VISTORIA/` é uma estrutura emergencial e provisória de
  > centralização de evidências. Não substitui o futuro repositório oficial de
  > documentação institucional, cuja arquitetura será definida durante o
  > Document Registry.

- [ ] Registrar data/hora de todas as ações emergenciais executadas (evidência para dossiê)
- [ ] Tirar screenshot do estado atual dos discos, backup e usuários (antes de qualquer mudança)

---

## 5. Plano de curto prazo — 0 a 30 dias

### A — Governança

- [ ] Redigir PSI própria da serventia (Política de Segurança da Informação, versão 1.0)
- [ ] Definir responsável técnico formal para TI e segurança
- [ ] Identificar se há necessidade de DPO/encarregado LGPD
- [ ] Inventariar contratos e licenças (Engegraph, Windows Server, antivírus, backup)
- [ ] Registrar todos os colaboradores com suas funções e níveis de acesso necessários
- [ ] Formalizar termo de responsabilidade para acesso a sistemas críticos

### B — Infraestrutura

- [ ] Definir solução de VPN para acesso remoto do gestor (ex.: WireGuard, OpenVPN, solução comercial)
- [ ] Iniciar segmentação mínima de rede: separar Wi-Fi de clientes da rede administrativa
- [ ] Revisar e atualizar plano de backup: incluir dump do banco Engegraph (após confirmação do procedimento)
- [ ] Confirmar com a Engegraph o procedimento oficial de backup e restauração do banco
- [ ] Definir política de retenção de backup (dias, versões, local e off-site)
- [ ] Definir RTO e RPO preliminares para cada sistema crítico
- [ ] Documentar topologia atual de rede (diagrama formal)
- [ ] Avaliar solução de backup off-site (nuvem, NAS externo, outro site)
- [ ] Avaliar nobreak/UPS: autonomia, alarmes, substituição de baterias se necessário

### C — Segurança

- [ ] Implantar VPN antes de qualquer outro acesso remoto
- [ ] Habilitar MFA para todos os acessos administrativos ao servidor e sistemas
- [ ] Configurar permissões NTFS por grupo/perfil nas pastas compartilhadas
- [ ] Habilitar auditoria de objetos nas pastas críticas (Windows Event Log)
- [ ] Instalar ou revisar antivírus/endpoint em todas as estações e servidor
- [ ] Eliminar contas genéricas e credenciais compartilhadas
- [ ] Documentar fluxo de autorização de suporte remoto da Engegraph

### D — Fluxos operacionais

- [ ] Mapear os principais fluxos: entrada de documentos, qualificação, geração, assinatura, arquivamento
- [ ] Mapear fluxo financeiro: emolumentos, repasses CNJ, ISS, fundos, caixa
- [ ] Levantar onde estão os documentos digitalizados e como são organizados/salvos
- [ ] Identificar documentos suspeitos/falsos: fluxo atual de tratamento e guarda

### E — Cartório System

- [ ] Confirmar que o banco SQLite (dev) e futuro PostgreSQL (prod) estarão em volume monitorado
- [ ] Planejar autenticação multiusuário: deixa de ser "muito depois" (ver seção 11)
- [ ] Planejar trilha de auditoria como requisito estrutural do sistema

### F — Dossiê

- [ ] Consolidar matriz gerencial de conformidade CNJ 213/2026 Classe 3 (ver `CNJ_213_COMPLIANCE_PLAN.md`)
- [ ] Criar registro de riscos inicial (ver `RISK_REGISTER.md`)
- [ ] Documentar topologia de rede atual com diagrama

---

## 6. Plano de 30 a 90 dias — Etapas 1 e 2 do Provimento

> Etapas 1 e 2 do Provimento CNJ 213/2026 são prioridade para Classe 3 com
> prazo inicial mais curto.

### A — Governança

- [ ] PSI aprovada e comunicada a todos os colaboradores
- [ ] Política de controle de acesso formalmente documentada
- [ ] Política de backup e restauração formalmente documentada
- [ ] Política de resposta a incidentes versão 1.0
- [ ] Política de gestão de ativos versão 1.0
- [ ] Inventário de ativos completo e atualizado
- [ ] Classificação dos dados (público, interno, restrito, confidencial)

### B — Infraestrutura

- [ ] VPN implantada e testada
- [ ] Backup off-site: solução escolhida e em operação
- [ ] Backup do banco Engegraph: dump transacional consistente confirmado e testado
- [ ] Primeiro teste formal de restauração realizado e documentado (ata + evidências)
- [ ] PCN (Plano de Continuidade de Negócios) versão 1.0 elaborado
- [ ] PRD (Plano de Recuperação de Desastres) versão 1.0 elaborado com RTO ≤8h e RPO ≤4h
- [ ] Contingência energética avaliada: nobreaks, autonomia, gerador (avaliação de viabilidade)
- [ ] Arquitetura-alvo de virtualização aprovada pelo gestor (ver `INFRASTRUCTURE_ROADMAP.md`)
- [ ] Plano de migração para VMs elaborado

### C — Segurança

- [ ] Segmentação mínima de rede implementada (VLANs ou equivalente): administrativa, servidores, clientes, impressoras
- [ ] Firewall stateful configurado
- [ ] Auditoria de acessos habilitada nos sistemas críticos
- [ ] MFA implantado e funcionando para todos os perfis administrativos
- [ ] Permissões NTFS revisadas e documentadas em matriz de acesso
- [ ] Gestão de vulnerabilidades: rotina de atualização de patches definida

### D — Fluxos operacionais

- [ ] Fluxos mapeados e documentados em POPs
- [ ] Fluxo de digitalização centralizado e padronizado
- [ ] Fluxo de documentos sigilosos/suspeitos documentado e com responsável definido

### E — Cartório System

- [x] Módulo de auditoria (Etapa B): CRUD de achados (AuditFinding) implementado
- [ ] Validar uso operacional do módulo de auditoria com dados reais da serventia
- [ ] Início do planejamento de autenticação multiusuário
- [ ] Banco de produção (PostgreSQL) definido e incluído no plano de backup
- [ ] **Blueprint de integração regulatória** (Sprint 2026-05-06): fronteiras,
  modelos futuros e roadmap definidos para `audit`, `retention`, `lgpd` e
  `compliance`. Ver
  [`CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md`](CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md)
  e ADRs em [`docs/decisions/`](decisions/).
- [x] **Sprint LGPD/Compliance-2** (2026-05-06): `ComplianceEvidence` MVP
  implementado. Evidências regulatórias reais podem ser registradas e
  vinculadas a requisitos da Matriz INOVA V1. Integração por referência fraca
  (ADR-001/ADR-002).
- [x] **Sprint LGPD/Compliance-3** (2026-05-06): `RequirementFindingLink` MVP
  implementado. Requisitos normativos podem ser vinculados a achados, sinais e
  ações de `audit`, `retention`, `lgpd` ou fontes externas, por referência
  fraca (`source_module` / `source_type` / `source_ref`). UniqueConstraint
  impede vínculos duplicados da mesma origem. Isolamento modular preservado:
  sem FK cruzada, sem import de outros módulos.
- [x] **Sprint LGPD/Compliance-4** (2026-05-07): `ComplianceRequirementStatus` MVP
  implementado (commit `d782013`). Status indicativo por requisito derivado de
  `ComplianceEvidence` e `RequirementFindingLink`. Recompute REST explícito com
  idempotência estrita. Histórico append-only (`ComplianceRequirementStatusHistory`).
  Campos de revisão humana somente leitura. Isolamento modular e linguagem
  conservadora preservados: sem conformidade automática, sem FK cruzada, sem
  import de `audit`, `lgpd`, `retention`. 433 testes passando.
- [x] **Sprint Compliance-4 Docs** (2026-05-07): Revisão de consistência documental
  pós-Compliance-4. Ajuste do blueprint regulatório e do roadmap para refletir
  o estado real das sprints Compliance-2, Compliance-3 e Compliance-4.
  Exclusivamente documental — sem alteração de código, testes ou migrations.
- [ ] **Document Registry-0 — CNPFE-GO Normative Matrix Blueprint**: próxima frente
  prioritária (exclusivamente documental/normativa, sem código). Objetivo: mapear
  documentos, livros, acervo, arquivos, pastas e classificadores esperados pela
  serventia conforme o Código de Normas e Procedimentos do Foro Extrajudicial de
  Goiás (CNPFE-GO). O futuro módulo `document_registry` será dono da matriz
  documental e do inventário institucional; `compliance` não assume essa
  responsabilidade e deverá consumi-la por referência fraca quando implementada.
- [ ] **Document Registry-1 — Expected Documents MVP**: futuro. Implementação da
  matriz de documentos esperados, candidatos encontrados pelo `audit`,
  conciliação e summary. Depende de Document Registry-0.
- [ ] **Compliance-5 — Operational Reporting MVP**: futuro, após Document Registry-0/1.
  Relatórios operacionais indicativos consolidando `compliance` + `document_registry`.
- [ ] **Compliance-6 — Human Review MVP**: futuro. Revisão humana explícita:
  preenchimento de `review_note`, `reviewed_by`, `reviewed_at`; uso efetivo
  de `UNDER_REVIEW`.

### F — Dossiê

- [ ] Dossiê técnico inicial com evidências de configuração e topologia
- [ ] Ata de primeiro teste de restauração
- [ ] Matriz de conformidade atualizada com evidências

---

## 7. Plano de 90 a 180 dias — Consolidação

### B — Infraestrutura

- [ ] Implementação faseada da virtualização (host, primeiras VMs)
- [ ] VM-FileServer em operação com permissões NTFS e auditoria
- [ ] VM-Backup/Monitoring em operação: alertas automáticos de falha de backup
- [ ] VM-CartorioSystem em operação (produção)
- [ ] Backup incremental compatível com RPO ≤4h
- [ ] Monitoramento contínuo de backups: alertas, logs, painel
- [ ] Teste de restauração incremental realizado e documentado
- [ ] Segmentação completa de rede (VLANs por função)

### C — Segurança

- [ ] Firewall com IPS/IDS ou solução equivalente implantado
- [ ] Proteção endpoint/EDR implantada
- [ ] Trilhas de auditoria com retenção mínima de 5 anos configuradas
- [ ] Centralização de logs de segurança
- [ ] Gestão de vulnerabilidades com rotina mensal de avaliação

### D — Fluxos operacionais

- [ ] POPs de todos os fluxos críticos finalizados e aprovados
- [ ] Digitalização centralizada: rotina, local, responsável, nomenclatura
- [ ] Piloto de fluxos internos integrados ao Cartório System

### E — Cartório System

- [ ] Autenticação multiusuário implementada (Etapa planejada)
- [ ] Trilha de auditoria interna do sistema em operação
- [ ] Módulo financeiro com fechamento mensal (Monthly Closing)
- [ ] Logs do sistema configurados com retenção adequada, sem vazar dados pessoais

### F — Dossiê

- [ ] Dossiê técnico atualizado com evidências de todas as configurações
- [ ] Registro de incidentes e resposta documentados
- [ ] Atas de testes de restauração (ao menos 2 testes documentados)

---

## 8. Plano de 6 a 24 meses — Maturidade

### B — Infraestrutura

- [ ] Alta disponibilidade/tolerância a falhas para sistemas críticos
- [ ] Virtualização completa: todas as VMs planejadas em operação
- [ ] Simulação anual de desastre (tabletop ou drill real) documentada
- [ ] Teste de extração integral ou segmentada do acervo digital
- [ ] Consolidação da redundância geográfica de backup

### C — Segurança

- [ ] Pentest ou metodologia equivalente para Classe 3 realizado
- [ ] Gestão formal de vulnerabilidades com ciclo trimestral
- [ ] Logs centralizados e protegidos contra alteração (imutabilidade)
- [ ] Portabilidade e reversibilidade do acervo documentadas e testadas

### A — Governança

- [ ] Consolidação da interoperabilidade com sistemas CNJ
- [ ] PSI e políticas revisadas anualmente
- [ ] Capacitação formal de colaboradores documentada

### E — Cartório System

- [ ] Exports com checksum, manifest e rastreabilidade completa
- [ ] Integração futura com Atlas por exports/eventos (unidirecional, sem acoplamento)
- [ ] Relatórios financeiros e CNJ com versionamento e evidência de geração
- [ ] Módulos de obrigações, relatórios e exports implementados

---

## 9. Estratégia de virtualização

> Ver detalhamento completo em `docs/architecture/target_infrastructure.md`.

### Objetivo

Criar um ambiente virtualizado no servidor atual (ou em hardware dedicado) que permita:
- Segregação de funções por VM
- Backup consistente por VM
- Testes de restauração sem afetar produção
- Expansão gradual sem reescrita de ambiente

### Benefícios esperados

- Isolamento de falhas: problema em uma VM não afeta as demais
- Snapshots facilitam testes e rollback (com cautela — snapshots não substituem backup)
- Migração facilitada para novo hardware
- Laboratório de testes sem custo de hardware adicional
- Base para tolerância a falhas e HA futuro

### Riscos

- Virtualizar aumenta a complexidade de gerenciamento
- Host único é ponto único de falha — requer backup e contingência do host
- Engegraph pode ter restrições de licenciamento em ambiente virtual (confirmar com fornecedor)
- SQL Server em VM exige backup consistente via agente ou dump, não apenas snapshot

### Pré-requisitos antes de virtualizar

1. Confirmar viabilidade de virtualização do Engegraph com o fornecedor
2. Confirmar licenciamento Windows Server para VMs
3. Confirmar licenciamento SQL Server (se aplicável)
4. Definir host de virtualização (Hyper-V, VMware ESXi, Proxmox)
5. Garantir hardware suficiente (RAM, CPU, storage)
6. Ter backup válido e testado do ambiente atual antes de migrar

### VMs sugeridas

| VM | Função | Observação |
|----|--------|-----------|
| `VM-FileServer` | Arquivos compartilhados com permissões NTFS e auditoria | Prioridade alta |
| `VM-CartorioSystem` | Aplicação FastAPI + PostgreSQL do Cartório System | Prioridade alta |
| `VM-Backup-Monitor` | Rotinas de backup, logs, alertas, monitoramento | Prioridade alta |
| `VM-Engegraph-App` | Aplicação Engegraph | Depende de aprovação do fornecedor |
| `VM-Engegraph-DB` | Banco do Engegraph (SQL Server) | Separar app/DB melhora backup; avaliar com fornecedor |
| `VM-DC` | Active Directory / controle de identidade, se aplicável | Avaliação futura |
| `VM-TestRestore` | Laboratório de testes de restauração e homologação | Essencial para evidências |

### Cautelas com banco de dados

- **Snapshots de VM não garantem consistência transacional** do banco SQL Server
- Backup correto de SQL Server exige: `BACKUP DATABASE` + `BACKUP LOG`, ou agente de backup com suporte a VSS SQL
- PRD deve documentar explicitamente o procedimento de restauração do banco e o tempo testado

### Política de backup por VM

- `VM-FileServer`: backup incremental a cada 4h (RPO Classe 3); full semanal
- `VM-CartorioSystem`: backup incremental a cada 4h; dump PostgreSQL a cada 4h
- `VM-Engegraph-DB`: dump SQL Server agendado (confirmar janela com fornecedor); incremental de log
- `VM-Backup-Monitor`: backup diário (contém os logs)
- Todas as VMs: snapshots somente antes de mudanças planejadas; não como substituto de backup

### Rollback

- Antes de qualquer migração: snapshot do estado atual + backup externo confirmado
- Plano documentado de rollback com passos e RTO estimado
- Teste de rollback em `VM-TestRestore` antes de aplicar em produção

---

## 10. Impacto no Cartório System

A adequação ao Provimento CNJ 213/2026 impacta diretamente o roadmap do sistema próprio.

### Mudanças de prioridade

| Item | Situação anterior | Nova prioridade |
|------|------------------|-----------------|
| Autenticação multiusuário | "Etapas que ficam para muito depois" | **Antes de uso por colaboradores** |
| Trilha de auditoria | Planejada no módulo audit | **Requisito estrutural imediato** |
| Logs de domínio | Não planejado | **Planejado — sem vazar dados pessoais** |
| Exports com rastreabilidade | Futuro genérico | **Com checksum, manifest, timestamp** |
| Backup do banco do sistema | Implícito | **Explícito: volume monitorado, incluído no PRD** |

### Requisitos novos no Cartório System

1. **Cada operação financeira relevante** deve registrar: usuário, timestamp, origem, trilha de alteração
2. **Logs não podem vazar dados pessoais** (nomes, CPF, dados de clientes)
3. **Exports e relatórios** devem ter: checksum SHA-256, timestamp de geração, identificação do usuário que gerou
4. **Relatórios CNJ** devem ter versionamento e evidência de geração (log de quem gerou, quando, hash do arquivo)
5. **Banco PostgreSQL de produção** deve estar em volume com monitoramento e incluído explicitamente no plano de backup e no PRD
6. **Trilha de auditoria** do módulo `audit/` deve ter retenção configurável e ser protegida contra deleção

### Sequência ajustada do Cartório System

```
Etapa A (Audit docs) ✅
  ↓
Etapa B (Audit CRUD: AuditFinding) ✅
  ↓
Etapa C (Auth básica: usuários, perfis, sessões) ← próxima (antecipada)
  ↓
Etapa D (Monthly Closing + logs de domínio)
  ↓
Etapa E (Exports com checksum e manifest)
  ↓
Etapas seguintes (Obrigações, Relatórios, etc.)
```

---

## 11. Riscos e decisões pendentes

| # | Decisão/Risco | Urgência | Impacto se não resolvido |
|---|---------------|----------|--------------------------|
| R-01 | Confirmar se banco Engegraph é SQL Server | Alta | Backup inconsistente |
| R-02 | Confirmar procedimento de backup consistente do Engegraph | Crítica | Irrecuperabilidade em falha |
| R-03 | Confirmar portas e método de acesso remoto do suporte Engegraph | Alta | Risco de acesso não auditado |
| R-04 | Confirmar SLA/contrato de suporte Engegraph (tempo de resposta em falha crítica) | Alta | RTO inviável |
| R-05 | Confirmar viabilidade de virtualizar Engegraph | Média | Impede arquitetura-alvo |
| R-06 | Licenciamento Windows Server para VMs (BYOL ou novo) | Média | Bloqueio legal na virtualização |
| R-07 | Licenciamento SQL Server (se aplicável) | Média | Bloqueio legal |
| R-08 | Solução de firewall/VPN escolhida e implantada | Crítica | Exposição de acesso remoto |
| R-09 | Solução de backup off-site escolhida | Alta | RPO inatingível sem cópia externa |
| R-10 | Fornecedor/responsável técnico externo de TI | Alta | Gargalo de execução |
| R-11 | DPO/encarregado LGPD: necessidade e nomeação | Média | Risco regulatório LGPD |
| R-12 | Autonomia dos nobreaks: risco de queda durante janela sem gerador | Alta | Corrupção de dados em queda de energia |
| R-13 | Disco D em situação crítica: risco de esgotamento imediato | Crítica | Perda de dados/paralisação |

---

## 12. Referências cruzadas

| Documento | Conteúdo |
|-----------|----------|
| [CNJ_213_COMPLIANCE_PLAN.md](CNJ_213_COMPLIANCE_PLAN.md) | Matriz de conformidade Classe 3 |
| [INFRASTRUCTURE_ROADMAP.md](INFRASTRUCTURE_ROADMAP.md) | Infraestrutura e virtualização |
| [RISK_REGISTER.md](RISK_REGISTER.md) | Registro de riscos detalhado |
| [VISITATION_READINESS_CHECKLIST.md](VISITATION_READINESS_CHECKLIST.md) | Checklist de prontidão para vistoria |
| [TECHNICAL_DOSSIER_STRUCTURE.md](TECHNICAL_DOSSIER_STRUCTURE.md) | Estrutura do dossiê técnico |
| [architecture/target_infrastructure.md](architecture/target_infrastructure.md) | Arquitetura-alvo de virtualização |
| [operations/engegraph.md](operations/engegraph.md) | Contexto operacional do Engegraph |
| [modules/audit.md](modules/audit.md) | Módulo de auditoria do Cartório System |
| [roadmap.md](roadmap.md) | Roadmap técnico do Cartório System |
