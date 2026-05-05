# Modelo de Domínio Inicial — Módulo LGPD

> **Nota:** Este documento define as entidades, campos, enums e relacionamentos do módulo LGPD.  
> Foco no MVP: 5 entidades. Entidades futuras descritas separadamente.

Última atualização: 2026-05-05  
Versão: 1.0

---

## 1. Entidades do MVP

### 1.1 — LgpdAction

Representa uma ação do Plano de Ação LGPD (AC-01 a AC-25).

**Descrição:** Cada ação é uma entrega necessária para adequação LGPD.

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| `id` | UUID | Sim | Identificador único |
| `action_code` | String (10) | Sim | AC-01, AC-02, ..., AC-25 (unique) |
| `activity_name` | String (200) | Sim | Título descritivo |
| `category` | Enum | Sim | Governança, Preparação, Implantação |
| `description` | Text | Sim | Descrição detalhada da ação |
| `action_type` | Enum | Sim | Obrigatório, Recomendação |
| `priority` | Enum | Sim | Alta, Média |
| `responsible_department` | String (100) | Não | TI, RH, Jurídica, etc. |
| `owner_id` | FK → LgpdActionOwner | Não | Quem executa (relacionamento) |
| `status` | Enum | Sim | Pendente, Em Progresso, Concluída |
| `date_created` | DateTime | Sim | Quando foi criada (auto, import date) |
| `date_planned` | Date | Não | Data alvo original (from CSV) |
| `date_completed` | Date | Não | Data real de conclusão |
| `notes` | Text | Não | Observações adicionais |
| `created_by` | String (100) | Sim | Quem registrou (default: "gestor") |
| `updated_by` | String (100) | Sim | Último a atualizar |
| `updated_at` | DateTime | Sim | Timestamp do último update |

**Enums:**

```python
class LgpdActionCategory(str, Enum):
    GOVERNANCA = "Governança"
    PREPARACAO = "Preparação"
    IMPLANTACAO = "Implantação"

class LgpdActionType(str, Enum):
    OBRIGATORIO = "Obrigatório"
    RECOMENDACAO = "Recomendação"

class LgpdActionPriority(str, Enum):
    ALTA = "Alta"
    MEDIA = "Média"

class LgpdActionStatus(str, Enum):
    PENDENTE = "Pendente"
    EM_PROGRESSO = "Em Progresso"
    CONCLUIDA = "Concluída"
```

**Regras de negócio:**

1. `action_code` é unique; não pode duplicar
2. Transições válidas de status: Pendente → Em Progresso → Concluída
3. Não é possível voltar a Pendente após Em Progresso
4. Quando status → Concluída, `date_completed` deve ser preenchido
5. Histórico de mudanças é rastreado (via `updated_by` e `updated_at`)

**Relacionamentos:**

- 1 LgpdAction : N LgpdEvidence (uma ação pode ter múltiplas evidências)
- 1 LgpdAction : 1 LgpdActionOwner (muitas-para-um via `owner_id`)
- 1 LgpdAction : N TrainingRecord (se AC-11, múltiplos treinamentos)

---

### 1.2 — LgpdActionOwner

Representa o responsável por executar uma ação.

**Descrição:** Pode ser uma pessoa ou departamento responsável.

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| `id` | UUID | Sim | Identificador único |
| `name` | String (100) | Sim | Nome do responsável |
| `department` | String (100) | Não | TI, RH, Jurídica, etc. |
| `email` | String (100) | Não | Email de contato |
| `phone` | String (20) | Não | Telefone de contato |
| `is_active` | Boolean | Sim | Se ainda é responsável (default: true) |
| `created_at` | DateTime | Sim | Timestamp |

**Regras de negócio:**

1. Name é obrigatório
2. Email deve ser válido (validação de formato)
3. Múltiplas ações podem ter o mesmo owner
4. Owner pode ser inativado (is_active = false)

**Relacionamentos:**

- 1 LgpdActionOwner : N LgpdAction (um responsável, múltiplas ações)

---

### 1.3 — LgpdEvidence

Representa um documento que evidencia execução de uma ação.

