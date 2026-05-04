# Plano de Auditoria de Fluxos Operacionais — Cartório Costa Teixeira

> Documento de planejamento. Nenhuma execução documentada aqui.
> Não inclui dados pessoais de clientes ou conteúdo de documentos reais.

Última atualização: 2026-05-04

---

## Objetivo

Mapear, diagnosticar e documentar os fluxos operacionais internos da serventia,
identificando:

- Ausências de documentação (fluxo sem POP)
- Dependências de pessoas únicas (risco de ausência)
- Pontos de falha não controlados
- Riscos de dados sensíveis transitando sem controle
- Inconsistências entre o fluxo real e o fluxo documentado
- Requisitos do Provimento CNJ 213/2026 não atendidos

---

## Fluxos prioritários

### Prioridade 1 — Críticos para vistoria e continuidade

| Fluxo | Risco atual | POP existente? |
|-------|------------|---------------|
| Entrada e protocolo de documentos | Sem rastreabilidade formal | A verificar |
| Digitalização de documentos | Descentralizada, histórico de perdas | A verificar |
| Tratamento de documentos suspeitos/falsos | Fluxo desconhecido | A verificar |
| Arquivamento físico e digital | Sem padronização conhecida | A verificar |
| Acesso ao servidor e sistemas críticos | Sem controle formal | A verificar |

### Prioridade 2 — Operacionais essenciais

| Fluxo | Risco atual | POP existente? |
|-------|------------|---------------|
| Qualificação e análise jurídica | Dependente de pessoa | A verificar |
| Geração de documentos (atos notariais) | Depende 100% do Engegraph | A verificar |
| Assinatura e autenticação | Processo manual + e-Notariado | A verificar |
| Emissão de certidões | Depende 100% do Engegraph | A verificar |
| Obrigações externas (CNJ, SEDI, ISS) | Prazos não sistematizados | A verificar |

### Prioridade 3 — Financeiro e suporte

| Fluxo | Risco atual | POP existente? |
|-------|------------|---------------|
| Emolumentos, repasses e ISS | Planilhas manuais isoladas | A verificar |
| Fundos e taxas (ARPEN, FIC, CRC, etc.) | Manual | A verificar |
| Comunicação com clientes | Sem padrão documentado | A verificar |
| Controle de prazos e vencimentos | Sem sistema centralizado | A verificar |

---

## Método de diagnóstico por fluxo

Para cada fluxo, aplicar o seguinte roteiro:

### Roteiro de diagnóstico (Fase 8 — entrevista estruturada)

**Bloco 1 — Descrição do fluxo atual**

```
1. Como o fluxo começa? (trigger)
2. Quem inicia o fluxo?
3. Quais sistemas são usados?
4. Quais documentos são gerados ou consultados?
5. Quem pode autorizar o próximo passo?
6. Como o fluxo termina? (output)
7. Existe algum registro do que foi feito?
```

**Bloco 2 — Dependências e vulnerabilidades**

```
1. Se a pessoa responsável faltar, quem pode continuar?
2. Se o Engegraph estiver fora do ar, o fluxo para completamente?
3. Há etapas que dependem de acesso remoto?
4. Há documentos físicos que só existem em um lugar?
5. Há dados de clientes que transitam por canais não controlados (WhatsApp, e-mail pessoal)?
```

**Bloco 3 — Conformidade e documentação**

```
1. Existe POP escrito para este fluxo?
2. O POP está atualizado (data de última revisão)?
3. Todos os colaboradores envolvidos conhecem o POP?
4. O fluxo gera evidência (log, registro, assinatura)?
5. Quanto tempo é preservada essa evidência?
```

---

## Mapa de documentação esperada por fluxo

Para cada fluxo auditado, o resultado esperado é:

| Documento | Formato | Propósito |
|-----------|---------|-----------|
| Diagrama de fluxo (BPMN simplificado ou textual) | Markdown/PNG | Visualização do fluxo |
| POP revisado ou criado | `.odt`/`.pdf` assinado | Execução pelo colaborador |
| Lista de achados | `flows_diagnosis.md` | Registro de gaps e riscos |
| Matriz de riscos do fluxo | `flows_risk_matrix.md` | Priorização |
| Lista de melhorias sugeridas | `action_plan.md` | Plano de ação |

