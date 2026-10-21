# Roadmap

> **Este é o ROADMAP GERAL AUTORITATIVO do Cartório System.**
>
> Os roadmaps por domínio listados abaixo são **subordinados** a este documento:
> detalham a execução dentro de sua área, mas **não substituem** o roadmap geral
> nem definem a prioridade do projeto. Em caso de divergência entre este
> documento e um roadmap de domínio, **este prevalece** quanto à prioridade; o
> roadmap de domínio prevalece quanto ao detalhe interno da sua área.
>
> | Roadmap subordinado | Escopo |
> |---|---|
> | [`audit/module_roadmap.md`](audit/module_roadmap.md) | 12 fases do módulo de auditoria |
> | [`regulatory/cnj_213/roadmap.md`](regulatory/cnj_213/roadmap.md) | Adequação ao Provimento CNJ 213/2026 (Classe 3) |
> | [`infrastructure/infrastructure_roadmap.md`](infrastructure/infrastructure_roadmap.md) | VMs, VLANs, backup e migração de infraestrutura |
> | [`knowledge_base/IMPLEMENTATION_ROADMAP.md`](knowledge_base/IMPLEMENTATION_ROADMAP.md) | Base de conhecimento normativa (bloqueado — sem código) |
> | [`audits/repository_rebaseline_2026_07/06_ROADMAP_RECONCILIADO.md`](audits/repository_rebaseline_2026_07/06_ROADMAP_RECONCILIADO.md) | Proposta de reconciliação de julho/2026 — **não aprovada** |

**Baseline factual deste documento:** 2026-09-03, `main`, após a sprint
`CARTORIO-SYSTEM-ENGINEERING-STABILIZATION-1`.

---

## 1. Estado atual em uma tabela

| Módulo | Estado | Interface | Uso real observado |
|---|---|---|---|
| `notas/inventarios` | Maduro | CLI | **Sim** — 6 casos reais entre 2026-05-23 e 2026-08-29 |
| `audit/scanner` | Maduro | CLI | Sim — execução validada em ambiente real |
| `audit/diagnosis` | Maduro | CLI | Sim — regras calibradas após execução real |
| `audit/findings` | Funcional | REST | Não |
| `compliance` | Funcional | REST | Não — seed da Matriz INOVA ainda não aplicado |
| `lgpd` | Funcional | REST | Parcial — 25 ações importadas do plano INOVA |
| `retention` | Parcial | sem router | Não — tabela de regras vazia; TEMP-* inativos |
| `finance` | Funcional, congelado | REST | Não — backlog futuro por decisão |
| Pipeline RI (`scripts/local_tools/`) | Funcional, fora de `app/` | CLI | Sim — base do dossiê PROAD/IERI |
| Autenticação, trilha transversal | Não iniciados | — | — |
| `drive_capture` (Drive do cartório, somente leitura) | Implementado; acesso real validado em smoke local de uma fonte piloto (20/10/2026) — ADR-011 *Proposto* | CLI manual | Não |
| `services_snapshot` (retrato de serviços da planilha piloto) | Atualização manual local; setores, status e indicadores de datas agregados (formato local 1.1) | CLI manual | Não |
| Knowledge Base / IA, Document Registry, Atlas | Blueprint apenas | — | — |

Diagnóstico completo e evidências:
[`reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md`](reports/RELATORIO_CARTORIO_SYSTEM_STRATEGIC_REBASELINE_2026_1.md).

---

## 2. Horizontes aprovados

Apenas três horizontes são mantidos aqui. Planejamento detalhado de longo prazo
é deliberadamente evitado — ele se desatualiza mais rápido do que é revisado, e
foi exatamente o que aconteceu com a versão anterior deste documento.

### HORIZONTE A — Estabilização ✅ concluído

Sprint `CARTORIO-SYSTEM-ENGINEERING-STABILIZATION-1` (2026-09-03):

- `ruff format` adotado como gate oficial; 25 arquivos alinhados.
- PyYAML declarada como dependência de runtime (era importada sem declaração).
- `Base.metadata` alinhada à unicidade criada pelas migrations — `alembic check`
  verde, sem migration nova.
