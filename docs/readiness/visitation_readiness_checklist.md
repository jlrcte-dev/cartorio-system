# Checklist de Prontidão para Vistoria — Provimento CNJ nº 213/2026

> Documento operacional para acompanhar a preparação da vistoria.
> Atualizar status à medida que itens forem concluídos.
> Não incluir credenciais, dados pessoais ou informações sensíveis.

Serventia: Cartório Costa Teixeira | Classe 3
Última atualização: 2026-05-04

---

## Legenda

| Status | Símbolo | Significado |
|--------|---------|-------------|
| Pendente | ⬜ | Não iniciado |
| Em andamento | 🔄 | Iniciado mas não concluído |
| Implementado | ✅ | Concluído e funcionando |
| Evidência disponível | 📄 | Documento/print de evidência gerado |
| Bloqueado | 🔴 | Impedimento identificado; requer decisão |

---

## Bloco 1 — Governança

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 1.1 | PSI aprovada e assinada | ⬜ | — | Gestor | Versão 1.0 obrigatória |
| 1.2 | PSI comunicada e assinada por todos os colaboradores | ⬜ | — | Gestor | Lista de ciência |
| 1.3 | Inventário de ativos completo | ⬜ | — | Responsável TI | Inclui serial, localização, função |
| 1.4 | Contratos e licenças inventariados | ⬜ | — | Gestor | Engegraph, Windows, antivírus, internet |
| 1.5 | Responsável técnico de TI formalmente designado | ⬜ | — | Gestor | Ato formal ou e-mail formal |
| 1.6 | Classificação dos dados documentada | ⬜ | — | Gestor | Público/Interno/Restrito/Confidencial |
| 1.7 | Sem contas genéricas ou compartilhadas | ⬜ | — | Responsável TI | Auditoria de contas |
| 1.8 | Termos de responsabilidade assinados pelos colaboradores | ⬜ | — | Gestor | Por acesso a sistemas críticos |
| 1.9 | Registro de capacitação em segurança da informação | ⬜ | — | Gestor | Ata ou certificado |

## Bloco 2 — Controle de acesso e autenticação

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 2.1 | Contas individuais para todos os usuários (sem compartilhamento) | ⬜ | — | Responsável TI | |
| 2.2 | MFA ativo para administradores | ⬜ | — | Responsável TI | Screenshot da configuração |
| 2.3 | MFA ativo para acesso ao servidor | ⬜ | — | Responsável TI | |
| 2.4 | MFA ativo para banco de dados | ⬜ | — | Responsável TI | |
| 2.5 | Permissões NTFS configuradas por grupo/perfil | ⬜ | — | Responsável TI | Matriz de acesso documentada |
| 2.6 | Pasta de documentos sigilosos com acesso restrito | ⬜ | — | Responsável TI | Apenas gestor + autorizado |
| 2.7 | VPN implantada para acesso remoto | ⬜ | — | Responsável TI | |
| 2.8 | RDP externo bloqueado no roteador | ⬜ | — | Responsável TI | Verificação de porta 3389 |
| 2.9 | Procedimento de autorização de suporte Engegraph documentado | ⬜ | — | Gestor | Quem autoriza; como registrar |
| 2.10 | Log de chamados de suporte mantido (data, hora, motivo) | ⬜ | — | Gestor | Planilha ou sistema |

## Bloco 3 — Backup e restauração

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 3.1 | Dump consistente do banco Engegraph executado e verificado | ⬜ | — | Responsável TI | Confirmar com fornecedor |
| 3.2 | Backup incremental ≤4h configurado (RPO Classe 3) | ⬜ | — | Responsável TI | |
| 3.3 | Backup full semanal configurado | ⬜ | — | Responsável TI | |
| 3.4 | Backup off-site em operação | ⬜ | — | Responsável TI | Nuvem ou NAS externo |
| 3.5 | Monitoramento automático de backup com alerta de falha | ⬜ | — | Responsável TI | E-mail ou SMS |
| 3.6 | Log de backup dos últimos 30 dias disponível | ⬜ | — | Responsável TI | Evidência de execuções |
| 3.7 | Primeiro teste formal de restauração realizado | ⬜ | — | Responsável TI | Ata obrigatória |
| 3.8 | RTO medido e ≤8h confirmado em teste | ⬜ | — | Responsável TI | Registrar tempo real |
| 3.9 | Plano de backup documentado e aprovado | ⬜ | — | Gestor | Inclui retenção e responsável |
| 3.10 | PCN formalizado e aprovado | ⬜ | — | Gestor | Versão 1.0 |
| 3.11 | PRD formalizado com RTO ≤8h e RPO ≤4h | ⬜ | — | Responsável TI | Procedimentos passo a passo |

## Bloco 4 — Rede e firewall

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 4.1 | Diagrama de rede atual documentado | ⬜ | — | Responsável TI | Inclui todos os dispositivos |
| 4.2 | Wi-Fi de clientes isolado logicamente da rede administrativa | ⬜ | — | Responsável TI | VLAN ou rede separada |
| 4.3 | VLANs configuradas (ao menos: servidores, admin, clientes) | ⬜ | — | Responsável TI | |
| 4.4 | Firewall stateful configurado | ⬜ | — | Responsável TI | |
| 4.5 | Topologia de rede alvo documentada | ⬜ | — | Responsável TI | |

