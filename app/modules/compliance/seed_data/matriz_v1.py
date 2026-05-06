"""Dataset matriz_v1 — Matriz de Correlação INOVA V1.

Origem: Matriz_Correlacao_Provimento213_Politicas V1.pdf (InovaLGPD, Março 2026).
Não contém o PDF — apenas referência textual ao caminho local.

Os artigos do Provimento CNJ 213/2026 e dos Anexos III/IV são representados
como requisitos com `source` indicando a origem normativa. A natureza da
obrigação (LGPD x Provimento x complementar) fica em `classification`.

Esta sprint NÃO declara conformidade. O objetivo é fundacional: representar
o mapa requisito → política → prazo → evidência sugerida.
"""

from __future__ import annotations

from typing import TypedDict

from app.modules.compliance.enums import (
    DeadlineUnit,
    PolicyDocumentKind,
    RequirementClassification,
    RequirementSource,
    RequirementStage,
    ServentiaClass,
)


class RequirementSeed(TypedDict):
    code: str
    source: RequirementSource
    article_label: str
    article_text: str
    classification: RequirementClassification
    stage: RequirementStage
    notes: str | None


class PolicySeed(TypedDict):
    code: str
    title: str
    kind: PolicyDocumentKind
    classification: RequirementClassification
    inova_filename: str
    description: str | None


class RequirementPolicySeed(TypedDict):
    requirement_code: str
    policy_code: str
    policy_section_notes: str


class DeadlineSeed(TypedDict):
    requirement_code: str
    serventia_class: ServentiaClass
    value: int | None
    unit: DeadlineUnit
    stage_label: str
    notes: str | None


class EvidenceTemplateSeed(TypedDict):
    requirement_code: str
    description: str
    sort_order: int
    notes: str | None


class SeedMetaInfo(TypedDict):
    seed_name: str
    seed_version: str
    source_document: str
    source_file_reference: str
    notes: str


SEED_META: SeedMetaInfo = {
    "seed_name": "matriz_v1",
    "seed_version": "V1.0_MAR2026",
    "source_document": (
        "Matriz de Correlação Provimento CNJ 213/2026 e Políticas — InovaLGPD V1.0, Março 2026"
    ),
    "source_file_reference": (
        "_local_data/LGPD - inova/Guia provimento 213/"
        "Matriz_Correlacao_Provimento213_Politicas V1.pdf"
    ),
    "notes": (
        "Dataset fundacional read-only. Representa o mapeamento da matriz "
        "InovaLGPD; não declara conformidade da serventia. Validação humana, "
        "jurídica e administrativa necessária antes de uso oficial."
    ),
}


# ---------------------------------------------------------------------------
# Requirements
# ---------------------------------------------------------------------------

