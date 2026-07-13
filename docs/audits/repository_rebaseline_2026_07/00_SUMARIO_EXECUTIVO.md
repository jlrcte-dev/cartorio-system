# 00 — Sumário Executivo — Rebaseline do Repositório

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> Auditoria somente-leitura de `C:\Users\João\Documents\cartorio_system` (branch `main`, HEAD `6ed62cb`, 2026-05-25).
> Análise baseada em evidências: git, código, testes executados, migrations e 77 documentos.

---

## VEREDITO: **APTO COM ESTABILIZAÇÃO PRÉVIA**

O núcleo do sistema está saudável — **904 testes (903 verdes + 1 skip legítimo de plataforma em 50 s), ruff limpo, cadeia de migrations linear com head único, isolamento de módulos quase perfeito e higiene exemplar de dados sensíveis**. Não há risco crítico ativo (P0): nenhum segredo versionado, nenhum dado pessoal no git, nenhuma dívida de código grave.

O que impede a retomada imediata do roadmap funcional é a **cintura de governança**: (1) ~6 semanas de trabalho documental crítico (dossiê PROAD) vivem apenas no working tree, sem commit; (2) não existe nenhuma automação de verificação (CI); (3) os documentos guarda-chuva (`architecture.md`, `roadmap.md`, `testing.md`, índices) contradizem o código e congelaram a imagem do projeto em maio/2026. Um ciclo curto de estabilização (Grupos A e B + CI mínimo, estimável em poucas sprints pequenas) remove esses bloqueios com risco próximo de zero.

---

## 1. Estado geral

| Dimensão | Estado |
|----------|--------|
| Código (`app/`: 8 módulos ativos, ~12,9k LOC) | 🟢 maduro, isolado, testado |
| Pipeline RI (`scripts/local_tools`: 7,4k LOC, ~334 testes) | 🟡 funcional, mas fora da arquitetura declarada |
| Testes (904) / lint | 🟢 verdes, rápidos, com golden files |
| Banco/migrations (10 revisões, head único) | 🟢 disciplinado; boa preparação estrutural p/ PostgreSQL (não validada em execução real) |
| Segurança de dados (582 MB reais fora do git) | 🟢 exemplar |
| Documentação por módulo | 🟢 atual |
| Documentação guarda-chuva + índices | 🔴 defasada (maio/2026) |
| Automação/CI | 🔴 inexistente |
| Working tree | 🔴 12 docs PROAD modificados + 2 untracked sem commit desde 2026-05-25 |

## 2. Grau de confiança da análise

**Alto** para código, testes, migrations e grafo de dependências (verificados por execução e leitura direta). **Médio** para classificação individual dos 74 documentos (leitura amostral + estrutura) e para itens dependentes de contexto externo ao repositório (backup de `_local_data/`, estado da infraestrutura da serventia, propostas de sprint não versionadas — marcados como "não confirmado").

## 3. Principais avanços (evidências no doc 04)

1. Eixo regulatório completo e integrado: audit (scanner+findings+diagnosis) + lgpd + retention + compliance (4 sprints), com referências fracas testadas (ADR-002).
2. Geração documental determinística (notas/inventários): golden tests byte-a-byte, exportador ODT stdlib-only, schema pydantic de entrada.
3. Pipeline RI sanitizado com contratos anti-PII e ~334 testes.
4. Rastreabilidade de decisões: D-01..23 + ADR-001..009 + conventional commits temáticos.
5. Fundação FastAPI enxuta com DDL exclusivo do Alembic e teste de isolamento do banco de dev.

## 4. Principais fragilidades

1. Trabalho PROAD (resposta à corregedoria) não commitado há ~6 semanas — risco de perda.
2. Zero CI/automação — qualidade depende de disciplina manual em uma máquina.
3. `docs/architecture.md` descreve um sistema de ~2026-05-04 ("finance é o único módulo ativo").
4. `docs/roadmap.md` marca como "próxima" sprint concluída em maio; contagens de teste antigas em 3 docs.
5. Estado real do projeto só é reconstituível cruzando 5 roadmaps + git log + memória externa.
6. Auth multiusuário e trilha de auditoria transversal (exigências CNJ 213 declaradas "antecipadas") não iniciadas.

## 5. Top 10 dívidas técnicas (registro completo: doc 04 + CSV)

| # | ID | Dívida | Prioridade |
|---|----|--------|-----------|
| 1 | TD-05 | Trabalho PROAD não commitado (12 M + 2 ??) | P1 |
| 2 | TD-09 | Ausência total de CI | P1 |
| 3 | TD-01 | architecture.md contradiz o código | P1 |
| 4 | TD-02 | roadmap.md defasado | P1 |
| 5 | TD-16 | 5 roadmaps sem hierarquia de autoridade | P2 |
| 6 | TD-11 | testing.md declara 48 testes (reais: 904) | P2 |
| 7 | TD-06 | Pipeline RI (7,4k LOC) fora da arquitetura modular | P2 |
| 8 | TD-10 | bandit/pip-audit/gitleaks exigidos e ausentes | P2 |
| 9 | TD-04 | Índices documentais incompletos (inclui ADR-009 fora do índice) | P2 |
| 10 | TD-13 | Relatórios de sprint sem política de arquivamento | P2 |

