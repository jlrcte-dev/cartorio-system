# Módulo LGPD — Operacionalização e Evidenciação do Plano de Ação

> **Prioridade:** Módulo de suporte operacional para conformidade jurídica  
> **Status:** Design arquitetural (Sprint LGPD-0) — Pronto para implementação  
> **Última atualização:** 2026-05-05

---

## 1. Objetivo e Escopo

O módulo LGPD do Cartório System é a ferramenta integrada de **operacionalização, rastreamento e evidenciação** do Plano de Ação LGPD da serventia.

### Funções principais

1. **Centralizar** o Plano de Ação (25 ações) em banco de dados estruturado
2. **Rastrear** responsáveis, prazos, status e evidências de cada ação
3. **Evidenciar** execução com documentos, políticas, hashes e metadados
4. **Gerar** relatórios de conformidade para gestor, INOVA e vistoria CNJ 213
5. **Integrar** ao módulo Audit para formar dossiê técnico unificado

### Escopo definido

**MVP (Sprint 1-3):**
- Importação e CRUD do Plano de Ação.csv (25 ações)
- Versionamento e publicação de 14 políticas/procedimentos
- Registro de evidências (upload com hash SHA-256)
- Rastreamento de treinamentos
- Dashboard JSON + relatórios estruturados (CSV, Markdown)

**Fora do MVP (Sprint 4+):**
- Integração com plataforma INOVA (bloqueada por erro técnico)
- Coleta de consentimento de colaboradores (AC-10)
- Monitoramento de titulares (AC-20)
- Avaliação detalhada de fornecedores (AC-13)
- Incidentes de privacidade completo (AC-25)
- Dashboard visual gráfico
- RAT/ROPa estruturado (39 atividades de tratamento)

---

## 2. Papel e Limites

### O módulo LGPD **FAZ**

✅ Registrar e rastrear ações do Plano LGPD  
✅ Centralizar evidências com metadados (data, responsável, hash)  
✅ Gerar relatórios de status e conformidade  
✅ Criar índices para dossiê técnico  
✅ Apoiar decisões de cumprimento (não substitui jurídico)  
✅ Documentar rastreabilidade para vistoria

### O módulo LGPD **NÃO FAZ**

❌ **Substituir a INOVA LGPD** — assessoria jurídica permanece externa  
❌ **Emitir parecer jurídico** — apenas registra decisões já tomadas  
❌ **Afirmar conformidade legal** — documenta estado, não valida legalidade  
❌ **Armazenar dados pessoais de titulares** — apenas metadados e hashes  
❌ **Tomar decisões operacionais** — suporta tomada de decisão, não decide  
❌ **Modificar arquivos do servidor** — read-only da perspectiva de operações

---

## 3. Relação com INOVA LGPD

O módulo LGPD opera **em paralelo e complemento** à plataforma INOVA:

| Aspecto | INOVA LGPD | Cartório System — Módulo LGPD |
|---------|-----------|------|
| **Função** | Assessoria jurídica; elaboração de políticas | Operacionalização; rastreamento; evidenciação |
| **Dados** | 25 ações do Plano; 38 atividades RAT/ROPa | Mesmas 25 ações; histórico de execução; evidências |
| **Saídas** | Políticas, procedimentos, pareceres | Relatórios de status, dashboard, dossiê |
| **Decisão** | INOVA recomenda; gestor decide | Sistema registra execução das decisões |
| **Integração** | Futura (plataforma atualmente bloqueada por erro) | Independente; funciona sem integração INOVA |

**Fluxo ideal:**
```
INOVA define política → Gestor aprova → Módulo LGPD registra execução → 
Relatório gerado → INOVA revisa conformidade jurídica
```

---

## 4. Relação com Provimento CNJ nº 213/2026

O Plano de Ação LGPD (INOVA) conecta-se com 6 blocos do Provimento CNJ 213:

| Bloco CNJ 213 | Ações LGPD relacionadas | Cartório System |
|---|---|---|
| **G — Governança** | AC-04, AC-05, AC-06, AC-08 | PolicyDocument (armazenar) |
| **A — Controle de Acesso** | AC-10, AC-15, AC-16 | TrainingRecord, DpoRecord |
| **B — Backup** | AC-14 | Política versionada |
| **T — Trilhas de Auditoria** | AC-11, AC-22, AC-23 | TrainingRecord, integração com Audit |
| **I — Incidentes** | AC-25 | PrivacyIncident (futura) |
| **D — Dossiê Técnico** | Todas (evidência) | Consolidação em `_VISTORIA/` |