SEED_REQUIREMENTS: list[RequirementSeed] = [
    {
        "code": "ART_1_X",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 1º, X — Definição PCN",
        "article_text": (
            "Plano de Continuidade de Negócios (PCN): conjunto estruturado de "
            "procedimentos destinados a assegurar a continuidade da prestação "
            "do serviço em situações de indisponibilidade."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_2,
        "notes": None,
    },
    {
        "code": "ART_1_XI",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 1º, XI — Definição PRD",
        "article_text": (
            "Plano de Recuperação de Desastres (PRD): conjunto de medidas "
            "técnicas e operacionais voltadas à restauração de sistemas e "
            "dados após incidente grave."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_2,
        "notes": None,
    },
    {
        "code": "ART_3_CAPUT",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 3º, caput — Políticas de Gestão",
        "article_text": (
            "Magistrados, delegatários, interinos e interventores deverão "
            "adotar e manter políticas de gestão, fiscalização e controle "
            "que assegurem confidencialidade, integridade, disponibilidade, "
            "autenticidade e rastreabilidade dos atos praticados."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_3_P1",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 3º, §1º — PSI",
        "article_text": (
            "Os serviços notariais e de registro deverão instituir diretrizes "
            "formais de continuidade operacional e preservação de dados, "
            "incorporadas à Política Interna de Segurança da Informação."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_3_P2",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 3º, §2º — Conteúdo Mínimo PCN/PRD",
        "article_text": (
            "Os planos referidos no §1º deverão contemplar identificação e "
            "avaliação de riscos, medidas de mitigação, providências de curto "
            "prazo (até 30 dias) e de médio prazo (até 90 dias)."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_2,
        "notes": None,
    },
    {
        "code": "ART_4_P2_P3",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 4º, §2º-§3º — Licenciamento e Vedação a EOL",
        "article_text": (
            "Todos os softwares utilizados pelas serventias deverão possuir "
            "licenciamento regular. Vedada a utilização de sistemas em End of "
            "Life (EOL)."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_5",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 5º — Autenticação Individualizada e MFA",
        "article_text": (
            "Os responsáveis e seus colaboradores deverão utilizar mecanismos "
            "de autenticação individualizados, com MFA nos acessos a sistemas "
            "críticos, vedado o uso de credenciais compartilhadas."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_6_I",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 6º, I — Políticas Alinhadas à LGPD",
        "article_text": (
            "Os responsáveis pelas serventias extrajudiciais deverão adotar, "
            "formalizar e manter políticas de gestão alinhadas à Lei Geral de "
            "Proteção de Dados Pessoais (Lei nº 13.709/2018)."
        ),
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_6_III",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 6º, III — Transferência Organizada de Acervos",
        "article_text": (
            "Garantir a transferência organizada dos acervos da serventia aos "
            "eventuais sucessores, incluindo bancos de dados, softwares, "
            "manuais, políticas internas, controle de acessos, inventário de "
            "ativos tecnológicos e histórico de atualizações."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_5,
        "notes": None,
    },
    {
        "code": "ART_6_IV",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 6º, IV — Continuidade da Prestação",
        "article_text": (
            "Promover a continuidade da prestação do serviço de forma "
            "adequada, ininterrupta, segura, eficaz e eficiente, em "
            "conformidade com planos de contingência e continuidade "
            "periodicamente revisados."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_2,
        "notes": None,
    },
    {
        "code": "ART_7_P1",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 7º, §1º — Registro de Operações de Tratamento",
        "article_text": (
            "A serventia deverá manter registro das operações de tratamento "
            "de dados (ROPA), conforme legislação vigente."
        ),
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_7_P2",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 7º, §2º — Designação de DPO",
        "article_text": (
            "Quando aplicável, deverá ser designado encarregado pelo "
            "tratamento de dados pessoais (DPO), com atribuições compatíveis "
            "com a legislação e os riscos inerentes."
        ),
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_7_P3",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 7º, §3º — Comunicação de Incidentes",
        "article_text": (
            "Incidentes que possam acarretar risco ou dano relevante aos "
            "titulares deverão ser comunicados à ANPD e à Corregedoria. "
            "Análise de causa raiz e medidas corretivas obrigatórias."
        ),
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_8",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 8º — Soluções Tecnológicas — Requisitos Gerais",
        "article_text": (
            "As soluções tecnológicas deverão basear-se em normas técnicas "
            "reconhecidas; permitir interoperabilidade; evitar dependência "
            "exclusiva; assegurar segregação lógica de dados, segmentação "
            "de redes e proteção perimetral."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_2,
        "notes": None,
    },
    {
        "code": "ART_9",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 9º — Criptografia de Dados",
        "article_text": (
            "Dados sensíveis, informações pessoais e registros eletrônicos "
            "deverão ser protegidos por criptografia adequada (TLS 1.2+ em "
            "trânsito, AES-256+ em repouso, backups), com gestão segura de "
            "chaves."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_3,
        "notes": None,
    },
    {
        "code": "ART_10",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 10 — Trilhas de Auditoria (Logs)",
        "article_text": (
            "Manter trilhas de auditoria que permitam rastreabilidade, "
            "identificação de usuários, data/hora, natureza da ação e "
            "resultado. Logs protegidos contra alteração com prazos mínimos "
            "de retenção."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_3_4,
        "notes": None,
    },
    {
        "code": "ART_11",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 11 — Gestão de Incidentes de Segurança",
        "article_text": (
            "Procedimentos documentados para gestão de incidentes: "
            "identificação, classificação por gravidade, contenção, "
            "erradicação, recuperação e registro. Críticos comunicados em "
            "até 72h. Análise de causa raiz obrigatória."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_12",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 12 — Atos Eletrônicos, Backup e Infraestrutura",
        "article_text": (
            "Atos eletrônicos com autenticidade, integridade, imutabilidade "
            "e rastreabilidade. Política formal de backup automatizado e "
            "monitorado, com cópias completas/incrementais, off-site e "
            "testes de restauração."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_3,
        "notes": None,
    },
    {
        "code": "ART_12_P9",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 12, §9º — Atas de Teste de Restauração",
        "article_text": (
            "Os testes de restauração deverão ser registrados em ata formal, "
            "conforme modelo do Anexo V, evidenciando integralidade do "
            "backup, falhas detectadas e medidas tomadas."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_4,
        "notes": None,
    },
    {
        "code": "ART_13",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 13 — Modelos de Cumprimento e Contratação",
        "article_text": (
            "O cumprimento dos requisitos poderá ocorrer por solução "
            "própria, contratada (SaaS/PaaS/IaaS), compartilhada ou "
            "coletiva. Contratações com cláusulas de confidencialidade, "
            "reversibilidade, portabilidade, gestão de incidentes e LGPD."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ART_15",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 15 — Mitigação de Dependência de Fornecedor",
        "article_text": (
            "Considera-se mitigada a dependência estrutural quando houver "
            "cláusula de reversibilidade e portabilidade em formato "
            "interoperável; teste de extração documentado; ausência de "
            "restrição à migração."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_5,
        "notes": None,
    },
    {
        "code": "ART_17",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 17 — Declaração no Sistema Justiça Aberta",
        "article_text": (
            "Os responsáveis deverão declarar o cumprimento das fases no "
            "Sistema Justiça Aberta, renovada anualmente com síntese do "
            "dossiê técnico."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.TODAS,
        "notes": None,
    },
    {
        "code": "ART_19",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 19 — Interoperabilidade com Plataformas de Fiscalização",
        "article_text": (
            "As soluções tecnológicas deverão ser aptas à integração com "
            "plataformas de fiscalização, com formatos abertos, identificação "
            "inequívoca, canal seguro e registros auditáveis."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_5,
        "notes": None,
    },
    {
        "code": "ART_20",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 20 — Prazos de Implementação Inicial (Etapas 1 e 2)",
        "article_text": (
            "A implementação das Etapas 1 e 2 deverá ocorrer em: Classe 3 — "
            "90 dias; Classe 2 — 150 dias; Classe 1 — 210 dias, contados da "
            "entrada em vigor."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPAS_1_2,
        "notes": None,
    },
    {
        "code": "ART_23",
        "source": RequirementSource.PROV_213,
        "article_label": "Art. 23 — Prazo Máximo Total (Etapas 1-5)",
        "article_text": (
            "A implementação integral deverá estar concluída em: Classe 3 — "
            "até 24 meses; Classe 2 — até 30 meses; Classe 1 — até 36 meses."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPAS_1_5,
        "notes": None,
    },
    {
        "code": "ANEXO_III_4_8",
        "source": RequirementSource.ANEXO_III,
        "article_label": "Anexo III, 4.8 — Direitos dos Titulares (LGPD)",
        "article_text": (
            "A PSI deve contemplar observância integral da Lei 13.709/2018, "
            "caracterização do controlador, ROPA, atendimento aos direitos "
            "dos titulares (art. 18 LGPD), comunicação de incidentes à ANPD "
            "e designação de DPO."
        ),
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ANEXO_IV_ETAPA_1",
        "source": RequirementSource.ANEXO_IV,
        "article_label": "Anexo IV, Etapa 1 — Governança e Conformidade Legal",
        "article_text": (
            "Designar responsável técnico, controlador e DPO; elaborar e "
            "divulgar PSI; implementar autenticação individualizada e MFA; "
            "instituir ROPA; definir comunicação de incidentes; elaborar "
            "inventário de ativos; regularizar licenciamento e contratos."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": None,
    },
    {
        "code": "ANEXO_IV_ETAPA_2",
        "source": RequirementSource.ANEXO_IV,
        "article_label": "Anexo IV, Etapa 2 — Infraestrutura e Continuidade",
        "article_text": (
            "Implementar infraestrutura energética (UPS/SAI); ambiente "
            "físico adequado; conectividade compatível; PCN e PRD com "
            "RTO/RPO; proteção de endpoint; documento de arquitetura "
            "tecnológica."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_2,
        "notes": None,
    },
    {
        "code": "ANEXO_IV_ETAPA_3",
        "source": RequirementSource.ANEXO_IV,
        "article_label": "Anexo IV, Etapa 3 — Acervo Digital e Resiliência",
        "article_text": (
            "Implementar criptografia (trânsito/repouso/backup); rotinas "
            "automatizadas de backup; monitoramento; firewall com IPS/IDS; "
            "SGBD com integridade transacional; trilhas de auditoria "
            "imutáveis."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_3,
        "notes": None,
    },
    {
        "code": "ANEXO_IV_ETAPA_4",
        "source": RequirementSource.ANEXO_IV,
        "article_label": "Anexo IV, Etapa 4 — Monitoramento e Auditoria",
        "article_text": (
            "Emitir relatório de conformidade de auditoria; rotina de "
            "atualização de sistemas; gestão formal de vulnerabilidades; "
            "simulação anual de desastre; testes de restauração; pentest "
            "para Classe 3; análise de causa raiz."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_4,
        "notes": None,
    },
    {
        "code": "ANEXO_IV_ETAPA_5",
        "source": RequirementSource.ANEXO_IV,
        "article_label": "Anexo IV, Etapa 5 — Interoperabilidade e Governança Evolutiva",
        "article_text": (
            "Adequar interoperabilidade com plataformas de fiscalização; "
            "padrões abertos; capacitação periódica; revisão da PSI; "
            "registros auditáveis por 5 anos; plano de reversibilidade com "
            "simulação de extração."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_5,
        "notes": None,
    },
    {
        "code": "ANEXO_II_4",
        "source": RequirementSource.ANEXO_IV,
        "article_label": "Anexo II, item 4 — Plano de Resposta a Incidentes",
        "article_text": (
            "Item operacional do Anexo II referente à manutenção de plano "
            "documentado de resposta a incidentes de segurança, com fluxos "
            "de comunicação interna e externa."
        ),
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "stage": RequirementStage.ETAPA_1,
        "notes": (
            "Referência cruzada do Anexo II ao art. 11 e art. 7º §3º; validar redação oficial."
        ),
    },
]


# ---------------------------------------------------------------------------
# Policies (30)
# ---------------------------------------------------------------------------

SEED_POLICIES: list[PolicySeed] = [
    # --- LGPD (12)
    {
        "code": "POL_AVISO_PRIVACIDADE",
        "title": "Política de Aviso de Privacidade",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Aviso_Privacidade_v1.0.docx",
        "description": "Aviso de privacidade para titulares de dados.",
    },
    {
        "code": "POL_PRIVACIDADE",
        "title": "Política de Privacidade",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Politica_Privacidade_v1.0.docx",
        "description": "Política institucional de privacidade.",
    },
    {
        "code": "ROPA",
        "title": "ROPA — Registro de Operações de Tratamento",
        "kind": PolicyDocumentKind.INVENTARIO,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "ROPA_Serventia_v1.0.xlsx",
        "description": "Record of Processing Activities (art. 37 LGPD).",
    },
    {
        "code": "TERMO_DPO",
        "title": "Termo de Nomeação do DPO / Encarregado de Dados",
        "kind": PolicyDocumentKind.DOCUMENTO,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Termo_Nomeacao_DPO_v1.0.docx",
        "description": "Designação formal do encarregado de dados.",
    },
    {
        "code": "POL_DESCARTE_DOC",
        "title": "Política de Descarte de Documentos",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Descarte_Documentos_v1.0.docx",
        "description": "Diretrizes de eliminação de dados pessoais.",
    },
    {
        "code": "POL_COMPARTILHAMENTO",
        "title": "Política de Compartilhamento de Dados",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Compartilhamento_Dados_v1.0.docx",
        "description": "Regras para compartilhamento com terceiros.",
    },
    {
        "code": "POL_USO_IMAGEM",
        "title": "Política de Uso de Imagem",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Uso_Imagem_v1.0.docx",
        "description": "Tratamento de imagens (CFTV, fotos institucionais).",
    },
    {
        "code": "POL_COOKIES",
        "title": "Política de Cookies",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Politica_Cookies_v1.0.docx",
        "description": "Política de cookies para canais digitais.",
    },
    {
        "code": "PROC_RIPD",
        "title": "Procedimento para Elaboração do RIPD",
        "kind": PolicyDocumentKind.PROCEDIMENTO,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "RIPD_Procedimento_v1.0.docx",
        "description": "Relatório de Impacto à Proteção de Dados.",
    },
    {
        "code": "PROC_LEGITIMO_INTERESSE",
        "title": "Procedimento para Análise de Legítimo Interesse",
        "kind": PolicyDocumentKind.PROCEDIMENTO,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Legitimo_Interesse_v1.0.docx",
        "description": "Teste de balanceamento de legítimo interesse (art. 10 LGPD).",
    },
    {
        "code": "POL_PRIVACY_BY_DESIGN",
        "title": "Política Privacy by Design",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Privacy_by_Design_v1.0.docx",
        "description": "Privacidade incorporada por padrão em sistemas e processos.",
    },
    {
        "code": "RESP_TITULAR",
        "title": "Política / Registro de Resposta ao Titular",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_LGPD,
        "inova_filename": "Resposta_Titular_v1.0.docx",
        "description": "Atendimento aos direitos dos titulares (art. 18 LGPD).",
    },
    # --- Provimento (11)
    {
        "code": "PSI",
        "title": "Política de Segurança da Informação (PSI)",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "PSI_Serventia_v1.0.docx",
        "description": "PSI institucional conforme Anexo III do Provimento.",
    },
    {
        "code": "PCN",
        "title": "Plano de Continuidade de Negócios (PCN)",
        "kind": PolicyDocumentKind.PLANO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "PCN_Serventia_v1.0.docx",
        "description": "Plano de continuidade com RTO/RPO por classe.",
    },
    {
        "code": "PRD",
        "title": "Plano de Recuperação de Desastres (PRD)",
        "kind": PolicyDocumentKind.PLANO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "PRD_Serventia_v1.0.docx",
        "description": "Plano técnico de recuperação após incidentes graves.",
    },
    {
        "code": "PLANO_INCIDENTES",
        "title": "Plano de Resposta a Incidentes",
        "kind": PolicyDocumentKind.PLANO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Plano_Resposta_Incidentes_v1.0.docx",
        "description": "Procedimentos de identificação, contenção e comunicação.",
    },
    {
        "code": "POL_BACKUP",
        "title": "Política de Backup",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Politica_Backup_v1.0.docx",
        "description": "Rotinas automatizadas, off-site, criptografia e testes.",
    },
    {
        "code": "INVENTARIO_ATIVOS",
        "title": "Inventário de Ativos Tecnológicos",
        "kind": PolicyDocumentKind.INVENTARIO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Inventario_Ativos_v1.0.xlsx",
        "description": "Registro de ativos, licenças e validade de suporte.",
    },
    {
        "code": "ARQUITETURA_TEC",
        "title": "Documento Técnico de Arquitetura Tecnológica",
        "kind": PolicyDocumentKind.DOCUMENTO_TECNICO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Arquitetura_Tecnologica_v1.0.docx",
        "description": "Topologia, ambientes, fluxos, redundâncias.",
    },
    {
        "code": "REVERSIBILIDADE",
        "title": "Plano de Reversibilidade e Portabilidade",
        "kind": PolicyDocumentKind.PLANO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Reversibilidade_Portabilidade_v1.0.docx",
        "description": "Garantia de portabilidade em formato interoperável.",
    },
    {
        "code": "DOSSIE_ETAPAS",
        "title": "Dossiê Técnico por Etapa",
        "kind": PolicyDocumentKind.DOCUMENTO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Dossie_Tecnico_Etapas.docx",
        "description": "Declarações de conclusão para Justiça Aberta.",
    },
    {
        "code": "ATA_RESTAURACAO",
        "title": "Modelo de Ata de Teste de Restauração (Anexo V)",
        "kind": PolicyDocumentKind.MODELO_ATA,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Ata_Teste_Restauracao_v1.0.docx",
        "description": "Modelo padrão para registrar testes de restauração.",
    },
    {
        "code": "CRONOGRAMA",
        "title": "Cronograma de Implementação",
        "kind": PolicyDocumentKind.DOCUMENTO,
        "classification": RequirementClassification.OBRIGATORIO_PROVIMENTO,
        "inova_filename": "Cronograma_Implementacao_v1.0.xlsx",
        "description": "Marcos de implementação por etapa e classe.",
    },
    # --- Complementares (7)
    {
        "code": "POL_MESA_LIMPA",
        "title": "Política de Mesa Limpa",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "Mesa_Limpa_v1.0.docx",
        "description": "Boa prática de segurança física no ambiente de trabalho.",
    },
    {
        "code": "POL_TELA_LIMPA",
        "title": "Política de Tela Limpa",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "Tela_Limpa_v1.0.docx",
        "description": "Boa prática de bloqueio de tela e descarte visual.",
    },
    {
        "code": "POL_BYOD",
        "title": "Política de BYOD (Bring Your Own Device)",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "Politica_BYOD_v1.0.docx",
        "description": "Controle de dispositivos pessoais em ambiente corporativo.",
    },
    {
        "code": "POL_USO_CELULARES",
        "title": "Política de Uso de Celulares — Cartórios",
        "kind": PolicyDocumentKind.POLITICA,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "Uso_Celulares_v1.0.docx",
        "description": "Controle de dispositivos móveis no ambiente da serventia.",
    },
    {
        "code": "GUIA_INCIDENTES",
        "title": "Guia Prático de Resposta a Incidentes — Cartórios",
        "kind": PolicyDocumentKind.GUIA,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "Guia_Pratico_Incidentes_v1.0.docx",
        "description": "Material operacional de apoio ao Plano de Incidentes.",
    },
    {
        "code": "KIT_CARTAZES",
        "title": "Cartazes e Documentos para Serventias",
        "kind": PolicyDocumentKind.CARTAZ,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "Kit_Cartazes_Serventia.zip",
        "description": "Cartazes informativos sobre DPO, câmeras, atendimento.",
    },
    {
        "code": "FAQ_LGPD",
        "title": "FAQ LGPD para Serventias",
        "kind": PolicyDocumentKind.FAQ,
        "classification": RequirementClassification.COMPLEMENTAR_BOA_PRATICA,
        "inova_filename": "FAQ_LGPD_Serventia_v1.0.docx",
        "description": "Perguntas frequentes para colaboradores.",
    },
]


# ---------------------------------------------------------------------------
# Requirement-Policy links
# ---------------------------------------------------------------------------


def _link(req: str, pol: str, notes: str = "") -> RequirementPolicySeed:
    return {
        "requirement_code": req,
        "policy_code": pol,
        "policy_section_notes": notes,
    }


SEED_REQUIREMENT_POLICIES: list[RequirementPolicySeed] = [
    _link("ART_1_X", "PCN", "Documento integral"),
    _link("ART_1_XI", "PRD", "Documento integral"),
    _link("ART_3_CAPUT", "PSI", "Seções 1-5 — Governança e princípios"),
    _link("ART_3_CAPUT", "PCN", "Seção de Gestão e Controle"),
    _link("ART_3_CAPUT", "PRD", "Seção de Controles Técnicos"),
    _link("ART_3_P1", "PSI", "Documento integral"),
    _link("ART_3_P2", "PCN", "Seções de Riscos, Mitigação, Curto/Médio Prazo"),
    _link("ART_3_P2", "PRD", "Seções de Avaliação de Riscos e Restauração"),
    _link("ART_4_P2_P3", "PSI", "Seção de Gestão de Ativos e Licenciamento"),
    _link("ART_4_P2_P3", "INVENTARIO_ATIVOS", "Registro de licenças e validade de suporte"),
    _link("ART_5", "PSI", "Seção 4.1 — Controle de Acesso e Autenticação"),
    # Art. 6º I — 14 LGPD policies
    _link("ART_6_I", "POL_AVISO_PRIVACIDADE", "Documento integral"),
    _link("ART_6_I", "POL_PRIVACIDADE", "Documento integral"),
    _link("ART_6_I", "POL_DESCARTE_DOC", "Documento integral"),
    _link("ART_6_I", "POL_BACKUP", "Documento integral"),
    _link("ART_6_I", "POL_COOKIES", "Documento integral"),
    _link("ART_6_I", "POL_BYOD", "Documento integral"),
    _link("ART_6_I", "POL_MESA_LIMPA", "Documento integral"),
    _link("ART_6_I", "POL_TELA_LIMPA", "Documento integral"),
    _link("ART_6_I", "POL_USO_CELULARES", "Documento integral"),
    _link("ART_6_I", "POL_USO_IMAGEM", "Documento integral"),
    _link("ART_6_I", "POL_COMPARTILHAMENTO", "Documento integral"),
    _link("ART_6_I", "PROC_RIPD", "Documento integral"),
    _link("ART_6_I", "PROC_LEGITIMO_INTERESSE", "Documento integral"),
    _link("ART_6_I", "POL_PRIVACY_BY_DESIGN", "Documento integral"),
    _link("ART_6_III", "REVERSIBILIDADE", "Documento integral"),
    _link("ART_6_III", "INVENTARIO_ATIVOS", "Documento integral"),
    _link("ART_6_IV", "PCN", "Documento integral"),
    _link("ART_6_IV", "PRD", "Documento integral"),
    _link("ART_7_P1", "ROPA", "Documento integral"),
    _link("ART_7_P2", "TERMO_DPO", "Documento integral"),
    _link("ART_7_P3", "PLANO_INCIDENTES", "Documento integral"),
    _link("ART_7_P3", "GUIA_INCIDENTES", "Documento integral"),
    _link("ART_7_P3", "PSI", "Seção 4.6 — Gestão de Incidentes"),
    _link("ART_8", "PSI", "Seções 4.5, 4.9 e 4.10"),
    _link("ART_8", "ARQUITETURA_TEC", "Documento integral"),
    _link("ART_9", "PSI", "Seção 4.9 — Criptografia"),
    _link("ART_9", "POL_BACKUP", "Seção de Criptografia de Backups"),
    _link("ART_10", "PSI", "Seção 4.3 — Monitoramento e Trilhas de Auditoria"),
    _link("ART_11", "PLANO_INCIDENTES", "Documento integral"),
    _link("ART_11", "GUIA_INCIDENTES", "Documento integral"),
    _link("ART_11", "PSI", "Seção 4.6 — Gestão de Incidentes"),
    _link("ART_12", "POL_BACKUP", "Documento integral"),
    _link("ART_12", "PRD", "Seção de Backup e Restauração"),
    _link("ART_12", "PSI", "Seção 4.4 — Backup e Recuperação"),
    _link("ART_12_P9", "ATA_RESTAURACAO", "Documento integral — Anexo V"),
    _link("ART_13", "PSI", "Seção 4.10 — Gestão de Fornecedores"),
    _link("ART_13", "REVERSIBILIDADE", "Documento integral"),
    _link("ART_15", "REVERSIBILIDADE", "Cláusulas e testes"),
    _link("ART_17", "DOSSIE_ETAPAS", "Declarações por etapa"),
    _link("ART_19", "PSI", "Seção 4.5 — Interoperabilidade"),
    _link("ART_19", "ARQUITETURA_TEC", "Seção de Integrações"),
    _link("ART_20", "CRONOGRAMA", "Cronograma das Etapas 1 e 2"),
    _link("ART_23", "CRONOGRAMA", "Cronograma global das Etapas 1-5"),
    _link("ANEXO_III_4_8", "RESP_TITULAR", "Documento integral"),
    _link("ANEXO_III_4_8", "KIT_CARTAZES", "Cartazes DPO/câmeras/atendimento"),
    _link("ANEXO_III_4_8", "FAQ_LGPD", "Material educativo"),
    _link("ANEXO_III_4_8", "ROPA", "Registro de operações de tratamento"),
    _link("ANEXO_III_4_8", "TERMO_DPO", "Designação de encarregado"),
    _link("ANEXO_IV_ETAPA_1", "PSI", "Documento integral (Anexo III)"),
    _link("ANEXO_IV_ETAPA_1", "ROPA", "Documento integral"),
    _link("ANEXO_IV_ETAPA_1", "TERMO_DPO", "Documento integral"),
    _link("ANEXO_IV_ETAPA_1", "INVENTARIO_ATIVOS", "Documento integral"),
    _link("ANEXO_IV_ETAPA_1", "PLANO_INCIDENTES", "Documento integral"),
    _link("ANEXO_IV_ETAPA_2", "PCN", "Documento integral"),
    _link("ANEXO_IV_ETAPA_2", "PRD", "Documento integral"),
    _link("ANEXO_IV_ETAPA_2", "ARQUITETURA_TEC", "Documento integral"),
    _link("ANEXO_IV_ETAPA_3", "POL_BACKUP", "Documento integral"),
    _link("ANEXO_IV_ETAPA_3", "PSI", "Seções 4.4, 4.5 e 4.9"),
    _link("ANEXO_IV_ETAPA_4", "PSI", "Seções 4.3, 4.5 e 4.7"),
    _link("ANEXO_IV_ETAPA_4", "PLANO_INCIDENTES", "Análise de causa raiz"),
    _link("ANEXO_IV_ETAPA_4", "ATA_RESTAURACAO", "Documento integral"),
    _link("ANEXO_IV_ETAPA_5", "REVERSIBILIDADE", "Documento integral"),
    _link("ANEXO_IV_ETAPA_5", "PSI", "Seção 5 — Revisão e Auditoria"),
    _link("ANEXO_II_4", "PLANO_INCIDENTES", "Documento integral"),
]


# ---------------------------------------------------------------------------
# Deadlines (per requirement × C1/C2/C3)
# ---------------------------------------------------------------------------


def _deadlines_initial(req: str, stage_label: str) -> list[DeadlineSeed]:
    """Etapas iniciais (1 e 2): 90/150/210 dias por classe."""
    return [
        {
            "requirement_code": req,
            "serventia_class": ServentiaClass.C3,
            "value": 90,
            "unit": DeadlineUnit.DIAS,
            "stage_label": stage_label,
            "notes": None,
        },
        {
            "requirement_code": req,
            "serventia_class": ServentiaClass.C2,
            "value": 150,
            "unit": DeadlineUnit.DIAS,
            "stage_label": stage_label,
            "notes": None,
        },
        {
            "requirement_code": req,
            "serventia_class": ServentiaClass.C1,
            "value": 210,
            "unit": DeadlineUnit.DIAS,
            "stage_label": stage_label,
            "notes": None,
        },
    ]


def _deadlines_progressive(req: str, stage_label: str) -> list[DeadlineSeed]:
    """Etapas progressivas (3, 4, 5): 24/30/36 meses por classe."""
    return [
        {
            "requirement_code": req,
            "serventia_class": ServentiaClass.C3,
            "value": 24,
            "unit": DeadlineUnit.MESES,
            "stage_label": stage_label,
            "notes": None,
        },
        {
            "requirement_code": req,
            "serventia_class": ServentiaClass.C2,
            "value": 30,
            "unit": DeadlineUnit.MESES,
            "stage_label": stage_label,
            "notes": None,
        },
        {
            "requirement_code": req,
            "serventia_class": ServentiaClass.C1,
            "value": 36,
            "unit": DeadlineUnit.MESES,
            "stage_label": stage_label,
            "notes": None,
        },
    ]


def _deadlines_at_stage_end(req: str) -> list[DeadlineSeed]:
    return [
        {
            "requirement_code": req,
            "serventia_class": cls,
            "value": None,
            "unit": DeadlineUnit.AO_FINAL_ETAPA,
            "stage_label": "Ao final de cada etapa",
            "notes": None,
        }
        for cls in (ServentiaClass.C3, ServentiaClass.C2, ServentiaClass.C1)
    ]


_DEADLINES_BY_REQ: dict[str, list[DeadlineSeed]] = {
    "ART_1_X": _deadlines_initial("ART_1_X", "Etapa 2"),
    "ART_1_XI": _deadlines_initial("ART_1_XI", "Etapa 2"),
    "ART_3_CAPUT": _deadlines_initial("ART_3_CAPUT", "Etapa 1"),
    "ART_3_P1": _deadlines_initial("ART_3_P1", "Etapa 1"),
    "ART_3_P2": _deadlines_initial("ART_3_P2", "Etapa 2"),
    "ART_4_P2_P3": _deadlines_initial("ART_4_P2_P3", "Etapa 1"),
    "ART_5": _deadlines_initial("ART_5", "Etapa 1"),
    "ART_6_I": _deadlines_initial("ART_6_I", "Etapa 1"),
    "ART_6_III": _deadlines_progressive("ART_6_III", "Etapa 5"),
    "ART_6_IV": _deadlines_initial("ART_6_IV", "Etapa 2"),
    "ART_7_P1": _deadlines_initial("ART_7_P1", "Etapa 1"),
    "ART_7_P2": _deadlines_initial("ART_7_P2", "Etapa 1"),
    "ART_7_P3": _deadlines_initial("ART_7_P3", "Etapa 1"),
    "ART_8": _deadlines_initial("ART_8", "Etapa 2"),
    "ART_9": _deadlines_progressive("ART_9", "Etapa 3"),
    "ART_10": _deadlines_progressive("ART_10", "Etapa 3-4"),
    "ART_11": _deadlines_initial("ART_11", "Etapa 1"),
    "ART_12": _deadlines_progressive("ART_12", "Etapa 3"),
    "ART_12_P9": _deadlines_progressive("ART_12_P9", "Etapa 4"),
    "ART_13": _deadlines_initial("ART_13", "Etapa 1"),
    "ART_15": _deadlines_progressive("ART_15", "Etapa 5"),
    "ART_17": _deadlines_at_stage_end("ART_17"),
    "ART_19": _deadlines_progressive("ART_19", "Etapa 5"),
    "ART_20": _deadlines_initial("ART_20", "Etapas 1-2"),
    "ART_23": _deadlines_progressive("ART_23", "Etapas 1-5"),
    "ANEXO_III_4_8": _deadlines_initial("ANEXO_III_4_8", "Etapa 1"),
    "ANEXO_IV_ETAPA_1": _deadlines_initial("ANEXO_IV_ETAPA_1", "Etapa 1"),
    "ANEXO_IV_ETAPA_2": _deadlines_initial("ANEXO_IV_ETAPA_2", "Etapa 2"),
    "ANEXO_IV_ETAPA_3": _deadlines_progressive("ANEXO_IV_ETAPA_3", "Etapa 3"),
    "ANEXO_IV_ETAPA_4": _deadlines_progressive("ANEXO_IV_ETAPA_4", "Etapa 4"),
    "ANEXO_IV_ETAPA_5": _deadlines_progressive("ANEXO_IV_ETAPA_5", "Etapa 5"),
    "ANEXO_II_4": _deadlines_initial("ANEXO_II_4", "Etapa 1"),
}

SEED_DEADLINES: list[DeadlineSeed] = [
    deadline for items in _DEADLINES_BY_REQ.values() for deadline in items
]


# ---------------------------------------------------------------------------
# Evidence templates
# ---------------------------------------------------------------------------


def _evidence(req: str, items: list[str]) -> list[EvidenceTemplateSeed]:
    return [
        {
            "requirement_code": req,
            "description": desc,
            "sort_order": idx + 1,
            "notes": None,
        }
        for idx, desc in enumerate(items)
    ]


_EVIDENCES_BY_REQ: dict[str, list[str]] = {
    "ART_1_X": [
        "Documento PCN formalizado e aprovado",
        "Definição de RTO e RPO compatíveis com a classe",
        "Cenários de indisponibilidade mapeados",
        "Procedimentos de ativação documentados",
    ],
    "ART_1_XI": [
        "Documento PRD formalizado e aprovado",
        "Procedimentos de restauração detalhados",
        "Testes de restauração documentados",
        "Integração com PCN",
    ],
    "ART_3_CAPUT": [
        "PSI aprovada e publicada",
        "PCN e PRD formalizados",
        "Ata de aprovação pelo responsável",
        "Evidência de divulgação interna",
    ],
    "ART_3_P1": [
        "PSI com seção de continuidade operacional",
        "Diretrizes de preservação de dados integradas",
        "Referência expressa ao PCN e PRD",
    ],
    "ART_3_P2": [
        "Matriz de riscos documentada",
        "Plano de mitigação formalizado",
        "Cronograma de curto prazo (30 dias)",
        "Cronograma de médio prazo (90 dias)",
    ],
    "ART_4_P2_P3": [
        "Inventário de ativos com licenças",
        "Registro de validade de suporte",
        "Notas fiscais e contratos de licenciamento",
    ],
    "ART_5": [
        "Política de controle de acesso formalizada",
        "Registros de MFA implementado",
        "Lista de perfis de acesso individualizados",
        "Vedação expressa a credenciais compartilhadas",
    ],
    "ART_6_I": [
        "14 políticas LGPD formalizadas e aprovadas",
        "Registro de operações de tratamento (ROPA)",
        "Canais de atendimento ao titular implementados",
        "DPO designado",
    ],
    "ART_6_III": [
        "Plano de reversibilidade formalizado",
        "Inventário de ativos completo",
        "Simulação de extração documentada",
        "Cláusulas contratuais de portabilidade",
    ],
    "ART_6_IV": [
        "PCN e PRD formalizados",
        "Cláusula de revisão periódica",
        "Simulações anuais de desastre",
        "Registro de revisões",
    ],
    "ART_7_P1": [
        "ROPA completo e atualizado",
        "Mapeamento de dados pessoais",
        "Identificação de bases legais",
        "Fluxos de dados documentados",
    ],
    "ART_7_P2": [
        "Termo de nomeação assinado",
        "Publicação do DPO no site/cartório",
        "Cartaz com dados do DPO na serventia",
        "Canal de contato do DPO ativo",
    ],
    "ART_7_P3": [
        "Plano de resposta a incidentes formalizado",
        "Guia prático para equipe da serventia",
        "Formulários de comunicação à ANPD",
        "Modelo de análise de causa raiz",
        "Registro de medidas corretivas",
    ],
    "ART_8": [
        "PSI com diretrizes tecnológicas",
        "Documento de arquitetura tecnológica",
        "Topologia de rede documentada",
        "Configuração de firewall e segmentação",
    ],
    "ART_9": [
        "Política de criptografia na PSI",
        "Configuração de TLS 1.2+ documentada",
        "Criptografia AES-256 em repouso",
        "Inventário de chaves e certificados",
        "Política de rotação de chaves",
    ],
    "ART_10": [
        "Política de logs na PSI",
        "Configuração de logs nos sistemas",
        "Mecanismo de proteção contra alteração",
        "Sincronização de tempo (NTP)",
        "Retenção de 5 anos documentada",
    ],
    "ART_11": [
        "Plano de resposta a incidentes",
        "Guia prático operacional",
        "Classificação de gravidade definida",
        "Fluxo de comunicação à Corregedoria",
        "Modelo de análise de causa raiz",
    ],
    "ART_12": [
        "Política de backup formalizada",
        "Rotinas automatizadas configuradas",
        "Armazenamento off-site implementado",
        "Logs de monitoramento",
        "Atas de teste de restauração",
    ],
    "ART_12_P9": [
        "Ata de teste de restauração assinada",
        "Resultado quantitativo do teste (RTO/RPO observado)",
        "Registro de falhas e medidas corretivas",
    ],
    "ART_13": [
        "Cláusulas contratuais modelo",
        "Checklist de revisão contratual",
        "Plano de reversibilidade",
        "Avaliação de fornecedores documentada",
    ],
    "ART_15": [
        "Cláusula contratual de reversibilidade",
        "Teste de extração documentado",
        "Formato interoperável definido",
        "Ausência de lock-in contratual",
    ],
    "ART_17": [
        "Modelo de declaração por etapa",
        "Síntese do dossiê técnico",
        "Registro no Sistema Justiça Aberta",
    ],
    "ART_19": [
        "Padrões de interoperabilidade definidos",
        "Formatos abertos adotados (PDF/A, XML)",
        "Canais seguros implementados",
        "Logs de integração",
    ],
    "ART_20": [
        "Cronograma detalhado por classe",
        "Marcos de implementação definidos",
        "Responsáveis atribuídos",
    ],
    "ART_23": [
        "Cronograma global com 5 etapas",
        "Marcos cumulativos definidos",
        "Acompanhamento progressivo",
    ],
    "ANEXO_III_4_8": [
        "Procedimento de resposta ao titular",
        "Cartazes afixados na serventia",
        "FAQ para colaboradores",
        "ROPA atualizado",
        "DPO nomeado e publicado",
    ],
    "ANEXO_IV_ETAPA_1": [
        "PSI aprovada e divulgada",
        "ROPA concluído",
        "DPO nomeado",
        "Inventário completo",
        "Contratos revisados",
        "MFA implementado",
    ],
    "ANEXO_IV_ETAPA_2": [
        "PCN e PRD com RTO/RPO",
        "Documento de arquitetura",
        "Laudo de aterramento",
        "Proteção de endpoint implementada",
    ],
    "ANEXO_IV_ETAPA_3": [
        "Criptografia implementada",
        "Rotinas de backup automatizadas",
        "Alertas de monitoramento",
        "Firewall e IPS/IDS",
        "Logs imutáveis",
    ],
    "ANEXO_IV_ETAPA_4": [
        "Relatório de conformidade de auditoria",
        "Rotina de atualizações",
        "Gestão de vulnerabilidades",
        "Atas de simulação de desastre",
        "Atas de teste de restauração",
    ],
    "ANEXO_IV_ETAPA_5": [
        "Simulação de extração documentada",
        "Padrões abertos implementados",
        "Registro de capacitações",
        "PSI revisada periodicamente",
        "Registros auditáveis mantidos",
    ],
    "ANEXO_II_4": [
        "Plano de resposta a incidentes vinculado ao Anexo II",
        "Fluxos de comunicação interna documentados",
        "Mapa de papéis e responsabilidades em incidentes",
    ],
}

SEED_EVIDENCE_TEMPLATES: list[EvidenceTemplateSeed] = [
    item
    for req_code in _EVIDENCES_BY_REQ
    for item in _evidence(req_code, _EVIDENCES_BY_REQ[req_code])
]


__all__ = [
    "DeadlineSeed",
    "EvidenceTemplateSeed",
    "PolicySeed",
    "RequirementPolicySeed",
    "RequirementSeed",
    "SEED_DEADLINES",
    "SEED_EVIDENCE_TEMPLATES",
    "SEED_META",
    "SEED_POLICIES",
    "SEED_REQUIREMENT_POLICIES",
    "SEED_REQUIREMENTS",
    "SeedMetaInfo",
]
