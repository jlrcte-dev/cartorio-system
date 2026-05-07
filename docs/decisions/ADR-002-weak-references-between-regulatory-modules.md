# ADR-002 — Referências fracas entre módulos regulatórios

## Status

Proposto — aguarda aprovação antes de implementação

Data: 2026-05-06  
Autores: João + Claude Code  
Sprint de origem: Blueprint Regulatório

---

## Contexto

O Cartório System possui quatro módulos regulatórios independentes: `audit`,
`retention`, `lgpd` e `compliance`. Cada módulo possui seu próprio domínio,
entidades, migrations e testes de isolamento.

A Sprint LGPD/Compliance-1 estabeleceu a fronteira estrita: `compliance` não
importa `audit`, `lgpd` ou `retention`. A próxima fase (LGPD/Compliance-2)
precisa implementar `ComplianceEvidence`, que por sua natureza deve referenciar
dados de outros módulos: findings de `audit` (DIAG-004), sinais de `retention`
(TEMP-002), ações de `lgpd` (AC-15) e fontes externas.

Há duas estratégias principais para essa integração:

**Estratégia A — Foreign Keys diretas**  
`ComplianceEvidence.audit_finding_id FK → audit_findings.id`

**Estratégia B — Referências fracas textuais**  
`ComplianceEvidence.source_module = "audit"`  
`ComplianceEvidence.source_ref = "DIAG-004"`

A escolha impacta acoplamento, migrations, capacidade de referenciar fontes
externas, e a autonomia de evolução de cada módulo.

---

## Decisão

**A integração inicial entre `compliance` e os demais módulos regulatórios ocorre
por referência fraca textual, não por foreign key direta.**

O conjunto de campos de referência fraca é:

```
source_module : str   →  "audit" | "retention" | "lgpd" | "external" | "manual"
source_type   : str   →  "finding" | "temp_signal" | "lgpd_action" |
                          "document" | "other"
source_ref    : str   →  código identificador legível (ex: "DIAG-004", "AC-15")
```

A validação de existência do `source_ref` é responsabilidade da camada de
service de `compliance` em tempo de execução, não do banco de dados.

FK formal pode ser introduzida em sprint futura quando o modelo estabilizar e
o benefício de integridade automática superar o custo de acoplamento.

---

## Consequências positivas

**1. Baixo acoplamento entre módulos**  
Migrations de `audit` (ex: adição de coluna em `audit_findings`) não impactam
`compliance`. Cada módulo evolui de forma independente. Não há FK cruzada que
exija coordenação de alembic entre módulos.

**2. Suporte a fontes heterogêneas**  
Fontes externas (documentos PDF em `_VISTORIA/`, atas, e-mails, screenshots)
não têm representação em nenhuma tabela do sistema. A referência fraca permite
que `ComplianceEvidence` as referencie com `source_module = "external"` e
`source_ref = "ata_dpo.pdf"` sem exigir tabela intermediária.

**3. Menor risco em migrations futuras**  
FK direta cria dependência de ordem na execução de migrations: `compliance`
precisaria ser migrado após `audit`. Referência fraca elimina esse vínculo.

**4. Rastreabilidade humana legível**  
`source_ref = "DIAG-004"` é imediatamente compreensível em logs, relatórios
e dossiê. Uma UUID de FK seria opaca sem join adicional.

**5. Semântica correta para achados imutáveis**  
`AuditFinding` tem regra de negócio de imutabilidade (nunca deletado). Mesmo
com FK, a probabilidade de referência órfã é negligível. Com referência fraca,
o mesmo benefício é obtido sem pagar o custo de acoplamento de schema.

**6. Preparação para fontes futuras**  
Futuras origens de evidências (ex: relatórios do SEDI, dados do e-notariado,
arquivos do Engegraph) podem ser referenciadas sem adicionar FK nem alterar o
schema de `ComplianceEvidence`.

---

## Consequências negativas

**1. Integridade referencial não garantida pelo banco**  
O banco não verifica se `source_ref = "DIAG-004"` existe em `audit_findings`.
Se um finding fosse deletado (não é possível, por design), a referência ficaria
inconsistente sem alertas automáticos do banco.

**Mitigação principal:** Achados e ações são imutáveis por princípio de design.
`AuditFinding` e `LgpdAction` nunca são deletados; apenas status evolui.

**Mitigação secundária:** O service de compliance valida a existência do
`source_ref` no momento de criação da evidência. Evidências já criadas não são
invalidadas retroativamente (comportamento esperado: o achado que motivou a
evidência ainda existia quando ela foi criada).

**2. Consulta cruzada sem join de banco**  
Para exibir detalhes do finding referenciado junto com a evidência, o service
precisa fazer duas queries: uma em `compliance_evidences` e outra em
`audit_findings`. Com FK + join, uma query seria suficiente.