**Convergência:** O dossiê técnico (Fase 10 do Audit) unifica evidências LGPD + técnicas.

---

## 5. Relação com Módulo Audit

Ambos os módulos são **complementares e ortogonais**:

```
app/modules/
├── audit/                          # Diagnóstico técnico
│   ├── scanner/                    # Inventário de arquivos (read-only)
│   ├── findings/                   # Achados técnicos estruturados
│   ├── diagnosis/                  # Análise de risco documental
│   └── (fases 4-10: actions, dossier, etc.)
│
└── lgpd/                           # Conformidade jurídica
    ├── actions/                    # Plano de Ação LGPD
    ├── evidences/                  # Documentos com metadados
    ├── policies/                   # Políticas versionadas
    ├── training/                   # Registros de capacitação
    ├── processing_records/         # RAT/ROPa
    ├── incidents/                  # Incidentes (futura)
    └── reports/                    # Relatórios integrados

Integração (Fase 10):
  Audit findings + LGPD evidences → _VISTORIA/ (dossiê unificado)
```

**Dados compartilhados:**
- Audit → LGPD: contexto de controle de acesso, trilhas de auditoria
- LGPD → Audit: políticas de suporte, treinamentos de staff

---

## 6. Relação Futura com Atlas

**Escopo:** Fora do MVP. Previsto para Fase 7+ (após MVP operacional).

**Estratégia:**
- Unidirecional: Cartório System exporta resumos para Atlas
- Formato: JSON estruturado (`exports/lgpd/summary_for_atlas.json`)
- Conteúdo: Métricas de conformidade, status de ações, não dados pessoais
- Cartório System permanece **independente e autossuficiente**

---

## 7. Princípios Técnicos

1. **Segregação clara** — Módulo LGPD não toca dados operacionais de documentos; apenas políticas e ações
2. **Imutabilidade de ações** — Uma ação criada nunca é deletada; apenas seu status evolui
3. **Rastreabilidade completa** — Quem criou, quando, qual versão, qual evidência
4. **Read-only para dados sensíveis** — Nunca armazenar nomes de titulares; apenas metadados
5. **Hash + timestamp** — Cada evidência leva SHA-256 e data de coleta
6. **Independência de INOVA** — Funciona mesmo que plataforma INOVA esteja bloqueada
7. **Conformidade com CNJ 213** — Todos os artefatos contêm rastreabilidade completa
8. **Padrões do projeto** — Seguir convenções de Audit: FastAPI, SQLAlchemy, exports estruturados

---

## 8. Cuidados com Dados Pessoais

**Regra geral:** O módulo LGPD **não armazena dados pessoais de titulares**.

### O que PODE armazenar

✅ Nome da ação ("Nomeação do DPO")  
✅ Nome do responsável pela ação (servidor da serventia)  
✅ Tipo de documento de evidência ("policy", "screenshot", "ata")  
✅ Hash SHA-256 do arquivo evidência  
✅ Metadados: data, responsável, versão

### O que NUNCA armazena

❌ CPF de titulares  
❌ Endereço de titulares  
❌ Telefone de titulares  
❌ Email de titulares (exceto em casos específicos de consentimento)  
❌ Dados financeiros de titulares  
❌ Histórico completo de processamento (apenas metadados)

**Auditoria de logs:** Se um log contiver dado pessoal acidentalmente, é erro crítico → logging segregado por padrão.

---

## 9. Estratégia de Evidências

Evidências são documentos que **comprovam execução** de uma ação.

### Tipos de evidências capturadas

| Tipo | Exemplo | Armazenamento | Hash? |
|------|---------|------|---|
| **Policy** | 98-PSI.docx, Privacidade.docx | `_VISTORIA/01_Governanca/Politicas/` | Sim |
| **Ata** | ata_reuniao_20260505.pdf | `_VISTORIA/01_Governanca/Atas/` | Sim |
| **Certificado** | certificado_lgpd_joao.pdf | `_VISTORIA/Treinamentos/` | Sim |
| **Screenshot** | mfa_ativo.png, dpo_site.png | `_VISTORIA/01_Governanca/Screenshots/` | Sim |
| **Parecer jurídico** | parecer_contratos.docx | `_VISTORIA/Juridico/` | Sim |
| **Email formal** | email_designacao_dpo.eml | `_VISTORIA/01_Governanca/Emails/` | Sim |

