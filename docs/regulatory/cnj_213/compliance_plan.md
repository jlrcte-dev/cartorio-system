# Plano de Conformidade — Provimento CNJ nº 213/2026 (Classe 3)

> **Aviso:** Este documento é um plano de adequação em andamento. Nenhuma linha
> desta matriz deve ser interpretada como declaração de conformidade. O objetivo é
> rastrear gaps, prioridades e evidências.

Última atualização: 2026-05-04
Serventia: Cartório Costa Teixeira
Classificação: **Classe 3**
Metas mínimas: RPO ≤ 4h | RTO ≤ 8h | Prazo global: 24 meses

---

## Legenda

| Símbolo | Situação |
|---------|----------|
| ✅ | Implementado com evidência |
| 🟡 | Em andamento / parcialmente atendido |
| ❌ | Gap identificado — ação necessária |
| ❓ | Situação desconhecida — requer diagnóstico |
| ⏳ | Planejado — ainda não iniciado |

---

## Matriz de conformidade

### Bloco 1 — Governança e Políticas

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| G-01 | PSI própria da serventia aprovada e comunicada | Art. X §Y | ❌ | Não existe PSI formal | Crítica | 30 dias | Documento PSI assinado; lista de ciência dos colaboradores | Gestor |
| G-02 | Inventário de ativos atualizado | Art. X | ❌ | Inventário inexistente | Alta | 30 dias | Planilha de ativos com hash/serial | Responsável TI |
| G-03 | Contratos e licenças inventariados | Art. X | ❓ | Parcialmente levantado | Alta | 30 dias | Tabela de contratos com validade | Gestor |
| G-04 | Classificação dos dados (público/interno/restrito/confidencial) | Art. X | ❌ | Não realizada | Alta | 60 dias | Documento de classificação | Gestor |
| G-05 | Responsabilização individual: sem contas genéricas | Art. X | ❌ | Possível uso de credenciais compartilhadas | Crítica | 30 dias | Auditoria de contas; remoção de genéricas | Responsável TI |
| G-06 | Responsável técnico formal designado | Art. X | ❓ | Não definido formalmente | Alta | 30 dias | Ato de designação | Gestor |
| G-07 | DPO/encarregado LGPD (se exigido) | LGPD + Prov. | ❓ | Avaliação pendente | Média | 60 dias | Nomeação ou justificativa de dispensa | Gestor |
| G-08 | Capacitação formal de colaboradores documentada | Art. X | ❌ | Não há registro formal | Média | 90 dias | Atas de capacitação; registros de presença | Gestor |

### Bloco 2 — Controle de Acesso e Autenticação

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| A-01 | Autenticação individualizada para todos os sistemas | Art. X | ❌ | Contas podem ser compartilhadas | Crítica | 30 dias | Auditoria de usuários; confirmação de individualização | Responsável TI |
| A-02 | MFA para acessos administrativos e sistemas críticos | Art. X | ❌ | Não implantado | Crítica | 30 dias | Evidência de MFA ativo (screenshot configuração) | Responsável TI |
| A-03 | MFA para banco de dados e sistemas de gestão | Art. X | ❌ | Não implantado | Crítica | 45 dias | Evidência de MFA ativo | Responsável TI |
| A-04 | Vedação a contas genéricas e credenciais compartilhadas | Art. X | ❌ | Verificação pendente | Crítica | 30 dias | Lista de contas ativas; confirmação de unicidade | Responsável TI |
| A-05 | Controle de acesso por perfil/grupo (least privilege) | Art. X | ❌ | Permissões NTFS não configuradas | Alta | 30 dias | Matriz de acesso documentada | Responsável TI |
| A-06 | Acesso remoto apenas via VPN | Art. X | ❌ | Sem VPN; possível RDP exposto | Crítica | 30 dias | Configuração VPN; remoção de RDP exposto | Responsável TI |
| A-07 | Controle e registro de acesso de terceiros (suporte Engegraph) | Art. X | ❌ | Procedimento não documentado | Alta | 45 dias | Procedimento escrito; log de chamados | Gestor |

