# Modelo de Registro de Riscos — Cartório System

> Este documento define o modelo (template) de registro de riscos usado pelo
> Módulo de Auditoria. O registro de riscos efetivo está em `RISK_REGISTER.md`.
> Este modelo é a especificação dos campos, enums e regras de preenchimento.

Última atualização: 2026-05-04

---

## Campos do registro de risco

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|------------|-----------|
| `id` | str | Sim | Identificador único. Formato: `<categoria>-<sequencial>`. Ex.: `RI-01`, `RS-03` |
| `category` | enum | Sim | Categoria do risco (ver tabela abaixo) |
| `title` | str | Sim | Título curto e descritivo (máximo 80 caracteres) |
| `description` | str | Sim | Descrição detalhada do risco e do cenário de ocorrência |
| `evidence` | str | Não | O que comprova o risco (arquivo de log, observação, entrevista, scan) |
| `origin` | enum | Sim | Como o risco foi identificado |
| `cnj_requirement` | str | Não | Requisito do Provimento 213/2026 relacionado (ex.: "B-01: RPO ≤4h") |
| `severity` | enum | Sim | Gravidade do impacto se o risco se materializar |
| `probability` | enum | Sim | Probabilidade de ocorrência |
| `impact` | enum | Sim | Impacto operacional se ocorrer |
| `priority` | enum | Sim | Prioridade de tratamento (calculada ou definida manualmente) |
| `recommendation` | str | Sim | Ação recomendada — o que fazer para mitigar |
| `owner` | str | Não | Responsável sugerido para tratar |
| `due_date` | date | Não | Prazo sugerido para resolução |
| `status` | enum | Sim | Estado atual do risco |
| `identified_at` | datetime | Sim | Data e hora de identificação |
| `reviewed_at` | datetime | Não | Data e hora da última revisão |
| `notes` | str | Não | Observações adicionais, histórico de tratamento |

---

## Enums

### category

| Valor | Descrição |
|-------|-----------|
| `INFRASTRUCTURE` | Hardware, servidor, discos, energia, ambiente físico |
| `BACKUP` | Backup, restauração, RPO, RTO, off-site |
| `SECURITY` | Autenticação, senhas, MFA, endpoint, malware |
| `NETWORK` | Rede, VPN, firewall, segmentação, portas expostas |
| `ACCESS` | Permissões, usuários, grupos, controle de acesso |
| `DOCUMENT` | Arquivos, pastas, digitalização, organização documental |
| `LGPD` | Dados pessoais, sigilo, conformidade LGPD |
| `CONTINUITY` | PCN, PRD, contingência, dependência crítica |
| `OPERATIONAL` | Fluxos, POPs, procedimentos, treinamento |
| `SYSTEM` | Cartório System, banco, logs, exports, autenticação |
| `REGULATORY` | CNJ, ARPEN, ONR, SEDI, obrigações externas |
| `ENGEGRAPH` | Engegraph especificamente: banco, backup, suporte, reinstalação |

### origin

| Valor | Descrição |
|-------|-----------|
| `SCANNER` | Identificado por scanner automatizado (Fase 1-6) |
| `MANUAL` | Registrado manualmente pelo gestor ou auditor |
| `TECHNICAL_REPORT` | Identificado em relatório técnico |
| `CHECKLIST` | Identificado via checklist estruturado |
| `INTERVIEW` | Identificado em entrevista com colaborador |
| `POLICY_REVIEW` | Identificado durante revisão de documentos e políticas |
| `CNJ_MAPPING` | Identificado via mapeamento do Provimento CNJ 213/2026 |
| `BACKUP_LOG` | Identificado via análise de log de backup |
| `DISK_SCAN` | Identificado via análise de disco/armazenamento |
| `NETWORK_REVIEW` | Identificado via revisão de rede |
| `OTHER` | Identificado por outro meio |
| `EXTERNAL` | Identificado por auditor externo ou vistoriador |

### severity

| Valor | Descrição | Exemplo |
|-------|-----------|---------|
| `CRITICAL` | Pode causar perda permanente de dados ou paralisação total | Backup sem dump do Engegraph |
| `HIGH` | Impacto severo mas recuperável | Sem VPN; RDP exposto |
| `MEDIUM` | Impacto moderado, operação continua com degradação | Sem MFA para admin |
| `LOW` | Impacto pequeno, operação normal | Nomenclatura inconsistente de pastas |
| `INFO` | Sem impacto imediato, observação de boa prática | Log de acesso ausente |

### probability

