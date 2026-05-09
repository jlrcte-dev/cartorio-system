# Plano de Prontidão para Vistoria — Provimento CNJ nº 213/2026

> Complementa o `visitation_readiness_checklist.md` (neste diretório). Enquanto o checklist
> lista o que precisa existir, este documento descreve o plano de ação para
> chegar lá. Não constitui garantia de conformidade.

Última atualização: 2026-05-04

---

## Objetivo

Organizar as ações necessárias para que a serventia chegue à vistoria com:

1. Evidências documentadas dos controles implementados
2. Dossiê técnico estruturado com hashes
3. Gaps conhecidos documentados com plano de tratamento
4. Respostas prontas para os principais questionamentos do vistoriador

---

## O que o vistoriador avalia (Classe 3)

Com base no Provimento CNJ 213/2026, o vistoriador verifica:

| Bloco | Perguntas esperadas |
|-------|---------------------|
| Governança | "Existe PSI? Foi comunicada? Há responsável técnico designado?" |
| Inventário | "Tem inventário de ativos? Contratos e licenças listados?" |
| Acesso | "Os acessos são individualizados? Há MFA? Existe política de permissões?" |
| Backup | "Qual a frequência do backup? Há off-site? O banco tem dump consistente? Já testou restauração?" |
| Rede | "A rede está segmentada? Wi-Fi de clientes está isolado? Há firewall?" |
| Auditoria | "Há logs de auditoria? Por quanto tempo ficam? São protegidos?" |
| Continuidade | "Existe PCN? Existe PRD? Qual é o RTO/RPO definido?" |
| Incidentes | "Como responde a um incidente? Há plano formalizado?" |
| LGPD | "Os dados pessoais são tratados adequadamente?" |
| Sistema próprio | "O sistema de gestão tem trilha de auditoria? O banco está no backup?" |

---

## Plano de ação por horizonte

### Semana 1 (Emergencial — 0 a 7 dias)

**Meta:** eliminar os riscos críticos mais imediatos e criar as bases do dossiê.

| Ação | Responsável | Entregável |
|------|-------------|-----------|
| Verificar logs do Cobian — últimos 30 backups | Responsável TI | Printscreen + data |
| Confirmar espaço em disco (volumes) | Responsável TI | Printscreen de cada volume |
| Criar pasta `_VISTORIA/` na rede com acesso restrito | Responsável TI | Pasta criada |
| Rodar Sprint 1 do Scanner (Fase 1 do módulo) | Dev + Gestor | `inventory.json`, `report.md` |
| Verificar se RDP está exposto no roteador | Responsável TI | Printscreen do firewall do roteador |
| Verificar se Wi-Fi de clientes está isolado | Responsável TI | Printscreen ou teste |
| Criar planilha de inventário de ativos (hardware) | Responsável TI | Planilha inicial |
| Iniciar lista de contratos e licenças | Gestor | Tabela com validade |
| Criar pasta restrita para documentos sigilosos | Responsável TI | Pasta criada com permissões |

---

### Semanas 2-4 (Curto prazo — 0 a 30 dias)

**Meta:** PSI aprovada, VPN implantada, MFA ativo, permissões NTFS configuradas.

| Ação | Responsável | Entregável |
|------|-------------|-----------|
| Redigir e aprovar PSI v1.0 | Gestor | PSI assinada |
| Comunicar PSI a todos os colaboradores | Gestor | Lista de ciência assinada |
| Instalar e configurar VPN | Responsável TI | VPN operacional; screenshot de configuração |
| Bloquear RDP externo no roteador | Responsável TI | Screenshot confirmação |
| Implantar MFA para administradores | Responsável TI | Screenshot configuração MFA |
| Configurar permissões NTFS por grupo | Responsável TI | Matriz de acesso documentada |
| Confirmar com Engegraph procedimento de backup | Gestor/TI | E-mail ou documento do fornecedor |
| Definir responsável técnico formal | Gestor | Ato de designação |
| Executar Fases 2-3 do módulo (diagnóstico documental + disco) | Dev + Gestor | Relatórios de diagnóstico |
| Confirmar antivírus/EDR ativo em todas as máquinas | Responsável TI | Screenshot ou relatório |

---

### Semanas 5-12 (Médio prazo — 30 a 90 dias)

**Meta:** dossiê inicial completo, backup com RPO ≤4h em operação, primeiro teste de restauração realizado.