### Bloco 3 — Backup e Continuidade

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| B-01 | RPO máximo 4 horas (Classe 3) | Art. X | ❌ | Backup atual é diário (RPO ~17h) | Crítica | 90 dias | Configuração de backup incremental ≤4h | Responsável TI |
| B-02 | RTO máximo 8 horas (Classe 3) | Art. X | ❓ | RTO não testado formalmente | Crítica | 90 dias | Ata de teste de restauração com tempo medido | Responsável TI |
| B-03 | Backup completo semanal + incremental diário/frequente | Art. X | 🟡 | Full existe; incremental não confirmado | Alta | 60 dias | Log de backup configurado; evidência de execução | Responsável TI |
| B-04 | Dump consistente do banco de dados (Engegraph) | Art. X | ❌ | Cobian copia arquivos; dump não confirmado | Crítica | 30 dias | Confirmação com Engegraph; log de dump executado | Responsável TI |
| B-05 | Backup off-site com redundância geográfica | Art. X | ❌ | Sem cópia off-site | Alta | 60 dias | Configuração solução off-site; log de replicação | Responsável TI |
| B-06 | Monitoramento automático de backup com alerta de falhas | Art. X | ❌ | Sem monitoramento automático | Alta | 90 dias | Configuração de alertas; evidência de notificação | Responsável TI |
| B-07 | Teste formal documentado de restauração (ata + evidências) | Art. X | ❌ | Nunca realizado formalmente | Crítica | 60 dias | Ata assinada; evidências (prints, tempo, hash) | Responsável TI |
| B-08 | PCN formalizado | Art. X | 🟡 | Existe rascunho; não formalizado | Alta | 90 dias | Documento PCN aprovado e assinado | Gestor |
| B-09 | PRD com RTO/RPO definidos | Art. X | ❌ | PRD não existe formalmente | Crítica | 90 dias | Documento PRD com procedimentos e metas | Responsável TI |
| B-10 | Contingência energética documentada | Art. X | 🟡 | Nobreaks existem; autonomia baixa; sem gerador | Média | 90 dias | Documentação dos nobreaks; plano de contingência | Gestor |

### Bloco 4 — Rede e Segmentação

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| N-01 | Segmentação lógica formal da rede | Art. X | ❌ | Sem segmentação; Wi-Fi clientes pode acessar rede admin | Crítica | 60 dias | Diagrama de rede com VLANs; configuração switch/AP | Responsável TI |
| N-02 | VLAN rede de servidores | Art. X | ❌ | Não implementada | Alta | 90 dias | Configuração documentada | Responsável TI |
| N-03 | VLAN rede administrativa | Art. X | ❌ | Não implementada | Alta | 90 dias | Configuração documentada | Responsável TI |
| N-04 | VLAN rede colaboradores/estações | Art. X | ❌ | Não implementada | Alta | 90 dias | Configuração documentada | Responsável TI |
| N-05 | VLAN rede visitantes/clientes (isolada) | Art. X | ❌ | Não implementada; risco atual | Crítica | 30 dias | Configuração documentada; isolamento confirmado | Responsável TI |
| N-06 | VLAN impressoras/scanners (se aplicável) | Art. X | ⏳ | Planejado | Baixa | 120 dias | Configuração documentada | Responsável TI |
| N-07 | Firewall stateful implantado | Art. X | ❓ | Estado atual desconhecido | Alta | 60 dias | Evidência de configuração do firewall | Responsável TI |
| N-08 | IPS/IDS ou solução equivalente | Art. X | ❌ | Não implantado | Média | 120 dias | Configuração ativa; logs de detecção | Responsável TI |
| N-09 | Diagrama de rede documentado | Art. X | ❌ | Não existe formalmente | Alta | 30 dias | Diagrama atualizado com todos os dispositivos | Responsável TI |

### Bloco 5 — Proteção de Endpoints

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| E-01 | Antivírus/EDR em todas as estações | Art. X | ❓ | Estado atual desconhecido | Alta | 30 dias | Lista de estações com proteção ativa | Responsável TI |
| E-02 | Antivírus/EDR no servidor | Art. X | ❓ | Estado atual desconhecido | Alta | 30 dias | Evidência de proteção ativa no servidor | Responsável TI |
| E-03 | Gestão de atualizações: SO e aplicações | Art. X | ❓ | Estado atual desconhecido | Alta | 30 dias | Política de patches; relatório de atualização | Responsável TI |
| E-04 | Vulnerabilidades críticas: tratamento em prazo definido | Art. X | ❌ | Sem processo formal | Média | 60 dias | Processo documentado; registro de tratamentos | Responsável TI |