- CI mínimo em `.github/workflows/ci.yml`: formatação, lint, testes e migrations
  em banco temporário.
- Documentos guarda-chuva reconciliados com o código.

### HORIZONTE B — Evolução de valor em `notas/inventarios` ◧ em andamento

Frente escolhida por ser a única com evidência de uso real repetido. Substitui
trabalho manual **observado**, não hipotético:

- ✅ **Precisão de percentual e fração ideal** — concluído em 2026-09-03 pela
  sprint `NOTAS-INVENTARIO-FRACOES-1` ([ADR-010](decisions/ADR-010-inventory-fraction-percentage-rendering.md)).
  `3,125%` deixou de ser truncado para `3,12%`; a fração ideal passou a ser
  aceita, validada e exibida nos artefatos técnicos. Um ponto segue aberto: a
  **redação da fração no texto da escritura** depende de definição do tabelião —
  os artefatos do caso real mostram que a serventia redigiu por percentual, e o
  gerador não inventa redação.
- ◻ **Saída fragmentada de cláusulas** (§§ 10 e 11) — hoje recortadas à mão em
  todos os casos recentes.
- ◻ **Saída em texto limpo para o Engegraph** — hoje produzida manualmente.

Frente operacional paralela (não compete por código com a acima):
**ativação do eixo regulatório** — aplicar os seeds de `compliance` e
`retention`, promover achados reais a `AuditFinding` e reexecutar
scanner + diagnosis sobre o acervo atual.

### HORIZONTE C — Evolução estrutural ◻ futuro

Depende de decisão humana explícita, item a item:

- Ingestão estruturada do demonstrativo de ITCD (hoje transcrito à mão).
- Destino do pipeline RI: promoção a `app/modules/registro_imoveis/` ou
  formalização como camada de ferramentas (**DH-1, em aberto**).
- Ciclo recorrente IERI-e / SIG-RI (Provimento CNJ 195/2025).
- Autenticação multiusuário e trilha de auditoria transversal — exigências
  estruturais do Provimento CNJ 213/2026.
- Doação como segunda família de atos notariais (1 caso real observado).

**Permanecem fora de horizonte, corretamente bloqueados:** Knowledge Base / IA
(depende das decisões DHP-01..10), Document Registry, integração Atlas e as
Etapas 2–7 do módulo financeiro.

---

## 3. Etapas concluídas

### Fundação

| Etapa | Entrega |
|---|---|
| Etapa 0 | Estrutura `app/{core,db,modules,interfaces}`, FastAPI com lifespan, settings via pydantic-settings, logging, handlers de erro, `GET /api/v1/health` |
| Etapa 0.1 | Pin de Python 3.12 (`requires-python`, `.python-version`) |
| Etapa 1 | Finance Core v1: `FinancialEntry`, `FinancialCategory`, CRUD `/finance/entries`, `GET /monthly-summary` |
| Etapa 1.1 | Finance hardening: `EntryDirection`, `EntrySource`, `created_by`/`updated_by`, regra status × tipo, migration reversível com backfill |
| Etapa 1.2 | Hardening pós-auditoria: `create_all` removido do lifespan (Alembic é a única fonte de DDL), handler 500 loga traceback, `CheckConstraint` GLOB removida, imutabilidade de `entry_type` e `competence_month`, teste de isolamento do banco |

### Módulo de auditoria

| Sprint | Estado | Entrega |
|---|---|---|
| Etapa A | ✅ | Documentação e posicionamento do módulo; roadmap CNJ 213 |
| Sprint 1 — Scanner read-only | ✅ | `app/modules/audit/scanner/`; **validado em ambiente real**; gera `file_inventory.json/csv`, `scan_summary.md`, `scan_manifest.json` com SHA-256 |
| Sprint 2 — AuditFinding CRUD | ✅ | 6 endpoints; sem `DELETE` físico; histórico de status |
| Sprint 2.5 — POP read-only | ✅ | Procedimento operacional formalizado |
| Sprint 3 + 3.5 — DocumentDiagnosis | ✅ | 7 regras DIAG-*; entrada é o artefato do scanner, não o servidor (decisão D-23) |
| Sprint 3.6 — Calibração pós-real | ✅ | Regras ajustadas **após** confronto com o resultado da execução real |