**Descrição:** Política, screenshot, ata, certificado, parecer, etc.

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| `id` | UUID | Sim | Identificador único |
| `action_id` | FK → LgpdAction | Sim | Qual ação esta evidência prova |
| `evidence_type` | Enum | Sim | policy, screenshot, ata, certificado, parecer, email, outra |
| `file_name` | String (255) | Sim | Nome do arquivo original |
| `file_path` | String (500) | Não | Caminho relativo em `_VISTORIA/01_Evidencias_LGPD/` |
| `file_hash` | String (64) | Não | SHA-256 do arquivo |
| `file_size_bytes` | Integer | Não | Tamanho em bytes |
| `description` | Text | Não | O que é a evidência; por que prova a ação |
| `collected_date` | Date | Sim | Quando foi coletada |
| `collected_by` | String (100) | Sim | Quem coletou |
| `confidentiality_level` | Enum | Não | Public, Internal, Restricted, Confidential |
| `linked_policy_id` | FK → PolicyDocument | Não | Se é uma política, qual |
| `created_at` | DateTime | Sim | Timestamp do upload |

**Enums:**

```python
class LgpdEvidenceType(str, Enum):
    POLICY = "policy"
    SCREENSHOT = "screenshot"
    ATA = "ata"
    CERTIFICADO = "certificado"
    PARECER = "parecer"
    EMAIL = "email"
    OUTRA = "outra"

class ConfidentialityLevel(str, Enum):
    PUBLIC = "Public"
    INTERNAL = "Internal"
    RESTRICTED = "Restricted"
    CONFIDENTIAL = "Confidential"
```

**Regras de negócio:**

1. action_id é obrigatório; não pode ser orfã
2. file_hash é calculado automaticamente no upload
3. file_path é gerado automaticamente: `AC-{code}/{evidence_type}/{filename}`
4. Não é possível alterar file_hash após upload (imutável)
5. Arquivo é armazenado uma única vez; duplicate checking via hash

**Relacionamentos:**

- N LgpdEvidence : 1 LgpdAction (muitas evidências por ação)
- 1 LgpdEvidence : 1 PolicyDocument (opcional; se tipo = policy)

---

### 1.4 — PolicyDocument

Representa uma política ou procedimento versionado.

**Descrição:** Políticas elaboradas pela INOVA (PSI, Privacidade, Descarte, etc.).

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| `id` | UUID | Sim | Identificador único |
| `policy_code` | String (50) | Sim | PSI, Privacidade, Descarte, etc. (unique) |
| `policy_name` | String (200) | Sim | Nome completo |
| `current_version` | String (20) | Sim | 1.0, 1.1, 2.0, etc. |
| `file_path` | String (500) | Sim | Caminho ao .docx ou PDF original |
| `published_date` | Date | Não | Quando foi publicada |
| `next_review_date` | Date | Não | Próxima data de revisão |
| `legal_requirement` | String (200) | Não | LGPD Art. X, CNJ 213 Bloco Y, etc. |
| `approval_by` | String (100) | Não | Quem aprovou (gestor/jurídico) |
| `is_active` | Boolean | Sim | Se está em vigor (default: true) |
| `created_at` | DateTime | Sim | Timestamp |

**Regras de negócio:**

1. policy_code é unique
2. current_version deve ser semântico (major.minor)
3. Histórico de versões é rastreado (via updated_at)
4. Uma política pode estar inativa após ser superada

**Relacionamentos:**

- 1 PolicyDocument : N LgpdEvidence (muitas evidências podem referenciar uma política)
- 1 PolicyDocument : N LgpdAction (via ação que depende da política)

---

### 1.5 — TrainingRecord

Representa um treinamento realizado por um colaborador.

**Descrição:** Registra capacitação formal para suportar AC-11.

**Campos:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|---|---|
| `id` | UUID | Sim | Identificador único |
| `action_id` | FK → LgpdAction | Não | AC-11 (Treinamento), se aplicável |
| `training_name` | String (200) | Sim | "LGPD para colaboradores", "Segurança de dados", etc. |
| `training_date` | Date | Sim | Quando foi realizado |
| `participant_name` | String (100) | Sim | Nome do participante |
| `certificate_hash` | String (64) | Não | SHA-256 do certificado |
| `certificate_file` | String (500) | Não | Caminho ao arquivo de certificado |
| `duration_minutes` | Integer | Não | Duração em minutos |
| `trainer` | String (100) | Não | Quem ministrou |
| `passing_score` | Decimal (3,2) | Não | Nota obtida (0.00 a 100.00) |
| `created_at` | DateTime | Sim | Timestamp do registro |

**Regras de negócio:**

1. training_name é obrigatório
2. training_date não pode ser futura (ou com validação especial)
3. participant_name é obrigatório; não pode estar vazio
4. certificate_hash é calculado se arquivo for enviado
5. Múltiplos registros possíveis para mesmo treinamento (diversos participantes)

