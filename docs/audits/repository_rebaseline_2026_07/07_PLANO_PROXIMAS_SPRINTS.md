# 07 — Plano das Próximas Sprints

> Sprint **CARTORIO-REPOSITORY-REBASELINE-1** — 2026-07-09.
> Sequência incremental derivada das evidências. Cada sprint é pequena, com objetivo único e rollback trivial. **Proposta para aprovação.**

---

## Grupo A — Estabilização (imediato)

### REB-A0 — Preservar o rebaseline
- **Objetivo único:** versionar o pacote desta auditoria (`docs/audits/repository_rebaseline_2026_07/`, 10 arquivos) em commit próprio.
- **Justificativa:** o diagnóstico aprovado é a referência de todas as sprints seguintes; enquanto untracked, está sujeito a perda.
- **Escopo permitido:** `git add` explícito do diretório da auditoria; nenhuma edição além de correções factuais autorizadas.
- **Aceite:** commit contendo exatamente os 10 arquivos; `pytest`/`ruff` verdes antes.
- **Risco/rollback:** nulo / `git revert`.
- **Nota:** REB-A0 e REB-A1 podem compor uma única sprint de salvaguarda (executadas em commits separados).

### REB-A1 — Salvaguardar o trabalho PROAD pendente
- **Objetivo único:** commitar o estado final dos 12 docs PROAD modificados + decidir destino dos 2 untracked.
- **Justificativa:** ~6 semanas de trabalho crítico (resposta à corregedoria) só existem no working tree (TD-05).
- **Escopo permitido:** `git add/commit` de `docs/proad/**` e `docs/modules/notas_inventarios/POP_*.md` (após revisão humana do conteúdo); nenhuma edição de conteúdo além de correções triviais aprovadas.
- **Contratos protegidos:** nenhum código tocado.
- **Dependências:** revisão humana do texto (são minutas oficiais).
- **Critérios de aceite:** `git status` limpo em `docs/proad/`; mensagem de commit descrevendo o marco (harmonização final + relatório parcial 11).
- **Testes:** `pytest` (sanidade, nada deve mudar).
- **Risco/rollback:** nulo / `git revert`.
- **Resultado esperado:** trabalho crítico protegido pelo histórico.

### REB-A2 — Higiene de EOL e raiz
- **Objetivo único:** política de EOL declarada (`.gitattributes` com `* text=auto` + exceções) e remoção do artefato HTML da raiz para pasta ignorada.
- **Justificativa:** TD-15; warnings LF→CRLF em todos os diffs de docs.
- **Escopo:** `.gitattributes`; mover `apresentacao_executiva_*.html` (não versionado) para `outputs/` ou `_local_data/`.
- **Contratos protegidos:** `tests/golden/**` **continua eol=lf** — golden tests não podem quebrar.
- **Dependências:** REB-A1 commitado antes (não misturar).
- **Aceite:** `git diff` sem warnings de EOL; `pytest` verde (inclui golden).
- **Risco/rollback:** baixo / reverter `.gitattributes`.

### REB-A3 — Governança do backup de `_local_data/` (frente operacional paralela)
- **Objetivo único:** documentar (em `docs/operations/local_data_policy.md` ou doc novo) responsável, destino e frequência de backup dos 582 MB de dados reais.
- **Posição na sequência:** paralela — depende de confirmação externa (gestor/infraestrutura da serventia) e não bloqueia as demais sprints; pode ocorrer a qualquer momento após REB-A1.
- **Justificativa:** TD-22 — evidências PROAD/RI dependem de disco local único (não confirmado se há backup externo).
- **Escopo:** apenas documentação + verificação factual com o gestor.
- **Aceite:** política escrita com responsável nomeado.
- **Risco:** nulo (doc). Registro apenas — execução do backup é operacional, fora do repo.

## Grupo B — Organização documental

### REB-B1 — Reescrever `docs/architecture.md`
- **Objetivo único:** arquitetura documentada = arquitetura real (base: `02_DIAGNOSTICO_ARQUITETURAL.md`).
- **Escopo:** `docs/architecture.md`; recriar `docs/operations/engegraph.md` (ou redirecionar as 3 referências — TD-01, TD-03).
- **Aceite:** zero referências quebradas (verificar por grep); módulos listados = módulos existentes; diagrama Mermaid incluído.
- **Risco/rollback:** nulo / revert.

### REB-B2 — Roadmap mestre reconciliado
- **Objetivo único:** `docs/roadmap.md` vira índice mestre: estado real por eixo + hierarquia declarada dos 5 roadmaps (TD-02, TD-16), incorporando o `06_ROADMAP_RECONCILIADO.md` aprovado.
- **Escopo:** `docs/roadmap.md`; marcador da Sprint 3.6 em `module_roadmap.md`.
- **Dependências:** aprovação humana do doc 06.
- **Aceite:** nenhum item "próxima" que já esteja concluído; links para os 4 roadmaps de eixo com papel declarado.

### REB-B3 — Índices e docs rápidos
- **Objetivo único:** atualizar `docs/README.md` (seções notas/RI/proad/ai/audits + ADRs 004–009), `decisions/index.md` (+ADR-009), `CLAUDE.md` §9 (+notas, +RI), `docs/quality/testing.md` (904 testes, golden, layout atual) — TD-04, TD-11.
- **Aceite:** todo doc versionado alcançável a partir de `docs/README.md`; contagens corretas na data do commit.