> Correção de registro: até 2026-09-02 este documento marcava a Sprint 3 como
> "🟡 próxima". Ela foi concluída em 2026-05-04 (commits `2e329e0` e `441a33e`).

### Eixo regulatório e documental

| Sprint | Estado | Entrega |
|---|---|---|
| LGPD-1 | ✅ | Módulo de ações do plano LGPD; import CSV INOVA; histórico append-only |
| retention-1A / 1B | ✅ | Regras de temporalidade + integração com DocumentDiagnosis (TEMP-*) |
| Compliance-1 a 4 | ✅ | Matriz INOVA V1 read-only, `ComplianceEvidence`, `RequirementFindingLink`, status indicativo com histórico |
| PROAD / IERI | ✅ | Base documental de resposta à Corregedoria (Provimento CNJ 195/2025) |

### Atos notariais

| Sprint | Estado | Entrega |
|---|---|---|
| NOTAS-INVENTARIO 1–3 | ✅ | Domínio, calculator (`Decimal`, `ROUND_HALF_EVEN`), validator, minuta-base em Markdown com §§ 1–20 |
| NOTAS-INVENTARIO-4 | ✅ | Schema Pydantic v2 (`extra="forbid"`, `SafeDecimal`) + golden files byte a byte |
| NOTAS-INVENTARIO-5 / 5B | ✅ | Exportador ODT sem dependência externa; cláusulas como corpo, não como títulos |
| ADR-009 | ✅ | Política de centavos: o sistema alerta e **não** corrige silenciosamente |

> Registro de honestidade documental: as sprints de `notas/inventarios` e o
> pipeline RI foram executadas em maio–junho/2026 **sem constar deste roadmap**.
> Passam a constar a partir desta revisão.

### Preparação documental sem código

A sprint **KNOWLEDGE-BASE-0** (2026-05-23) entregou apenas documentação
conceitual. Não há código, banco, migration, endpoint, embeddings, RAG, MCP,
agentes nem integração com IA externa. A implementação depende de aprovação
humana formal (DHP-01..10) e das ADRs 004–008, hoje em estado *Proposto*.
Ver [`knowledge_base/`](knowledge_base/).

---

## 4. Backlog futuro — módulo financeiro

O módulo financeiro é preservado integralmente e **não deve ser expandido
agora**. Estas etapas voltam ao roadmap ativo quando houver uso operacional real
que as justifique.

- **Etapa 2 — Monthly Closing:** fechamento mensal como artefato auditável, com
  snapshot de `MonthlySummary`, lock de mês fechado e distinção entre resultado
  realizado e projetado.
- **Etapa 3 — Obligations / Reports:** `ObligationType` (CNJ, SEDI, ISS, CRC,
  ONR…), ocorrências mensais com `due_date`, vínculo com `FinancialEntry`.
- **Etapa 4 — Exports:** CSV/JSON do mês, resumo contábil, estrutura para o
  Atlas em `exports/atlas/`.
- **Etapas 5–7:** anexos e comprovantes, importação de planilhas históricas
  (2016–2026), CRUD e seed de categorias financeiras.

---

## 5. Princípios de evolução

1. Adicionar módulos sem mexer nos existentes — `app/modules/<novo>/`.
2. Toda regra cruzada nova mora no `rules.py` do módulo.
3. Toda mudança de schema passa por migration Alembic reversível, com backfill
   explícito quando colunas `NOT NULL` forem adicionadas.
4. Etapa nova só começa quando a anterior está com **CI verde** — formatação,
   lint, testes e migrations.
5. **Read-only first.** O scanner nunca modifica arquivos do servidor analisado.
6. **Uso prático ao final de cada sprint.** Nenhuma sprint é preparatória sem
   entregável.
7. **Nenhuma sprint entra no repositório sem constar deste roadmap.** A ausência
   de `notas/inventarios` e do pipeline RI nas versões anteriores tornou o
   estado do projeto reconstituível apenas por arqueologia de commits.