## 6. Top 5 riscos

1. **Perda do dossiê PROAD** (working tree único + backup de `_local_data/` não confirmado).
2. **Regressão silenciosa em `main`** (sem CI; push manual sem verificação automatizada).
3. **Decisão errada por documentação defasada** (arquitetura/roadmap oficiais incorretos).
4. **Gap regulatório na vistoria CNJ 213** (sem auth, sem trilha transversal — prazo global de 24 meses corre desde a classificação).
5. **Conhecimento tácito não versionado** (propostas de sprint e estado só em memória de sessões de IA — ex.: FRACOES-1 não existe em nenhum doc do repo).

## 7. Principais inconsistências documentais

- roadmap.md × module_roadmap.md (Sprint 3 "próxima" × concluída);
- architecture.md × código (1 módulo × 8);
- testing.md × pytest (48 × 904);
- registro_imoveis.md ("pré-implementação") × 7,4k LOC + 334 testes;
- 3 referências a `docs/operations/engegraph.md` inexistente;
- CLAUDE.md §9 e docs/README.md sem os módulos notas/RI; decisions/index.md sem ADR-009.

## 8. Situação real perante o roadmap

Fundação, eixo regulatório e geração documental: **concluídos ou maduros**. Financeiro: congelado por decisão. Auth, trilha transversal, exports, protocolos: **não iniciados**. KB/IA e Document Registry: blueprints bloqueados por decisões humanas (correto). Dois eixos executados em maio/junho (notas, PROAD/RI) **não constam** do roadmap geral. Detalhe: doc 06.

## 9. Estrutura-alvo (resumo — doc 05)

Manter ~85% como está. Mudanças propostas: promover pipeline RI a `app/modules/registro_imoveis/` (DH-1), criar `docs/history/` para relatórios de época, `docs/audits/` para diagnósticos (criado nesta sprint), separar `scripts/` de ferramentas locais, ADRs de layout de módulo e da exceção `diagnosis→retention`.

## 10. Sequência recomendada (doc 07)

`REB-A0/A1` (preservar rebaseline + commit PROAD — podem compor uma única sprint de salvaguarda) → `A2` (EOL) → `D1` (CI mínimo, antecipado) → `B1..B4` (docs guarda-chuva, índices, status documental) → **aprovação do blueprint** → `C0..C2` (ADRs + movimentos; C0 antes de qualquer movimentação do pipeline RI; DH-1 permanece aberta) → `D2/D3` → `E1` (**auth multiusuário — próxima etapa funcional recomendada**) → `E2` (trilha transversal). `REB-A3` (backup _local_data) em frente operacional paralela após A1; `NOTAS-FRACOES-1` como quick win paralelo.

## 11. Decisões que dependem de aprovação humana

- **DH-1:** destino do pipeline RI (recomendação: promover a módulo).
- **DH-2:** manter/remover os 6 placeholders vazios.
- **DH-3:** estratégia para o template `.j2` espelho.
- **DH-4:** CHANGELOG.md × git log.
- **DH-5:** adotar ou abandonar mypy.
- Aprovação do roadmap reconciliado (doc 06) e do blueprint (doc 05).
- Conteúdo final dos docs PROAD antes do commit (REB-A1).
- DHP-01..10 (Knowledge Base/IA) — permanecem pendentes, sem mudança.

## 12. Itens que não puderam ser confirmados

- Existência/rotina de **backup externo** de `_local_data/` (582 MB) e do `cartorio.db` de dev.
- Divergência com `origin/main` em tempo real (nenhum `fetch` foi executado; leitura do estado local).
- Aderência fina de `docs/operations/how_to_run.md` e dos docs de infraestrutura à realidade atual (não confrontados com o ambiente).
- Status real das ações externas PROAD (envio, protocolo, prazos) — evidência apenas documental.
- Intencionalidade da ausência de router no módulo `retention` (nenhum documento a declara).
- Proposta FRACOES-1: citada como próxima sprint de notas em memória de sessão, **sem documento versionado**.

---

### Arquivos desta auditoria

`00_SUMARIO_EXECUTIVO.md` · `01_INVENTARIO_REPOSITORIO.md` · `02_DIAGNOSTICO_ARQUITETURAL.md` · `03_GOVERNANCA_DOCUMENTAL.md` · `04_REGISTRO_DIVIDA_TECNICA.md` · `05_BLUEPRINT_REPOSITORIO_ALVO.md` · `06_ROADMAP_RECONCILIADO.md` · `07_PLANO_PROXIMAS_SPRINTS.md` · `inventory_files.csv` · `technical_debt_register.csv`