### REB-B4 — Convenção de status documental + arquivamento
- **Objetivo único:** frontmatter mínimo (`status`, `data`, `dono`) definido em 1 doc de política; aplicado aos históricos (`analysis/`, `ai/`, `reports/`) com banner "fotografia de época" (TD-13). *Movimentação física fica para REB-C2.*
- **Aceite:** política escrita; históricos marcados.

## Grupo C — Organização arquitetural (somente após aprovação do blueprint — doc 05)

### REB-C0 — ADRs de fronteira
- **Objetivo único:** 2 ADRs: (1) padrão de layout de módulo flat × hexagonal e quando usar cada (TD-08); (2) legitimação (ou plano de remoção) da dependência `audit.diagnosis→retention` (TD-17). Registrar decisões DH-1..DH-5 do doc 05.
- **Aceite:** ADRs aceitos e indexados.

### REB-C1 — Dar lugar ao pipeline RI (executa DH-1)
- **Objetivo único:** mover `scripts/local_tools/` → `app/modules/registro_imoveis/` (recomendado) ou `tools/ri/`, atualizando imports dos 6 arquivos de teste.
- **Contratos protegidos:** contratos anti-PII dos CLIs; nomes/formatos de saída.
- **Aceite:** `pytest` integral verde antes e depois (mesmos 904); `ruff` limpo; doc `registro_imoveis.md` reescrito sem "pré-implementação".
- **Risco/rollback:** médio / `git revert` (mudança mecânica, sem lógica).

### REB-C2 — Arquivar artefatos de sprint
- **Objetivo único:** mover `docs/analysis/`, `docs/ai/`, `docs/reports/` (+CSS+gerador de PDF) para `docs/history/**` conforme tabela do doc 05; corrigir links.
- **Aceite:** grep de links internos sem órfãos; `pytest` verde (gerador não é importado por nada).

### REB-C3 (opcional) — Placeholders
- Remover os pacotes vazios sem previsão no roadmap aprovado (DH-2). Aceite: grep de imports vazio + `pytest`.

## Grupo D — Dívidas técnicas prioritárias

### REB-D1 — CI mínimo (antecipada: executar logo após REB-A2, antes do Grupo B)
- **Objetivo único:** GitHub Actions com `pytest` + `ruff check` em push/PR para `main` (TD-09).
- **Motivo da antecipação:** as sprints B/C geram commits frequentes; tê-los verificados automaticamente desde cedo custa pouco e protege todo o restante da sequência.
- **Aceite:** pipeline verde no commit da própria sprint; badge opcional no README.
- **Risco:** nulo para o código; segredo nenhum necessário (SQLite in-memory).

### REB-D2 — Ferramentas de segurança
- **Objetivo único:** adicionar `bandit`, `pip-audit`, `gitleaks` ao CI (job separado, pode começar como não-bloqueante) e ao grupo dev do pyproject (TD-10); decidir mypy (DH-5).
- **Aceite:** execução documentada; findings triados (não corrigir nesta sprint).

### REB-D3 — Sincronia renderer ↔ template espelho
- **Objetivo único:** teste automático que falha se `renderer.py` e o `.j2` divergirem (ou execução da alternativa escolhida em DH-3) (TD-12).
- **Aceite:** teste no CI; golden inalterados.

## Grupo E — Retomada funcional (após A, B e D1)

### REB-E1 — Autenticação multiusuário mínima ⭐ próxima etapa funcional recomendada
- **Objetivo:** identidade real substituindo `created_by="gestor"` — pré-requisito CNJ 213 e da trilha transversal.
- **Dependências:** estabilização (A/B) + CI (D1); ADR de abordagem (sessão × token; escopo mínimo).
- **Risco:** médio (toca todos os routers) — por isso exige CI antes.

### REB-E2 — Trilha de auditoria transversal
- Após E1 (precisa de identidade). Requisito estrutural CNJ 213 (retenção ≥ 5 anos).

### NOTAS-FRACOES-1 — Quick win paralelo
- Elimina rota manual de frações/percentuais da minuta (truncamento 3,125%→3,12%). Pode rodar em paralelo a REB-B* por ser autocontida e protegida por golden tests.

---

## Ordem recomendada (resumo)

```
REB-A0/A1 → REB-A2 → REB-D1 → REB-B1 → REB-B2 → REB-B3 → REB-B4
        → REB-C0 → REB-C1 → REB-C2 → REB-D2 → REB-D3 → REB-E1 → REB-E2

REB-A3 em paralelo após REB-A1 (depende de confirmação externa)
NOTAS-FRACOES-1 em paralelo a partir das sprints B
```

Racional: proteger o diagnóstico e o trabalho pendente (A0/A1) antes de qualquer coisa; ter CI (D1, antecipada) antes dos ciclos de commits das sprints B/C; tornar os documentos confiáveis (B) antes de mover arquivos (C); C0 (ADRs, incl. decisão DH-1 — **não fechada nesta sprint de salvaguarda**) precede qualquer movimentação do pipeline RI (C1).