---

## Fluxo de digitalização — auditoria prioritária

O fluxo de digitalização foi identificado como crítico: há histórico de documentos
perdidos após digitalização. Este fluxo requer diagnóstico imediato.

### Perguntas específicas

```
1. Onde são digitalizados os documentos? (scanner em qual máquina?)
2. Para onde vão os arquivos após a digitalização? (pasta local, servidor, pendrive?)
3. Quem verifica se a digitalização ficou legível?
4. Existe nomenclatura padrão para os arquivos?
5. Como o arquivo digitalizado é vinculado ao processo/protocolo?
6. O arquivo vai para o Engegraph? Como?
7. Existe backup dos arquivos digitalizados?
8. Já ocorreu perda de documentos digitalizados? Como foi identificado?
9. Como documentos sigilosos são tratados após a digitalização?
```

### Estado esperado (pós-auditoria)

- Pasta centralizada no FileServer para digitalizações, com subpastas por área
- Nomenclatura padrão definida: `AAAA-MM-DD_tipo_protocolo.pdf`
- Responsável definido para cada tipo de digitalização
- Backup automático da pasta de digitalização dentro do RPO ≤4h
- POP de digitalização aprovado e comunicado

---

## Fluxo de tratamento de documentos suspeitos/falsos

### Perguntas específicas

```
1. Existe procedimento formal para documentos suspeitos?
2. Quem tem autoridade para suspeitar de um documento?
3. O que acontece com o documento enquanto a suspeita é investigada?
4. Há registro das suspeitas e investigações?
5. Quando e como a serventia comunica às autoridades?
6. Existe pasta física isolada para documentos suspeitos?
7. Existe pasta digital isolada para cópias de documentos suspeitos?
8. Quem tem acesso a essa pasta?
```

---

## Fluxo financeiro — integração com Cartório System

O fluxo financeiro é especialmente relevante pois o Cartório System já possui
o módulo Finance Core v1.2. A auditoria deste fluxo deve mapear:

```
1. Como são registrados os emolumentos hoje? (Engegraph? Planilha? Ambos?)
2. Como são calculados os repasses ao CNJ, ARPEN, FIC, etc.?
3. Quem verifica os cálculos antes do repasse?
4. Como é feito o controle de ISS?
5. As planilhas financeiras têm backup?
6. Quem tem acesso às planilhas financeiras?
7. Há conciliação entre Engegraph e planilhas?
```

Os achados desta auditoria alimentam diretamente o backlog de evolução do módulo
financeiro do Cartório System (quando retomar no futuro).

---

## Fluxo de obrigações externas

| Obrigação | Periodicidade | Sistema usado | Gap atual |
|-----------|-------------|--------------|-----------|
| Declaração CNJ (JTCO/JTEM) | Mensal | A verificar | A verificar |
| SEDI | A verificar | A verificar | A verificar |
| ISS | Mensal | Manual/Prefeitura | A verificar |
| CRC (Carne Leão) | Mensal | A verificar | A verificar |
| ARPEN | A verificar | A verificar | A verificar |
| FIC | A verificar | A verificar | A verificar |
| ONR | A verificar | A verificar | A verificar |
| Sioreg | A verificar | A verificar | A verificar |

**Ação:** Preencher esta tabela durante a Fase 8 com o gestor.

---

## Entregas esperadas da Fase 8

```text
exports/audit/flows-<data>/
├── manifest.json
├── flows_inventory.md          # lista de fluxos com status (documentado/não documentado)
├── flows_diagnosis.md          # achados por fluxo
├── flows_risk_matrix.md        # riscos identificados nos fluxos
├── digitalization_diagnosis.md # diagnóstico específico da digitalização
├── suspicious_docs_diagnosis.md
├── financial_flow_diagnosis.md
└── action_plan.md              # recomendações priorizadas
```