**Relacionamentos:**

- N TrainingRecord : 1 LgpdAction (muitos treinamentos vinculados a AC-11)

---

## 2. Entidades Futuras (Sprint 3+)

### 2.1 — ProcessingActivity

Representa uma atividade de tratamento de dados (RAT/ROPa).

**Status:** ⏳ Futuro (Sprint 3+)

**Descrição:** 38 atividades mapeadas na plataforma INOVA.

**Campos candidatos:**

| Campo | Tipo | Descrição |
|-------|------|---|
| `id` | UUID | Identificador único |
| `activity_name` | String | "Abertura de protocolo", "Recepção de documentos", etc. |
| `purpose` | Text | Finalidade do tratamento |
| `data_categories` | JSON | Tipos de dados: [CPF, nome, endereço, etc.] |
| `legal_basis` | Enum | Consentimento, Contrato, Lei, etc. |
| `retention_period` | String | Tempo de retenção |
| `linked_policy_id` | FK | Qual política governa |
| `risk_level` | Enum | Low, Medium, High |

**Vinculação:**
- Com AC-17 (Inventário de Dados Pessoais)
- Com 14 Políticas (cada atividade vinculada a política)

---

### 2.2 — PrivacyIncident

Representa um incidente de privacidade ou breach.

**Status:** ⏳ Futuro (Sprint 4+)

**Descrição:** Registra incidentes para suportar AC-25.

**Campos candidatos:**

| Campo | Tipo | Descrição |
|-------|------|---|
| `id` | UUID | Identificador único |
| `incident_date` | DateTime | Quando foi descoberto |
| `incident_type` | Enum | breach, unauthorized_access, loss, etc. |
| `description` | Text | Descrição do incidente |
| `affected_data_categories` | JSON | Quais tipos de dados foram afetados |
| `affected_record_count` | Integer | Quantos registros (se conhecido) |
| `response_actions` | JSON | Ações tomadas em resposta |
| `reported_to_authorities` | Boolean | Se notificou ANPD/autoridades |
| `report_date` | DateTime | Quando foi reportado (se aplicável) |
| `status` | Enum | open, resolved, closed |

**Regra:** Vinculado a AuditAction (via origem LGPD) ou registro separado

---

### 2.3 — VendorAssessment

Representa avaliação de fornecedor.

**Status:** ⏳ Futuro (Sprint 4+)

**Campos candidatos:**

| Campo | Tipo | Descrição |
|-------|------|---|
| `id` | UUID | Identificador único |
| `vendor_name` | String | Nome do fornecedor |
| `vendor_type` | Enum | Software, Hardware, Serviços, Consultoria |
| `risk_level` | Enum | Low, Medium, High, Critical |
| `contract_reviewed` | Boolean | Se contrato foi analisado |
| `compliance_status` | String | Compliant, Non-compliant, Under review |
| `last_assessment_date` | Date | Última avaliação |
| `action_id` | FK | AC-13 (Avaliação de Fornecedores) |

---

### 2.4 — DpoRecord

Representa a designação formal do DPO/Encarregado.

**Status:** ⏳ Futuro (Sprint 3+)

**Campos candidatos:**

| Campo | Tipo | Descrição |
|-------|------|---|
| `id` | UUID | Identificador único |
| `dpo_name` | String | Nome do DPO |
| `contact_email` | String | Email institucional |
| `contact_phone` | String | Telefone |
| `designation_date` | Date | Quando foi designado |
| `published_on_website` | Boolean | Se publicado no site |
| `action_id` | FK | AC-15 (Nomeação) e AC-16 (Divulgação) |

---

## 3. Enums Compartilhados

```python
# Estados e categorias gerais
class DocStatus(str, Enum):
    DRAFT = "Draft"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"

class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class LegalBasis(str, Enum):
    CONSENTIMENTO = "Consentimento"
    CONTRATO = "Contrato"
    LEI = "Lei"
    INTERESSE_LEGITIMO = "Interesse Legítimo"
    OBRIGACAO_LEGAL = "Obrigação Legal"
    PROTECAO_VITAL = "Proteção de Vida"
    EXERCICIO_FUNCOES = "Exercício de Funções"
```

---

## 4. Relacionamentos Globais

