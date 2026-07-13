# 05 — Blueprint do Repositório-Alvo

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> **Proposta para aprovação humana.** Nada foi movido nesta sprint. A estrutura parte do repositório real — a maior parte permanece onde está.

---

## 1. Princípio norteador

O repositório atual está ~85% correto. O blueprint **não** propõe reorganização ampla: propõe (a) dar lugar declarado ao que cresceu sem lugar (pipeline RI, artefatos de sprint), (b) separar documentação vigente de histórica, e (c) formalizar políticas por diretório. Movimentos físicos ficam restritos ao Grupo C do plano de sprints, cada um com testes antes/depois.

## 2. Estrutura-alvo proposta

```text
cartorio-system/
├── app/                          # (inalterado) código de produção
│   ├── core/  db/  interfaces/   # fundação transversal
│   └── modules/
│       ├── finance/ audit/ lgpd/ retention/ compliance/   # (inalterados)
│       ├── notas/                                          # (inalterado)
│       └── registro_imoveis/     # NOVO (Grupo C): pipeline promovido de
│                                 # scripts/local_tools, padrão local-first
│                                 # (CLI + domain, como notas) — OU manter em
│                                 # tools/ (decisão humana DH-1)
├── alembic/                      # (inalterado) migrations
├── tests/                        # (inalterado) inclui golden/ e fixtures
├── scripts/                      # SÓ automação de desenvolvimento/repo
│   └── (gerar_relatorio_pdf.py sai daqui — ver tabela §4)
├── tools/                        # NOVO (alternativa a promover RI a módulo):
│   └── ri/                       # ferramentas locais que operam _local_data/
├── exports/                      # contratos de saída (atlas/, futuro audit/)
├── outputs/                      # (ignorado) saídas manuais de geradores
├── _local_data/                  # (ignorado) dados reais — política inalterada
├── .ai_tmp/                      # (ignorado) artefatos de sessões de IA
├── docs/
│   ├── README.md                 # índice mestre ÚNICO (completo)
│   ├── architecture.md           # reescrito; fonte autoritativa de arquitetura
│   ├── roadmap.md                # índice mestre de roadmaps + estado real
│   ├── decisions/                # ADRs + D-XX (inalterado; índice completo)
│   ├── modules/                  # 1 doc vigente por módulo (inalterado)
│   ├── operations/               # setup, dados locais, engegraph (recriado)
│   ├── quality/                  # testing.md reescrito, risk model
│   ├── regulatory/               # cnj_213 (inalterado)
│   ├── proad/                    # dossiê PROAD (inalterado; commitado!)
│   ├── infrastructure/           # (inalterado)
│   ├── readiness/                # (inalterado)
│   ├── knowledge_base/           # blueprints IA (inalterado; status: proposto)
│   ├── document_registry/        # blueprints (inalterado; status: proposto)
│   ├── audits/                   # NOVO: auditorias de repositório (esta)
│   └── history/                  # NOVO: relatórios de época com banner de status
│       ├── analysis/             # ← docs/analysis (relatórios sprint LGPD)
│       ├── ai/                   # ← docs/ai (investigação AI-LEGAL-0)
│       └── reports/              # ← docs/reports (relatório diretoria + gerador)
└── (raiz)                        # README, CLAUDE.md, CONFIGURATION, pyproject
```

## 3. Política por diretório

| Diretório | Finalidade | Permitido | Proibido | Responsável conceitual | Versionamento |
|-----------|-----------|-----------|----------|------------------------|---------------|
| `app/` | Código de produção | Módulos autocontidos, padrão registrado em ADR | Dados reais, artefatos gerados, docs operacionais | Arquitetura | Total |
| `app/modules/registro_imoveis/` (se DH-1=promover) | Pipeline RI local-first | domain/application/interfaces(CLI); contratos anti-PII | Persistir PII; caminhos absolutos | Módulo RI | Total (código apenas) |
| `tools/` (se DH-1=manter fora) | Ferramentas locais sobre `_local_data/` | CLIs standalone testadas | Import de `app` sem decisão; outputs versionados | Operação | Código sim; saídas nunca |
| `scripts/` | Automação do repositório (dev) | Helpers de build/CI/repo | Lógica de negócio; geradores one-off de sprint | DX | Total |
| `tests/` | Testes + golden + fixtures | Sintéticos sem PII | Dados reais | Qualidade | Total |
| `alembic/` | Migrations | Revisões lineares reversíveis | DDL fora daqui | Banco | Total |
| `exports/` | Contratos de saída estruturada | `.gitkeep` + especificações | Conteúdo gerado | Integrações | Só estrutura |
| `outputs/`, `.ai_tmp/`, `_local_data/` | Saídas manuais / temp IA / dados reais | — | Entrar no git | Operação | **Nunca** (já ignorados) |
| `docs/` (vigentes) | Fonte autoritativa por tema | 1 doc vigente por tema, com status | Fotografias de época sem banner | Governança documental | Total |
| `docs/history/` | Registro histórico imutável | Relatórios de sprint/época com banner `status: histórico` | Edição posterior (exceto banner) | Governança documental | Total |
| `docs/audits/` | Auditorias de repositório | Diagnósticos datados (como este) | Mutação de auditorias passadas | Governança | Total |

