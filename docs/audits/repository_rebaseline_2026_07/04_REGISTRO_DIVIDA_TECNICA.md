# 04 — Registro de Dívida Técnica + Pontos Positivos/Negativos + Matriz de Maturidade

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> Registro completo em [`technical_debt_register.csv`](technical_debt_register.csv) (22 itens).

---

## 1. Sumário do registro de dívidas

| Prioridade | Itens | IDs |
|-----------|-------|-----|
| **P0** (risco imediato) | **0** | — |
| **P1** (bloqueia evolução segura) | 4 | TD-05 (trabalho PROAD não commitado), TD-09 (sem CI), TD-01 (architecture.md contradiz código), TD-02 (roadmap.md defasado) |
| **P2** | 10 | TD-03, TD-04, TD-06, TD-10, TD-11, TD-13, TD-16, TD-18*, TD-19*, TD-22* |
| **P3** | 5 | TD-08, TD-12, TD-14, TD-15, TD-17 |
| **P4** | 3 | TD-07*, TD-20, TD-21 |

\* Classificação diferenciada: TD-07 é **decisão consciente** documentada; TD-18/TD-19 são **funcionalidades não iniciadas** (pertencem ao roadmap, não à dívida de código); TD-22 é **risco operacional externo ao repositório** (infraestrutura da serventia), registrado com a dependência mas mantido em categoria própria.

**Leitura essencial:** não há dívida de *código* grave. As dívidas P1 são de **versionamento (1)**, **automação (1)** e **documentação (2)**. O padrão dominante é: o código evoluiu com disciplina; os documentos guarda-chuva e a automação não acompanharam.

---

## 2. Pontos positivos (com evidência)

| # | Ponto | Evidência | Impacto | Confiança |
|---|-------|-----------|---------|-----------|
| 1 | **Isolamento de módulos quase perfeito.** Grafo completo de imports mostra 1 única dependência entre módulos (`audit.diagnosis→retention`); eixo compliance usa referência fraca (`source_module/source_type/source_ref`) conforme ADR-002, com teste dedicado | mapa de imports; `tests/test_compliance_isolation.py`; ADR-002 | Evolução independente por módulo; refatorações locais seguras | Alta |
| 2 | **Suíte de testes robusta e rápida.** 904 coletados, 903 passando + 1 skip legítimo (chmod no Windows), em 50 s; golden tests byte-a-byte com `.gitattributes eol=lf`; teste que garante que pytest não toca `cartorio.db` | execução `pytest -q`; `tests/test_isolation.py`; `.gitattributes` | Regressões detectáveis em <1 min; contratos de output documental protegidos | Alta |
| 3 | **Higiene exemplar de dados sensíveis.** 582 MB/1.944 arquivos reais em `_local_data/` fora do git; `.gitignore` com padrões específicos anti-PII (`*_matriculas*`, `*_ieri*`, exports); zero credenciais versionadas; pipeline RI com contratos anti-PII testados | `.gitignore`; `git status --ignored`; `docs/operations/local_data_policy.md` | Risco LGPD/regulatório de vazamento via repositório ≈ zero | Alta |
| 4 | **Disciplina de migrations.** Cadeia Alembic linear (10 revisões, head único `f4a5b6c7d8e9`), `env.py` injeta URL das settings, DDL exclusivo do Alembic (lifespan documenta e cumpre), backfill explícito em NOT NULL (D-17), `Numeric(14,2)` para dinheiro | `alembic/versions/`; `app/main.py:22-23`; migrations de hardening | Boa preparação estrutural para futura adoção de PostgreSQL (compatibilidade ainda não validada em execução real) | Alta |
| 5 | **Rastreabilidade de decisões acima da média.** 23 decisões técnicas (D-01..23) + 9 ADRs indexados + conventional commits pequenos e temáticos (1 sprint = 1 commit) | `docs/decisions/`; `git log --oneline` | Arqueologia de "por quê" barata; onboarding de decisões viável | Alta |
| 6 | **Geração documental determinística sem dependência externa.** Exportador ODT construído só com stdlib (zipfile+xml), meta sem datas para determinismo; renderer com golden files | `odt_exporter.py` (docstring + código); `tests/test_notas_inventarios_odt_exporter.py` | Minutas reproduzíveis e auditáveis | Alta |
| 7 | **Regras de negócio fora dos endpoints.** Padrão `rules.py` + `service.py` respeitado em todos os módulos REST; routers só orquestram | leitura de `router.py`/`service.py` de finance, lgpd, compliance, findings | Testabilidade sem HTTP; regra única | Alta |

## 3. Pontos negativos (com evidência)