```
LgpdAction (25 itens do Plano)
  ├── 1 : N → LgpdActionOwner (responsável)
  ├── 1 : N → LgpdEvidence (documentos que provam)
  └── 1 : 1 → AC-11 → N TrainingRecord

PolicyDocument (14 políticas)
  ├── 1 : N → LgpdEvidence (se tipo = policy)
  └── vinculada a AC-03..06, AC-08, AC-09, AC-14, AC-19, AC-22, AC-23, AC-24

TrainingRecord (N registros por participante)
  └── N : 1 → LgpdAction (AC-11)

LgpdEvidence (22+ documentos no MVP)
  ├── N : 1 → LgpdAction
  └── N : 1 → PolicyDocument (opcional)

Futuro:
ProcessingActivity (38 atividades RAT/ROPa)
  └── 1 : 1 → AC-17

PrivacyIncident (incidentes)
  └── 1 : 1 → AC-25

VendorAssessment (fornecedores)
  └── 1 : 1 → AC-13

DpoRecord (DPO)
  └── 1 : 1 → AC-15, AC-16
```

---

## 5. Modelo de Domínio Conceitual

```
LGPD Compliance Ecosystem
├── Action (AC-01..25)
│   ├── Owner (responsável)
│   ├── Evidence (documentos)
│   │   └── Policy (tipo = policy)
│   └── Training (AC-11)
├── Policy (14 documentos)
│   └── Evidence (tipo = policy)
└── [Futuro]
    ├── ProcessingActivity (38 atividades)
    ├── PrivacyIncident
    ├── VendorAssessment
    └── DpoRecord
```

---

## 6. Decisões de Design

### 6.1 — Por que não armazenar dados pessoais de titulares?

**Decisão:** Módulo LGPD NOT armazena CPF, endereço, email de titulares.

**Justificativa:**
1. LGPD exige minimização: apenas dados necessários
2. Segurança: menos dados sensíveis em banco significa menor risco de breach
3. Privacidade by design: LGPD é sobre rastreamento de conformidade, não processamento de dados
4. Operacional: dados de titulares são responsabilidade de AC-20 (integração externa, não MVP)

**Alternativa rejeitada:** Armazenar em tabela separada criptografada.
Razão: Aumenta complexidade; não é necessário para MVP.

### 6.2 — Por que usar Hash SHA-256 em vez de armazenar arquivo inteiro?

**Decisão:** Armazenar hash e caminho, não conteúdo do arquivo.

**Justificativa:**
1. Rastreabilidade: hash prova integridade para vistoria
2. Performance: hash é pequeno; arquivo é grande
3. Segurança: arquivo original fica em `_VISTORIA/` (acesso restrito); banco só tem metadados
4. Conformidade: hash + timestamp é evidência para dossiê

### 6.3 — Por que não deletar ações/evidências?

**Decisão:** Ações são imutáveis; status evolui, não se deleta.

**Justificativa:**
1. Auditoria: histórico completo necessário para vistoria
2. Conformidade: não pode perder rastreamento do que foi feito
3. Responsabilidade: quem criou, quando, por quê — nunca é apagado

**Implementação:** Status `CANCELLED` (futuro) se necessário anular; nunca DELETE.

### 6.4 — Por que LgpdActionOwner é entidade separada?

**Decisão:** Owner é tabela separada, não string em LgpdAction.

**Justificativa:**
1. Reutilização: mesmo responsável pode executar múltiplas ações
2. Extensibilidade: owner pode ter email, phone, department → fácil adicionar sem migrar LgpdAction
3. Referência: possibilita relatórios "por responsável"

### 6.5 — Por que trainingRecord é separado?

**Decisão:** Treinamentos são tabela separada, não lista em LgpdAction.

**Justificativa:**
1. Múltiplos participantes: um treinamento pode ter 10+ participantes
2. Rastreabilidade: certificado individual, data, duração por participante
3. Relatórios: fácil contar "quantos colaboradores treinados?" por data

---

## 7. Constraints e Validações

### Nível de Banco

| Constraint | Tabela | Campo | Descrição |
|-----------|--------|-------|----------|
| PRIMARY KEY | LgpdAction | id | UUID gerado |
| UNIQUE | LgpdAction | action_code | AC-01..25 única |
| FOREIGN KEY | LgpdAction | owner_id | → LgpdActionOwner.id |
| FOREIGN KEY | LgpdEvidence | action_id | → LgpdAction.id (not null) |
| FOREIGN KEY | LgpdEvidence | linked_policy_id | → PolicyDocument.id (nullable) |
| FOREIGN KEY | TrainingRecord | action_id | → LgpdAction.id (nullable) |
| UNIQUE | PolicyDocument | policy_code | PSI, Privacidade, etc. |
| CHECK | LgpdAction | status IN (...) | Valores válidos de enum |
| CHECK | LgpdEvidence | file_hash LENGTH = 64 | SHA-256 fixo |