### Fluxo de coleta

1. **Upload** → Usuário anexa arquivo à ação
2. **Validação** → Sistema verifica tipo, tamanho
3. **Hash** → SHA-256 calculado automaticamente
4. **Armazenamento** → Cópia em `_VISTORIA/`
5. **Metadados** → Registrados em `LgpdEvidence`
6. **Manifesto local** → JSON com detalhes por ação

---

## 10. Estratégia de Relatórios

Relatórios estruturados gerados automaticamente:

| Relatório | Formato | Destinatário | Frequência |
|-----------|---------|---|---|
| **R-01: Status Summary** | JSON, Markdown | Gestor | On-demand |
| **R-02: Action Detail** | Markdown | Gestor, INOVA | On-demand |
| **R-03: Conformity Matrix** | CSV | Gestor, vistoriador | Trimestral |
| **R-04: Evidence Manifest** | JSON | Audit, vistoriador | On-demand |
| **R-05: Training Summary** | CSV | Gestor, RH | Semestral |

**Exemplos de saída:**
- `lgpd_status_20260505.json` — Dashboard com 11/25 concluídas, 14 pendentes
- `lgpd_action_detail.md` — Detalhe de AC-15 (DPO): status, responsável, prazos, evidências
- `lgpd_conformity_cnj213.csv` — Mapa de ações LGPD → blocos CNJ 213
- `_VISTORIA/00_Indice_Hashes.xlsx` — Índice mestre com todos os hashes

---

## 11. Fases Futuras Previstas

### Sprint LGPD-4 — Incidentes e Resposta

Entidades: `PrivacyIncident`, integração com AuditAction  
Objetivo: AC-25 (Plano de Resposta a Incidentes) com registro formal e comunicação

### Sprint LGPD-5 — Avaliação de Fornecedores

Entidades: `VendorAssessment`  
Objetivo: AC-13 (Avaliação de Parceiros) estruturada

### Sprint LGPD-6 — RAT/ROPa Estruturado

Entidades: `ProcessingActivity`  
Objetivo: Importar e rastrear 38 atividades de tratamento

### Sprint LGPD-7+ — Integração com Atlas, automação assistida

---

## 12. Arquitetura do Código

Estrutura proposta (paralela ao padrão do Audit):

```
app/modules/lgpd/
├── __init__.py
├── enums.py                    # LgpdActionStatus, LgpdActionCategory
├── rules.py                    # Validações de negócio
│
├── actions/
│   ├── models.py               # LgpdAction, LgpdActionOwner
│   ├── schemas.py              # Pydantic para API
│   ├── service.py              # CRUD + import_from_csv
│   └── router.py               # POST/GET/PATCH endpoints
│
├── evidences/
│   ├── models.py               # LgpdEvidence, PolicyDocument
│   ├── schemas.py
│   ├── service.py
│   ├── storage.py              # Salvar em _VISTORIA/
│   └── router.py
│
├── training/
│   ├── models.py               # TrainingRecord
│   ├── schemas.py
│   ├── service.py
│   └── router.py
│
├── reports/
│   ├── generator.py            # Lógica de geração
│   ├── router.py               # Endpoints
│   └── exports/                # Templates
│
└── cli.py                      # Importação CLI
```

---

## 13. Entidades do MVP

### Críticas (Sprint 1-2)

| Entidade | Descrição | Status |
|----------|-----------|--------|
| `LgpdAction` | Ação do Plano (AC-01..25) | ✅ Sprint 1 |
| `LgpdActionOwner` | Responsável pela ação | ✅ Sprint 1 |
| `LgpdEvidence` | Documento anexado | ✅ Sprint 2 |
| `PolicyDocument` | Política versionada | ✅ Sprint 2 |
| `TrainingRecord` | Treinamento realizado | ✅ Sprint 2 |

### Futuras (Sprint 3+)

| Entidade | Descrição | Prioridade |
|----------|-----------|-----------|
| `ProcessingActivity` | Atividade RAT/ROPa | Sprint 3 |
| `PrivacyIncident` | Incidente de privacidade | Sprint 4 |
| `VendorAssessment` | Avaliação de fornecedor | Sprint 4 |
| `DpoRecord` | Registro do DPO | Sprint 3 |

---

## 14. APIs Principais