**Mitigação:** O caso de uso principal é listar evidências por requisito, não
por finding. A query cruzada (buscar detalhes do finding a partir da evidência)
é menos frequente e pode ser otimizada por cache ou lazy-load quando necessário.

**3. Sem restrição de tipo `source_ref` por `source_module`**  
O banco aceita `source_module = "audit"` com `source_ref = "AC-15"` sem erro.
A validação de coerência é responsabilidade do service.

**Mitigação:** Validação no service: se `source_module = "audit"`, `source_ref`
deve seguir padrão `DIAG-\d{3}`. Enum `source_module` e validação regex no
Pydantic schema.

---

## Alternativas consideradas

### Alternativa A: FK direta entre tabelas de módulos diferentes

```python
# Em compliance/models.py
class ComplianceEvidence(Base):
    audit_finding_id = Column(UUID, ForeignKey("audit_findings.id"), nullable=True)
    lgpd_action_id   = Column(UUID, ForeignKey("lgpd_actions.id"), nullable=True)
```

**Por que descartada:**

1. **Violação de isolamento:** `compliance/models.py` passaria a importar
   `audit_findings` e `lgpd_actions` — quebrando o princípio de isolamento
   testado em `test_compliance_isolation`.
2. **Acoplamento de migrations:** migrations de compliance precisariam rodar
   após audit e lgpd; qualquer reordenação quebraria o alembic history.
3. **Impossibilidade com fontes externas:** documentos em `_VISTORIA/` não
   têm tabela no sistema; a FK exigiria tabela intermediária para cada tipo.
4. **Excesso de colunas nullable:** com N módulos como fonte possível,
   `ComplianceEvidence` teria N colunas de FK nullable — má modelagem.

### Alternativa B: Tabela polimórfica com `content_type_id`

Padrão `GenericForeignKey` (estilo Django): tabela `content_types` mapeia
`app_label + model` → `id`; `ComplianceEvidence` tem `content_type_id` +
`object_id`.

**Por que descartada:**

1. **Complexidade sem benefício imediato:** requer tabela adicional
   (`content_types`) e lógica específica de resolução de tipo.
2. **Não nativo no SQLAlchemy:** requer implementação customizada.
3. **Opaco para leitura direta:** `object_id = UUID` é ilegível sem join;
   a referência fraca textual (`source_ref = "DIAG-004"`) é mais legível.
4. **Ancora no schema atual:** se `audit_findings.id` mudar de UUID para
   outro tipo, `object_id` precisaria acompanhar.

### Alternativa C: Event sourcing / tabela de eventos compartilhada

Cada módulo publica eventos em uma tabela compartilhada (`regulatory_events`);
compliance consome os eventos.

**Por que descartada:**

1. **Complexidade desproporcional:** o nível de maturidade do projeto não
   justifica event sourcing neste momento.
2. **Novos conceitos para o time:** introduz padrão arquitetural distinto
   do padrão atual (FastAPI + SQLAlchemy CRUD).
3. **Latência eventual:** para o caso de uso (evidenciação regulatória com
   revisão humana), consistência eventual é desnecessária.
4. **Pode ser considerado em sprint futura** se o volume e a frequência de
   integração crescerem significativamente.

---

## Critérios para promover para FK formal

A FK direta pode ser introduzida futuramente se **todos** os critérios abaixo
forem atendidos:

1. O schema de `AuditFinding` e `LgpdAction` estiver estável (sem renomeações
   previstas por pelo menos 6 meses)
2. O benefício de consistência automática do banco superar o custo de
   acoplamento de migrations (avaliação do time)
3. As consultas cruzadas (finding + evidência em um join) forem frequentes o
   suficiente para justificar a otimização
4. Não houver fontes externas (`source_module = "external"`) em uso ativo
   que ficariam excluídas da FK

---

## Impacto nas próximas sprints

| Sprint | Impacto |
|--------|---------|
| LGPD/Compliance-2 | Implementa `ComplianceEvidence` com `source_module`, `source_type`, `source_ref` |
| Sprint RequirementFindingLink | Mesmo padrão: `source_module` + `source_ref` para finding ou temp_signal |
| Sprint DossieTecnico | DossieService resolve referências fracas na geração; não usa join de banco |
| LGPD-2 | Sem impacto — lgpd_actions não recebe referência de volta do compliance |
| Testes de isolamento | `test_compliance_isolation` continua verificando ausência de imports cruzados |

---

## Referências

- [Blueprint de Integração Regulatória](../CNJ_213_REGULATORY_INTEGRATION_BLUEPRINT.md) — Seção 6
- [ADR-001 — ComplianceEvidence como entidade central](ADR-001-compliance-evidence-ownership.md)
- [docs/modules/compliance.md](../modules/compliance.md) — Fronteiras atuais do módulo
- Decisão D-23 em [decisions.md](../decisions.md) — DocumentDiagnosis analisa artefatos, não servidor diretamente