### Nível de Aplicação

| Validação | Campo | Regra |
|-----------|-------|-------|
| Format | LgpdAction.action_code | Matches `AC-\d{2}` |
| Format | LgpdEvidence.file_hash | 64 hex characters (SHA-256) |
| Format | PolicyDocument.current_version | Matches `\d+\.\d+` (semântico) |
| Range | TrainingRecord.passing_score | 0.00 ≤ score ≤ 100.00 |
| Date | TrainingRecord.training_date | Não pode ser futura |
| Length | LgpdActionOwner.email | Email válido |
| Transition | LgpdAction.status | Apenas Pending → InProgress → Completed |

---

## 8. Índices Recomendados

```sql
-- Busca rápida por ação
CREATE INDEX idx_lgpd_action_code ON lgpd_action(action_code);
CREATE INDEX idx_lgpd_action_status ON lgpd_action(status);

-- Busca por evidências
CREATE INDEX idx_lgpd_evidence_action_id ON lgpd_evidence(action_id);
CREATE INDEX idx_lgpd_evidence_type ON lgpd_evidence(evidence_type);

-- Busca por política
CREATE INDEX idx_policy_document_code ON policy_document(policy_code);

-- Busca por treinamento
CREATE INDEX idx_training_record_action_id ON training_record(action_id);
CREATE INDEX idx_training_record_date ON training_record(training_date);
```

---

## 9. Exemplos de Instâncias

### LgpdAction

```python
LgpdAction(
    id="550e8400-e29b-41d4-a716-446655440001",
    action_code="AC-15",
    activity_name="Nomeação do Encarregado de Proteção de Dados",
    category=LgpdActionCategory.IMPLANTACAO,
    description="Designar formalmente o DPO da serventia conforme Art. 5, II da LGPD",
    action_type=LgpdActionType.OBRIGATORIO,
    priority=LgpdActionPriority.ALTA,
    responsible_department="Jurídica",
    owner_id="550e8400-e29b-41d4-a716-446655440002",  # FK LgpdActionOwner
    status=LgpdActionStatus.PENDENTE,
    date_created=datetime(2026, 5, 5),
    date_planned=date(2023, 3, 10),
    date_completed=None,
    notes="Aguardando resposta de INOVA sobre critérios legais de designação",
    created_by="gestor",
    updated_by="gestor",
    updated_at=datetime(2026, 5, 5)
)
```

### LgpdEvidence

```python
LgpdEvidence(
    id="550e8400-e29b-41d4-a716-446655440010",
    action_id="550e8400-e29b-41d4-a716-446655440001",  # AC-15
    evidence_type=LgpdEvidenceType.EMAIL,
    file_name="email_designacao_dpo_20260505.eml",
    file_path="_VISTORIA/01_Evidencias_LGPD/AC-15/email_designacao_dpo_20260505.eml",
    file_hash="abc123def456...89abcdef",  # SHA-256
    file_size_bytes=4096,
    description="Email formal comunicando a designação do DPO",
    collected_date=date(2026, 5, 5),
    collected_by="gestor",
    confidentiality_level=ConfidentialityLevel.INTERNAL,
    linked_policy_id=None,
    created_at=datetime(2026, 5, 5, 10, 30)
)
```

### PolicyDocument

```python
PolicyDocument(
    id="550e8400-e29b-41d4-a716-446655440020",
    policy_code="PSI",
    policy_name="Política de Segurança da Informação",
    current_version="1.0",
    file_path="_local_data/LGPD-inova/Politicas-Procedimentos/98-PSI.docx",
    published_date=date(2023, 3, 15),
    next_review_date=date(2024, 3, 15),
    legal_requirement="LGPD Art. 32; CNJ 213 Bloco G",
    approval_by="Gestor + INOVA",
    is_active=True,
    created_at=datetime(2023, 3, 15)
)
```

---

## 10. Migrações Alembic

As migrações serão geradas automaticamente por `alembic revision --autogenerate`:

```
# Exemplo de nome
migrations/versions/
└── 202605050000_create_lgpd_module.py
    ├── create_table_lgpd_action
    ├── create_table_lgpd_action_owner
    ├── create_table_lgpd_evidence
    ├── create_table_policy_document
    ├── create_table_training_record
    └── create_indexes
```

Nenhuma migração será criada manualmente nesta sprint (LGPD-0).

---

**Preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.0  
**Status:** Modelo Completo
