# Alinhamento ao Provimento CNJ nº 213/2026 — Módulo de Auditoria

> Este documento mapeia como o Módulo de Auditoria do Cartório System apoia
> diretamente a adequação da serventia ao Provimento CNJ nº 213/2026, Classe 3.
> Não constitui declaração de conformidade.

Última atualização: 2026-05-04

---

## Como o módulo de auditoria apoia a adequação

O Módulo de Auditoria não implementa conformidade — ele a prepara. Cada fase do
módulo produz evidências, diagnósticos e artefatos que a serventia usa para:

1. Identificar gaps em relação aos requisitos do Provimento
2. Priorizar ações de adequação
3. Gerar evidências documentadas para a vistoria
4. Monitorar a evolução da adequação ao longo do tempo

---

## Mapa de fases × requisitos CNJ 213/2026

| Fase do módulo | Requisitos CNJ suportados | Artefato gerado |
|----------------|--------------------------|-----------------|
| Fase 1 — Scanner de arquivos | D-01 (dossiê), D-04 (interoperabilidade) | `inventory.json`, `report.md` |
| Fase 2 — Diagnóstico documental | G-01 (PSI), G-02 (inventário), D-01 (dossiê) | `diagnosis_report.md`, `policies_inventory.md` |
| Fase 3 — Discos e armazenamento | B-01 (RPO), RI-02/03 (discos críticos) | `disk_report.md` |
| Fase 4 — Backup | B-01 a B-09 (backup e continuidade) | `backup_audit_report.md` |
| Fase 5 — Segurança local | A-01 a A-06 (autenticação, acesso), E-01 a E-04 (endpoint) | `security_local_report.md` |
| Fase 6 — Rede | N-01 a N-09 (rede e segmentação) | `network_local_report.md` |
| Fase 7 — POPs e políticas | G-01 a G-05 (governança), I-01 a I-04 (incidentes) | `policies_inventory.md` |
| Fase 8 — Fluxos operacionais | T-01 a T-04 (auditoria), G-04 (classificação) | `flows_diagnosis.md` |
| Fase 9 — Motor de riscos | Todos | `risk_matrix.md`, `action_plan.md` |
| Fase 10 — Dossiê | D-01 a D-05 (dossiê e portabilidade) | `dossier_index.json` |

> Códigos de requisito referem-se à `CNJ_213_COMPLIANCE_PLAN.md`.

---

## Requisitos críticos para Classe 3 e como o módulo os apoia

### B-01 — RPO máximo 4 horas

**Exigência:** backup incremental frequente para atingir RPO ≤4h.

**Como o módulo apoia:**
- Fase 4 audita os logs do Cobian Gravity e identifica a frequência real dos backups
- Gera evidência do gap entre RPO atual (~17h) e meta (≤4h)
- Documenta a necessidade de dump incremental do banco Engegraph
- Artefato: `backup_audit_report.md` com evidência para dossiê

---

### B-07 — Teste formal de restauração

**Exigência:** teste documentado com ata e evidências.

**Como o módulo apoia:**
- Fase 4 verifica se há registros de testes anteriores (por nome/data de arquivos)
- Gera checklist de pré-requisitos para o teste
- Fornece modelo de ata de restauração (ver `TECHNICAL_DOSSIER_STRUCTURE.md`)
- O teste em si é executado manualmente — o módulo prepara e documenta

---

### G-02 — Inventário de ativos

**Exigência:** inventário atualizado de todos os ativos de TI.

**Como o módulo apoia:**
- Fase 1 gera inventário completo de arquivos e pastas
- Fases 3 e 5 complementam com informações de disco e usuários
- O gestor complementa com hardware (não coletado automaticamente na Fase 1)
- Artefato: `inventory.json` + `inventory.csv` para análise

---

### A-05 — Controle de acesso por perfil (least privilege)

**Exigência:** permissões NTFS por grupo, sem acesso genérico.

**Como o módulo apoia:**
- Fase 2 identifica pastas com arquivos sensíveis acessíveis amplamente
- Fase 5 lista usuários e grupos ativos
- Gera relatório de achados de acesso para subsidiar configuração das permissões
- A configuração em si é executada manualmente pelo responsável TI

---

### T-01/T-02 — Trilhas de auditoria com retenção ≥5 anos

**Exigência:** logs de auditoria de sistemas com identificação de usuário, data,
hora, operação e proteção contra alteração.

**Como o módulo apoia:**
- O próprio módulo de auditoria implementa trilha de auditoria: cada achado tem
  `created_by`, `created_at`, `updated_by`, `updated_at` e não é deletável
- O Cartório System tem `created_by`/`updated_by` em todas as entidades financeiras
- Fase 5 verifica se auditoria de eventos Windows está habilitada
- A retenção de 5 anos deve ser configurada no servidor — o módulo documenta o gap

---

### D-01 — Dossiê técnico com evidências e hashes

**Exigência:** dossiê com evidências, hashes SHA-256, guarda mínima de 5 anos.

**Como o módulo apoia:**
- Fase 10 consolida todos os artefatos das fases anteriores
- Gera `dossier_index.json` com hash SHA-256 de cada documento
- Produz `dossier_report.md` com resumo executivo
- Verifica completude em relação ao `VISITATION_READINESS_CHECKLIST.md`
- Todos os artefatos são assinados digitalmente ou têm hash registrado

---

## Limitações do módulo em relação à conformidade

| Requisito | O módulo faz | O que requer ação humana |
|-----------|-------------|--------------------------|
| PSI própria | Diagnostica ausência; fornece template conceitual | Redigir, aprovar e assinar a PSI |
| PCN/PRD | Diagnostica ausência; fornece modelo | Elaborar, aprovar e assinar PCN/PRD |
| MFA | Diagnostica ausência | Configurar MFA no servidor e sistemas |
| VPN | Diagnostica ausência | Contratar solução e configurar |
| Segmentação de rede | Diagnostica ausência | Configurar VLANs no hardware |
| Teste de restauração | Fornece checklist e modelo de ata | Executar o teste manualmente |
| Backup off-site | Diagnostica ausência | Contratar solução e configurar |
| Capacitação | Identifica ausência de registros | Realizar capacitação e documentar |

O módulo é uma ferramenta de diagnóstico e evidência — não um agente de remediação.

---

## Cronograma de uso do módulo para a vistoria

| Quando executar | Fase | Artefato para dossiê |
|----------------|------|----------------------|
| Imediatamente (Sprint 1) | Fase 1 | Inventário de arquivos e relatório |
| Semana 1-2 | Fase 2 + Fase 3 | Diagnóstico documental + discos |
| Semana 2-3 | Fase 4 | Auditoria de backup |
| Semana 3-4 | Fase 5 + Fase 6 | Segurança local + rede |
| Semana 4-6 | Fase 7 + Fase 8 | Políticas + fluxos |
| Semana 6-8 | Fase 9 | Matriz de riscos + plano de ação |
| Antes da vistoria | Fase 10 | Dossiê técnico completo |

---

## Módulo Compliance (fundação read-only)

Em 2026-05-06 foi iniciado o módulo `app/modules/compliance/` com a Sprint
LGPD/Compliance-1, que materializa a Matriz de Correlação INOVA V1 do
Provimento (requisitos → políticas indicadas → prazos por classe → evidências
sugeridas). A camada é estritamente consultiva (somente leitura) e **não
declara conformidade**. Detalhes em [`docs/modules/compliance.md`](modules/compliance.md).