| Valor | Critério |
|-------|---------|
| `HIGH` | Ocorreu recentemente OU condições presentes para ocorrência imediata |
| `MEDIUM` | Possível nos próximos 6 meses se nada for feito |
| `LOW` | Improvável nos próximos 12 meses, mas possível |

### impact

| Valor | Critério |
|-------|---------|
| `HIGH` | Para as operações da serventia OU perde dados OU compromete sigilo |
| `MEDIUM` | Degrada operação significativamente, mas não paralisa |
| `LOW` | Desconforto operacional, sem prejuízo a atos ou dados |

### priority

A prioridade é derivada de severity + probability. Regra geral:

| Severity | Probability HIGH | Probability MEDIUM | Probability LOW |
|----------|-----------------|-------------------|-----------------|
| CRITICAL | URGENT | URGENT | HIGH |
| HIGH | URGENT | HIGH | MEDIUM |
| MEDIUM | HIGH | MEDIUM | LOW |
| LOW | MEDIUM | LOW | LOW |
| INFO | LOW | LOW | LOW |

### status

| Valor | Descrição |
|-------|-----------|
| `OPEN` | Risco identificado, sem ação iniciada |
| `IN_PROGRESS` | Ação de mitigação em andamento |
| `RESOLVED` | Risco mitigado e evidência disponível |
| `ACCEPTED` | Risco aceito conscientemente pelo gestor (com justificativa) |
| `CLOSED` | Risco não se aplica mais (ex.: sistema desativado) |

---

## Identificadores por categoria

| Prefixo | Categoria |
|---------|-----------|
| `RI-` | INFRASTRUCTURE |
| `RB-` | BACKUP |
| `RS-` | SECURITY |
| `RN-` | NETWORK |
| `RA-` | ACCESS |
| `RD-` | DOCUMENT |
| `RL-` | LGPD |
| `RC-` | CONTINUITY |
| `RO-` | OPERATIONAL |
| `RSY-` | SYSTEM |
| `RR-` | REGULATORY |
| `RE-` | ENGEGRAPH |

---

## Exemplo de registro preenchido

```json
{
  "id": "RB-01",
  "category": "BACKUP",
  "title": "Banco Engegraph sem dump consistente",
  "description": "O Cobian Gravity copia arquivos do servidor mas não executa dump SQL do banco. Em caso de falha de disco, os arquivos copiados podem não ser suficientes para restaurar o banco com integridade transacional.",
  "evidence": "Observação direta do Cobian Gravity + confirmação do fornecedor de que não oferece ferramenta própria de backup",
  "origin": "MANUAL",
  "cnj_requirement": "B-04: Dump consistente do banco de dados",
  "severity": "CRITICAL",
  "probability": "HIGH",
  "impact": "HIGH",
  "priority": "URGENT",
  "recommendation": "Confirmar com Engegraph o procedimento oficial de backup. Implementar dump SQL agendado (BACKUP DATABASE se SQL Server). Testar restauração em ambiente isolado.",
  "owner": "Responsável TI",
  "due_date": "2026-06-01",
  "status": "OPEN",
  "identified_at": "2026-05-04T00:00:00Z",
  "reviewed_at": null,
  "notes": "Pendência técnica aberta. Ver docs/operations/engegraph.md para detalhes."
}
```

---

## Regras de preenchimento

1. **Um risco por entrada.** Não agrupar riscos distintos em uma linha.
2. **Evidência obrigatória para RESOLVED.** Antes de marcar como resolvido, registrar
   a evidência (arquivo, screenshot, ata) no campo `evidence`.
3. **ACCEPTED exige justificativa.** O campo `notes` deve registrar o motivo da
   aceitação e quem aceitou (gestor).
4. **Revisão obrigatória a cada 30 dias** para riscos OPEN e IN_PROGRESS.
5. **Não apagar registros.** Riscos encerrados permanecem com status `CLOSED` para
   rastreabilidade histórica.
6. **Dados pessoais proibidos.** Nomes de clientes, CPFs ou dados de documentos
   nunca entram no registro de riscos.

---

## Integração com o Módulo de Auditoria

O modelo acima mapeia diretamente para a entidade `AuditFinding` do módulo
`app/modules/audit/`. A implementação da Etapa B (CRUD de AuditFinding) deve
usar este modelo como especificação dos campos e enums.

Os campos `cnj_requirement`, `origin` e `category` são adições ao modelo
original que enriquecem o registro para uso específico na adequação ao
Provimento CNJ 213/2026.