## Bloco 5 — Proteção de endpoints

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 5.1 | Antivírus/EDR instalado e ativo em todas as estações | ⬜ | — | Responsável TI | Lista de estações com proteção |
| 5.2 | Antivírus/EDR instalado e ativo no servidor | ⬜ | — | Responsável TI | |
| 5.3 | SO e aplicações atualizados (patches aplicados) | ⬜ | — | Responsável TI | Relatório de atualização |
| 5.4 | Política de atualização de patches documentada | ⬜ | — | Responsável TI | |

## Bloco 6 — Trilhas de auditoria

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 6.1 | Auditoria de eventos habilitada no Windows Server | ⬜ | — | Responsável TI | Login/logout, acesso a arquivos |
| 6.2 | Auditoria de objetos habilitada nas pastas críticas | ⬜ | — | Responsável TI | FileServer, pastas sigilosas |
| 6.3 | Retenção de logs configurada para ≥5 anos | ⬜ | — | Responsável TI | Ou exportação/centralização |
| 6.4 | Proteção de logs contra alteração indevida | ⬜ | — | Responsável TI | |
| 6.5 | Trilha de auditoria do Cartório System configurada | ⬜ | — | Desenvolvedor | Módulo audit em operação |

## Bloco 7 — Gestão de incidentes

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 7.1 | Plano de resposta a incidentes formalizado | ⬜ | — | Gestor | |
| 7.2 | Tabela de classificação de incidentes por gravidade | ⬜ | — | Gestor | |
| 7.3 | Processo de comunicação de incidentes críticos (72h) | ⬜ | — | Gestor | |
| 7.4 | Registro de incidentes criado e disponível | ⬜ | — | Responsável TI | |

## Bloco 8 — Dossiê técnico

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 8.1 | Pasta `_VISTORIA/` criada na rede local | ⬜ | — | Responsável TI | Com subpastas organizadas |
| 8.2 | Inventário de ativos com evidências | ⬜ | — | Responsável TI | |
| 8.3 | Diagrama de rede atual | ⬜ | — | Responsável TI | |
| 8.4 | Diagrama de rede alvo | ⬜ | — | Responsável TI | |
| 8.5 | Evidências de configuração de VPN | ⬜ | — | Responsável TI | Sem credenciais |
| 8.6 | Evidências de configuração de MFA | ⬜ | — | Responsável TI | Sem credenciais |
| 8.7 | Evidências de configuração de firewall | ⬜ | — | Responsável TI | |
| 8.8 | Evidências de configuração de backup | ⬜ | — | Responsável TI | |
| 8.9 | Log de backup dos últimos 30 dias | ⬜ | — | Responsável TI | |
| 8.10 | Ata de teste de restauração (com RTO medido) | ⬜ | — | Responsável TI | Assinada |
| 8.11 | Evidências de permissões NTFS (matriz de acesso) | ⬜ | — | Responsável TI | |
| 8.12 | PSI assinada | ⬜ | — | Gestor | |
| 8.13 | PCN assinado | ⬜ | — | Gestor | |
| 8.14 | PRD assinado | ⬜ | — | Responsável TI | |
| 8.15 | Plano de backup assinado | ⬜ | — | Responsável TI | |
| 8.16 | Contratos e licenças listados | ⬜ | — | Gestor | |
| 8.17 | Registros de capacitação | ⬜ | — | Gestor | |
| 8.18 | Hashes SHA-256 dos documentos críticos do dossiê | ⬜ | — | Responsável TI | |
| 8.19 | Plano de resposta a incidentes assinado | ⬜ | — | Gestor | |
| 8.20 | Log de chamados de suporte (últimos 6 meses) | ⬜ | — | Gestor | |

## Bloco 9 — Fluxos operacionais

| # | Item | Status | Evidência | Responsável | Observações |
|---|------|--------|-----------|-------------|-------------|
| 9.1 | Mapeamento dos principais fluxos operacionais documentado | ⬜ | — | Gestor | |
| 9.2 | Fluxo de entrada e qualificação de documentos documentado | ⬜ | — | Gestor | |
| 9.3 | Fluxo de digitalização centralizado e padronizado | ⬜ | — | Gestor | |
| 9.4 | Fluxo de tratamento de documentos sigilosos/suspeitos documentado | ⬜ | — | Gestor | |
| 9.5 | POPs dos fluxos críticos aprovados | ⬜ | — | Gestor | |

---

## Resumo de progresso

| Bloco | Total | Concluídos ✅ | Em andamento 🔄 | Pendentes ⬜ |
|-------|-------|--------------|-----------------|------------|
| 1 — Governança | 9 | 0 | 0 | 9 |
| 2 — Acesso e autenticação | 10 | 0 | 0 | 10 |
| 3 — Backup e restauração | 11 | 0 | 0 | 11 |
| 4 — Rede e firewall | 5 | 0 | 0 | 5 |
| 5 — Endpoints | 4 | 0 | 0 | 4 |
| 6 — Trilhas de auditoria | 5 | 0 | 0 | 5 |
| 7 — Gestão de incidentes | 4 | 0 | 0 | 4 |
| 8 — Dossiê técnico | 20 | 0 | 0 | 20 |
| 9 — Fluxos operacionais | 5 | 0 | 0 | 5 |
| **Total** | **73** | **0** | **0** | **73** |

> Atualizar este resumo a cada revisão semanal.