### Bloco 6 — Trilhas de Auditoria

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| T-01 | Trilhas de auditoria: usuário, data, hora, tipo de operação | Art. X | ❌ | Logs de sistema não configurados formalmente | Alta | 60 dias | Configuração de auditoria; amostra de log | Responsável TI |
| T-02 | Retenção mínima de 5 anos das trilhas | Art. X | ❌ | Sem política de retenção | Alta | 90 dias | Política de retenção documentada; config storage | Responsável TI |
| T-03 | Proteção das trilhas contra alteração indevida | Art. X | ❌ | Logs não protegidos contra adulteração | Alta | 90 dias | Config de imutabilidade ou exportação protegida | Responsável TI |
| T-04 | Auditoria em sistemas críticos (Engegraph, servidor, VPN) | Art. X | ❌ | Não configurado | Alta | 60 dias | Evidência de auditoria ativa por sistema | Responsável TI |

### Bloco 7 — Gestão de Incidentes

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| I-01 | Plano de resposta a incidentes formalizado | Art. X | ❌ | Não existe | Alta | 60 dias | Documento de IRP aprovado | Gestor |
| I-02 | Classificação de incidentes por gravidade | Art. X | ❌ | Não existe | Alta | 60 dias | Tabela de classificação documentada | Responsável TI |
| I-03 | Comunicação de incidentes críticos em até 72h | Art. X | ❌ | Sem processo formal | Alta | 60 dias | Processo documentado; registro de comunicações | Gestor |
| I-04 | Registro formal de incidentes | Art. X | ❌ | Sem registro formal | Alta | 60 dias | Log de incidentes registrado | Responsável TI |

### Bloco 8 — Dossiê Técnico e Portabilidade

| # | Requisito | Fonte | Situação | Gap | Prioridade | Prazo alvo | Evidência necessária | Responsável |
|---|-----------|-------|----------|-----|-----------|-----------|----------------------|-------------|
| D-01 | Dossiê técnico com evidências e hashes | Art. X | ❌ | Em construção | Alta | 90 dias | Dossiê completo com documentos e hashes SHA-256 | Responsável TI |
| D-02 | Assinatura digital onde aplicável | Art. X | ⏳ | Planejado | Média | 120 dias | Documentos assinados digitalmente | Gestor |
| D-03 | Guarda do dossiê por mínimo 5 anos | Art. X | ⏳ | Planejado | Média | 120 dias | Política de guarda documentada | Gestor |
| D-04 | Interoperabilidade e portabilidade de dados | Art. X | 🟡 | Cartório System nasceu com exports estruturados | Média | 180 dias | Documentação de portabilidade; teste de extração | Responsável TI |
| D-05 | Reversibilidade: capacidade de extrair acervo integralmente | Art. X | ❓ | Não testado | Média | 180 dias | Teste de extração documentado | Responsável TI |

---

## Resumo por prioridade

| Prioridade | Total de itens | Implementado ✅ | Em andamento 🟡 | Gap ❌ | Desconhecido ❓ | Planejado ⏳ |
|-----------|---------------|----------------|-----------------|--------|----------------|-------------|
| Crítica | 12 | 0 | 1 | 9 | 2 | 0 |
| Alta | 22 | 0 | 2 | 14 | 6 | 0 |
| Média | 10 | 0 | 0 | 4 | 2 | 4 |
| Baixa | 1 | 0 | 0 | 0 | 0 | 1 |
| **Total** | **45** | **0** | **3** | **27** | **10** | **5** |

> Esta matriz será atualizada à medida que ações forem executadas e evidências forem coletadas.
> Campos "Fonte no Provimento" (Art. X §Y) serão preenchidos após revisão do texto integral
> do Provimento CNJ nº 213/2026.