| # | Ponto | Evidência | Impacto | Confiança |
|---|-------|-----------|---------|-----------|
| 1 | **Trabalho crítico não commitado por ~6 semanas.** HEAD de 2026-05-25; 12 docs PROAD (+328/−415) + 2 untracked no working tree | `git status`; `git log -1` | Perda potencial de material de resposta à corregedoria | Alta |
| 2 | **Zero automação de verificação.** Sem CI, sem hooks, sem coverage medido; bandit/pip-audit/gitleaks exigidos pelo CLAUDE.md e ausentes do ambiente | inexistência de `.github/`; `pip list` | Qualidade depende 100% de disciplina manual local | Alta |
| 3 | **Docs guarda-chuva contradizem o código.** architecture.md ("finance é o único módulo ativo"), roadmap.md (Sprint 3 "próxima"), testing.md ("48 testes") | citações nos próprios arquivos vs código/pytest | Fonte oficial induz a erro; imagem do projeto congelada em maio | Alta |
| 4 | **Maior bolsão de lógica fora da arquitetura.** Pipeline RI: 7.366 LOC em `scripts/local_tools/` vs 4.155 do maior módulo de `app/` | contagem LOC; `docs/modules/registro_imoveis.md` ("pré-implementação") | Código de produção sem lugar declarado na arquitetura | Alta |
| 5 | **Estado real do projeto não reconstituível por documentos.** É necessário cruzar 5 roadmaps + git log + memória externa (sessões de IA) para saber o que existe | TD-16; esta própria auditoria | Dependência de conhecimento tácito; risco de bus factor = 1 | Alta |
| 6 | **Sem trilha de auditoria transversal nem auth** — exigências estruturais CNJ 213 apontadas como "antecipadas" no próprio roadmap, ainda não iniciadas | `docs/roadmap.md` §eixo regulatório; código | Gap regulatório se a vistoria ocorrer antes da implementação | Alta |

---

## 4. Matriz de maturidade (0–4)

| # | Dimensão | Nota | Evidências | Lacuna | Condição para subir 1 nível |
|---|----------|------|-----------|--------|------------------------------|
| 1 | Organização do repositório | **3** | Separação app/docs/tests/scripts limpa; zero binários; ignores corretos | Pipeline RI sem lugar; artefatos one-off em scripts/ | Executar Grupo C (blueprint aprovado) |
| 2 | Clareza arquitetural | **2** | Código claro e consistente | Doc autoritativa contradiz o real | Reescrever architecture.md (REB-B1) |
| 3 | Separação de módulos | **4** | 1 import cruzado em ~150 arquivos; referências fracas testadas | Exceção diagnosis→retention sem ADR | Registrar ADR da exceção |
| 4 | Domínio e regras de negócio | **3** | rules.py por módulo; domain models puros em notas; Decimal para dinheiro | Fórmulas de frações truncadas (rota manual §15 notas) | FRACOES-1 + ADR de layout |
| 5 | Testes | **3** | 904 testes/50s; golden; isolamento de banco | Sem coverage medido; sem CI executando | CI mínimo + relatório de cobertura |
| 6 | Banco e migrations | **3** | Cadeia linear; head único; env.py por settings; boa preparação estrutural para PostgreSQL | Compatibilidade nunca validada em execução real contra PostgreSQL | Job de CI com Postgres (futuro) |
| 7 | Documentação técnica | **2** | Docs por módulo bons e atuais | Guarda-chuva defasados; índices incompletos | Grupo B completo |
| 8 | Governança documental | **2** | Convenção de pastas por domínio; ADRs indexados | Sem status de documento; históricos indistinguíveis; PROAD não commitado | REB-A1 + REB-B4 |
| 9 | Segurança | **2** | Higiene de segredos/PII exemplar; read-only policy | Sem auth; sem scanners de segurança instalados | REB-D2 (ferramentas) e depois auth |
| 10 | Auditabilidade | **3** | Historicos append-only (lgpd, compliance status); findings sem DELETE; manifestos com hash | Sem trilha transversal de mutações | Módulo de audit trail (REB-E2) |
| 11 | Observabilidade | **1** | Logging estruturado stdout; handler 500 com traceback | Sem métricas, sem agregação | Definir mínimo quando houver operação multiusuário |
| 12 | Automação e CI | **0** | Inexistente | Tudo manual | REB-D1: pytest+ruff em GitHub Actions |
| 13 | Experiência de desenvolvimento | **3** | venv pinado 3.12; suíte rápida; ruff configurado; how_to_run.md | Sem task runner; mypy prometido e ausente | Makefile/justfile + decisão sobre mypy |
| 14 | Preparação para operação | **2** | deployment_and_operation.md (audit); CLIs documentadas | Sem auth, sem backup de _local_data governado, monousuário | REB-A3 + auth |
| 15 | Aderência ao roadmap | **2** | Eixos audit/compliance/cnj bem sincronizados | Roadmap geral defasado; 5 roadmaps sem hierarquia | REB-B2 (roadmap reconciliado aprovado) |
| 16 | Preparação para integração futura | **2** | Independência do Atlas absoluta; exports/atlas/ reservado | Nenhum contrato de export implementado (Etapa 4 finance em backlog) | Implementar primeiro export com checksum/timestamp |

**Média simples: 2,3** — projeto **funcional e consistente no núcleo (código/testes/banco), frágil na cintura de governança (docs guarda-chuva, CI, versionamento do trabalho em curso)**.