## 4. Tabela de migração proposta (nada executado)

| Origem atual | Destino sugerido | Motivo | Risco | Dependências | Validação necessária | Sprint | Reversível |
|--------------|------------------|--------|-------|--------------|----------------------|--------|-----------|
| `scripts/local_tools/*.py` (7 arquivos) | `app/modules/registro_imoveis/` **ou** `tools/ri/` | Dar lugar arquitetural ao maior bolsão de lógica (TD-06) | Médio (imports dos 6 arquivos de teste mudam) | DH-1 decidida; ADR de layout | `pytest` antes/depois (foco `tests/test_ri_*`); `ruff` | REB-C1 | Sim (git mv) |
| `scripts/gerar_relatorio_pdf.py` | `docs/history/reports/tooling/` (junto do relatório que gera) | Gerador one-off de artefato de sprint (TD-14) | Baixo (standalone, sem imports de app) | nenhuma | executar `--help` do script após mover | REB-C2 | Sim |
| `docs/analysis/` (6 docs) | `docs/history/analysis/` | Relatórios de época LGPD (TD-13) | Baixo (só links) | REB-B4 (convenção de status) | grep de links internos | REB-C2 | Sim |
| `docs/ai/AI_LEGAL_TOOLS_INVESTIGATION.md` | `docs/history/ai/` | Relatório de investigação datado | Baixo | REB-B4 | grep de links | REB-C2 | Sim |
| `docs/reports/*` (+ `generated/relatorio_pdf.css`) | `docs/history/reports/` | Relatório à diretoria é fotografia de época; CSS é insumo do gerador | Baixo | REB-B4 | grep de links | REB-C2 | Sim |
| `docs/proad/` | **permanece** | Dossiê ativo até encerramento do PROAD; mover depois para `history/` | — | encerramento do processo | — | futura | — |
| `app/modules/{clients,documents,exports,protocols,reports,tasks}/` | remover **ou** manter conforme roadmap reconciliado aprovado | Placeholders vazios (TD-07) | Baixo (verificar ausência de imports — confirmada) | 06_ROADMAP aprovado | `pytest` + grep imports | REB-C3 (opcional) | Sim |
| `docs/operations/engegraph.md` | **criar** (conteúdo resgatado de architecture.md §Coexistência + memória do diagnóstico de maio) | 3 referências quebradas (TD-03) | Baixo | REB-B1 | links resolvem | REB-B1 | Sim |
| `apresentacao_executiva_..._mvp.html` (raiz, ignorado) | `_local_data/` ou `outputs/` | Artefato gerado solto na raiz | Nulo (não versionado) | nenhuma | — | REB-A2 | Sim |

## 5. Decisões humanas necessárias antes do Grupo C

| ID | Decisão | Opções | Recomendação da auditoria |
|----|---------|--------|---------------------------|
| **DH-1** | Destino do pipeline RI | (a) promover a `app/modules/registro_imoveis/`; (b) formalizar `tools/ri/` | **(a)** — já há doc de módulo reservando o nome, testes no padrão do repo e precedente local-first (`notas`); ADR-003/blueprint já tratam o domínio |
| **DH-2** | Placeholders vazios | (a) remover os 6; (b) manter os que o roadmap reconciliado confirmar | **(b)** — remover apenas os sem previsão (avaliar após aprovação do 06) |
| **DH-3** | Template `.j2` espelho | (a) teste de sincronia renderer↔template; (b) remover espelho; (c) promover a fonte | **(a)** — menor mudança, preserva a decisão da sprint NOTAS-3 |
| **DH-4** | Changelog | (a) criar CHANGELOG.md; (b) aceitar git log como registro | **(b)** com commits disciplinados (padrão atual já é bom) |
| **DH-5** | mypy | (a) adotar e configurar; (b) remover menções | decisão de custo/benefício do mantenedor; a auditoria apenas registra a inconsistência atual |
