# ADR-006 — Política Inicial de Dados para Uso em IA

## Status

Proposto

## Contexto

O Cartório System lida com dados de naturezas distintas: normas públicas, documentos
internos, metadados operacionais e dados pessoais/sensíveis de partes, matrículas e
atos. Antes de qualquer uso de IA — seja em base local ou via API externa — é necessário
definir formalmente quais categorias de dados podem ser usadas em cada contexto.

A ausência de PII em um documento **não implica autorização automática para envio
a API externa**. Documentos internos podem ser confidenciais por razões de estratégia,
contrato, segurança ou governança, independentemente de conterem ou não dados pessoais.

Esta ADR define a política inicial para as Fases 1 e 2. Fases posteriores poderão
expandir o escopo mediante decisão humana formal, análise jurídica e, quando necessário,
contrato enterprise com Zero Data Retention (ZDR).

## Decisão

### Categorias e permissões iniciais

| Categoria | Knowledge Base local | API externa (Fase 2+) | Observação |
|-----------|---------------------|----------------------|------------|
| **Norma pública** (Provimento CNJ 213, Provimento 50/2015, CNPFE-GO, Código de Normas) | Permitido | Permitido com cautela | Baixo risco; documentos públicos |
| **Documento interno sem PII** (ADRs, roadmaps, documentação técnica) | Permitido | Somente após revisão de conteúdo | Pode revelar estratégia interna |
| **Documento interno confidencial** (relatórios técnicos, diagnósticos, documentos InovaLGPD com restrição contratual) | Permitido com controle de acesso | Evitar nas fases iniciais | Ausência de PII não elimina confidencialidade |
| **Metadados operacionais** (nomes de arquivos, caminhos, achados sem PII) | Permitido com redaction | Somente com redaction validada | Pode revelar estrutura interna |
| **Dados pessoais / sensíveis** (CPF, nomes de partes, valores, matrículas, atos, dados de titulares LGPD) | Proibido nas fases iniciais | Proibido nas fases iniciais | Exige base legal, anonimização, ZDR e aprovação formal |

### Regras derivadas

1. **Fase 1 (knowledge_base sem IA):** apenas normas públicas e documentos internos
   previamente revisados e aprovados pelo gestor.

2. **Fase 2 (ai_gateway com prompts fixos):** apenas dados normativos públicos e
   documentos internos sem PII e sem restrição contratual. Nenhum dado operacional.

3. **Dados operacionais (AuditFinding, LgpdAction, inventários):** somente a partir
   da Fase 3 ou posterior, com redaction validada, anonimização e aprovação formal.

4. **Dados pessoais/sensíveis e dados de matrículas:** proibidos em todas as fases
   iniciais. Uso futuro exige: base legal LGPD explícita, anonimização, contrato
   enterprise com ZDR e decisão formal do gestor/delegatário.

5. **Documentos InovaLGPD:** uso na knowledge base depende de confirmação da
   ausência de restrição contratual (DHP-05).

## Consequências

### Positivas

- Elimina o risco de violação de LGPD nas fases iniciais.
- Reduz o risco de quebra de sigilo profissional.
- Cria um critério claro e auditável para cada chamada de IA.
- Permite que o `ai_gateway` implemente validação automática da categoria do dado.
- Facilita a expansão progressiva e controlada do escopo.

### Negativas / Trade-offs

- Casos de uso iniciais são limitados a consultas normativas — não abrangem dados
  de clientes, matrículas ou processos reais.
- Requer disciplina na classificação de cada documento antes de indexar.
- Expansão do escopo requer processo formal a cada nova categoria de dado.

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|-------------|-------------------|
| Permitir todos os dados internos sem PII desde a Fase 1 | Ausência de PII não elimina confidencialidade; risco de revelar estratégia |
| Nenhuma política formal (decidir caso a caso) | Sem rastreabilidade; risco de decisão inconsistente; inviável para auditoria |
| Permitir dados anonimizados desde Fase 2 | Anonimização precisa ser validada antes de ser confiável; depende de redaction estável |
| Contratar ZDR imediatamente para ampliar escopo | Custo; ZDR não resolve classificação de confidencialidade não-PII |

## Relação com normas e governança

- LGPD (Lei 13.709/2018), arts. 7º e 11: a base legal para tratamento de dados
  pessoais deve estar definida antes de qualquer uso em IA.
- Provimento CNJ 213/2026: dados de registros imobiliários têm natureza pública
  (atos de registro) e privada (dados de partes) — a distinção é relevante.
- ADR-004 e ADR-005: esta política é o critério de dados que viabiliza a Fase 1
  e restringe a Fase 2.
- DAR-002 (AI-LEGAL-0): esta ADR formaliza e expande a decisão proposta em DAR-002.

## Próximos passos

1. Aprovação humana: gestor deve confirmar as categorias autorizadas (DHP-03, DHP-04,
   DHP-05, DHP-06, DHP-07).
2. Criar lista de documentos autorizados para a knowledge base (lista explícita, não
   categoria genérica).
3. Implementar validação de categoria no `ai_gateway` antes de qualquer chamada à API.
4. Revisar esta ADR antes da Fase 3 para avaliar expansão de escopo.

---

*Proposto na Sprint AI-LEGAL-0A — 2026-05-17*
*Nenhum código foi implementado. Pendente de aprovação humana.*