| Ação | Responsável | Entregável |
|------|-------------|-----------|
| Implantar backup incremental ≤4h (RPO Classe 3) | Responsável TI | Log de backup incremental |
| Implantar backup off-site | Responsável TI | Evidência de replicação |
| Monitoramento automático de backup | Responsável TI | Configuração de alertas |
| Primeiro teste formal de restauração | Responsável TI | Ata assinada com RTO medido |
| Elaborar PCN v1.0 | Gestor + TI | PCN assinado |
| Elaborar PRD v1.0 com RTO ≤8h e RPO ≤4h | Responsável TI | PRD assinado |
| Executar Fases 4-6 do módulo (backup, segurança, rede) | Dev + Gestor | Relatórios de auditoria |
| Segmentação de rede (VLANs ao menos: clientes isolados) | Responsável TI | Diagrama + configuração |
| Elaborar plano de resposta a incidentes | Gestor | IRP assinado |
| Classificação dos dados formalizada | Gestor | Documento assinado |
| Capacitação básica em segurança para colaboradores | Gestor | Ata com assinaturas |
| Dossiê inicial montado com evidências coletadas | Responsável TI | Pasta `_VISTORIA/` completa |

---

## Postura durante a vistoria

### O que demonstrar ativamente

1. **Mostrar o dossiê organizado** — cada seção com documentos datados e assinados
2. **Mostrar os logs de backup** — evidência de execução regular
3. **Mostrar a ata de teste de restauração** — com RTO medido
4. **Mostrar a configuração de MFA** — ativo e funcionando
5. **Mostrar o diagrama de rede** — com VLANs ou isolamento de clientes
6. **Mostrar a PSI assinada pelos colaboradores** — lista de ciência

### O que dizer sobre gaps conhecidos

Para cada gap ainda não resolvido, ter:

1. O gap identificado formalmente (no `../regulatory/cnj_213/compliance_plan.md` ou `RISK_REGISTER.md`)
2. O plano de tratamento com prazo
3. A justificativa técnica ou operacional da limitação atual

**Frase-padrão:** *"Este item foi identificado como gap em [data]. O plano de tratamento prevê [ação] com prazo em [data]."*

Isso demonstra maturidade de governança — o vistoriador valoriza mais um gap com plano documentado do que ausência de documentação.

### O que não fazer

- Não improvisar respostas sem evidência
- Não afirmar conformidade onde não há evidência
- Não revelar credenciais, senhas ou dados de clientes
- Não mostrar arquivos com dados pessoais de clientes durante a vistoria

---

## Perguntas para o vistoriador — preparação

Preparar resposta para cada pergunta abaixo com a evidência correspondente:

| Pergunta | Evidência disponível | Localização no dossiê |
|----------|---------------------|----------------------|
| "Tem PSI?" | PSI assinada | Seção 01 — Governança |
| "Quem é o responsável técnico?" | Ato de designação | Seção 01 — Governança |
| "Com que frequência faz backup?" | Log de backup + plano de backup | Seção 05 — Backup |
| "Já testou restauração?" | Ata de teste | Seção 05 — Backup |
| "Qual o RTO/RPO definido?" | PRD | Seção 06 — Continuidade |
| "A rede está segmentada?" | Diagrama de rede + configuração | Seção 03 — Rede |
| "Tem MFA?" | Screenshot configuração | Seção 04 — Acesso |
| "Os logs ficam por quanto tempo?" | Política de retenção + config | Seção 08 — Auditoria |
| "Há inventário de ativos?" | Planilha de inventário | Seção 02 — Inventário |
| "O sistema de gestão tem trilha de auditoria?" | Documentação do Cartório System | Seção 11 — Sistema |

---

## Documentos mínimos para a vistoria

Lista priorizada dos documentos que precisam existir no dia da vistoria:

### Indispensáveis (sem isso, vistoria provavelmente negativa)

1. PSI v1.0 assinada com lista de ciência
2. Inventário de ativos
3. Log de backup dos últimos 30 dias
4. Ata de ao menos um teste de restauração
5. Diagrama de rede (ao menos atual)
6. Evidência de MFA ativo
7. PCN v1.0 assinado
8. PRD v1.0 com RTO/RPO

### Importantes (demonstram maturidade)

9. Matriz de conformidade CNJ 213/2026 atualizada
10. Registro de riscos com planos de tratamento
11. Plano de resposta a incidentes
12. Contrato de suporte Engegraph
13. Evidências de permissões NTFS configuradas
14. Política de retenção de logs
15. Registros de capacitação

### Complementares (demonstram excelência)

16. Dossiê com hashes SHA-256
17. Segundo teste de restauração
18. Relatório do módulo de auditoria (inventário de arquivos)
19. Plano de virtualização aprovado
20. Fluxos operacionais documentados com POPs