### Sprint 1 — Ações

```
POST   /api/v1/lgpd/actions/import          # Importar CSV
GET    /api/v1/lgpd/actions                 # Listar com filtros
GET    /api/v1/lgpd/actions/{id}            # Detalhe
PATCH  /api/v1/lgpd/actions/{id}            # Atualizar status
GET    /api/v1/lgpd/actions/summary         # Resumo: 11/25, etc.
GET    /api/v1/lgpd/actions/export?fmt=csv  # Exportar CSV
```

### Sprint 2 — Evidências

```
POST   /api/v1/lgpd/evidences               # Upload arquivo
GET    /api/v1/lgpd/evidences?action_id=AC-04  # Listar por ação
GET    /api/v1/lgpd/evidences/manifest      # Manifesto JSON
GET    /api/v1/lgpd/policies                # Listar políticas
POST   /api/v1/lgpd/training                # Registrar treinamento
GET    /api/v1/lgpd/training/report?fmt=csv # Relatório
```

### Sprint 3 — Relatórios

```
GET    /api/v1/lgpd/reports/status          # Dashboard JSON
GET    /api/v1/lgpd/reports/export?fmt=pdf  # Relatório completo
GET    /api/v1/lgpd/reports/conformity?mapping=cnj213  # Matriz
```

---

## 15. Critério de Pronto por Sprint

### Sprint LGPD-1: Ações

- [ ] 100% dos 25 itens importados do CSV
- [ ] Dashboard mostra 44% (11/25 concluídas)
- [ ] CRUD funcionando: create, read, update, delete status
- [ ] Filtros: categoria, prioridade, status, responsável
- [ ] Exportação CSV com metadados
- [ ] 20+ testes passando
- [ ] Ruff clean
- [ ] Documentação: como usar, como importar

### Sprint LGPD-2: Evidências

- [ ] 14 políticas importadas e versionadas
- [ ] Upload de arquivo funcionando (multipart)
- [ ] Hash SHA-256 calculado e verificado
- [ ] Mínimo 2 evidências por ação finalizada (22+ arquivos)
- [ ] Manifesto JSON gerado com hashes
- [ ] Dashboard mostra evidências por ação
- [ ] 25+ testes novos
- [ ] Ruff clean

### Sprint LGPD-3: Relatórios

- [ ] 4 relatórios principais gerando corretamente
- [ ] Números validados (totais batem)
- [ ] Dashboard JSON integrado a `/api/v1/`
- [ ] Integração com estrutura `_VISTORIA/` pronta
- [ ] 15+ testes novos
- [ ] Documentação: como gerar, como interpretar
- [ ] Ruff clean

---

## 16. Integração com Dossiê Técnico

Fase 10 do módulo Audit consolida artefatos:

```
_VISTORIA/
├── 01_Governanca/
│   ├── Politicas/              ← LGPD: 14 documentos versionados
│   └── Atas/                   ← LGPD: evidências de ações
├── 01_Evidencias_LGPD/         ← LGPD: 22+ evidências estruturadas
│   ├── AC-04/
│   │   ├── 98-PSI.docx
│   │   └── manifest.json
│   └── AC-15/
│       ├── email_designacao.eml
│       └── manifest.json
├── 04_Auditoria/               ← Audit: findings, diagnosis
├── 04_Relatorios_LGPD/         ← LGPD: relatórios gerados
└── 00_Indice_Master.xlsx       ← Índice consolidado com todos os hashes
```

---

## 17. Implementação

Ver documentos complementares:

- `docs/analysis/lgpd_module_backlog.md` — Epics e user stories
- `docs/analysis/lgpd_domain_model.md` — Entidades, campos, relacionamentos
- `docs/analysis/lgpd_mvp_decision_matrix.md` — Decisões técnicas
- `docs/analysis/lgpd_inova_questions.md` — Perguntas críticas para INOVA

---

## 18. Status e Próximos Passos

**Atual:** Design arquitetural completo (Sprint LGPD-0)

**Próximo:**
1. Validação com João (escopo, timing)
2. Respostas de INOVA (12 perguntas críticas)
3. Decisão "vai/não vai"
4. Alocação de dev + início Fase 1 (preparação)

**Decisão esperada:** Semana de 2026-05-29

---

**Preparado por:** Claude Code  
**Data:** 2026-05-05  
**Versão:** 1.0 — Design Completo  
**Status:** Pronto para Implementação
