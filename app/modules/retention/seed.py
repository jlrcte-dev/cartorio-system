"""Seed inicial de regras de temporalidade — Sprint retention-1A.

Conteúdo extraído manualmente do anexo do Provimento CNJ 50/2015 (compilado),
limitado a linhas com legibilidade confirmada. Cobre: guarda permanente,
1 ano, 5 anos, 10 anos, eliminação condicionada a digitalização/microfilmagem,
RCPN, Ofício de Notas e documentos comuns/administrativos.

A persistência é idempotente por (codigo, documento). Não roda em
`alembic upgrade` — o operador decide quando popular.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.retention import repository
from app.modules.retention.enums import NormSource, RetentionPhaseKind
from app.modules.retention.schemas import RetentionRuleIn

SOURCE_NORM = NormSource.PROVIMENTO_CNJ_50_2015.value
SOURCE_VERSION = "COMPILADO_LOCAL"
SOURCE_FILE = (
    "_local_data/serventia_docs/Atos Normativos e Administrativos/"
    "02 - Provimentos CNJ/Provimento 50-2015-compilado.pdf"
)
SOURCE_NOTES = (
    "Arquivo local indicado como compilado. "
    "Redação consolidada deve ser validada antes de uso jurídico definitivo."
)


def _rule(
    *,
    codigo: str,
    assunto: str,
    documento: str,
    fase_corrente_text: str,
    fase_corrente_kind: RetentionPhaseKind,
    fase_corrente_years: int | None = None,
    fase_corrente_months: int | None = None,
    eliminacao: bool = False,
    guarda_permanente: bool = False,
    requer_microfilmagem: bool = False,
    requer_digitalizacao: bool = False,
    observacao: str | None = None,
    base_legal: str | None = None,
    alteracoes: str | None = None,
) -> RetentionRuleIn:
    return RetentionRuleIn(
        codigo=codigo,
        assunto=assunto,
        documento=documento,
        fase_corrente_text=fase_corrente_text,
        fase_corrente_kind=fase_corrente_kind,
        fase_corrente_years=fase_corrente_years,
        fase_corrente_months=fase_corrente_months,
        eliminacao=eliminacao,
        guarda_permanente=guarda_permanente,
        requer_microfilmagem=requer_microfilmagem,
        requer_digitalizacao=requer_digitalizacao,
        observacao=observacao,
        base_legal=base_legal,
        alteracoes=alteracoes,
        source_norm=SOURCE_NORM,
        source_version=SOURCE_VERSION,
        source_file=SOURCE_FILE,
        source_code=codigo,
        source_notes=SOURCE_NOTES,
    )


# ---------------------------------------------------------------------------
# Regras seedadas — apenas linhas com legibilidade confirmada no PDF compilado.
# ---------------------------------------------------------------------------

SEED_RULES: list[RetentionRuleIn] = [
    # --- Registro Civil das Pessoas Naturais (3-1) ---
    _rule(
        codigo="3-1-1-1",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Livro borrão",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
        base_legal="Lei nº 6.015/73",
    ),
    _rule(
        codigo="3-1-1-2",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Livro de editais e proclamas",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
        base_legal="Lei nº 6.015/73",
    ),
    _rule(
        codigo="3-1-1-3",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Livro de registro de nascimento — assento",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
        base_legal="Lei nº 6.015/73",
    ),
    _rule(
        codigo="3-1-1-4",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Livro de registro de óbito — assento",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
        base_legal="Lei nº 6.015/73",
    ),
    _rule(
        codigo="3-1-1-5",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Livro de registro de casamento — assento",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
        base_legal="Lei nº 6.015/73",
    ),
    _rule(
        codigo="3-1-2",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Declaração de Nascido Vivo (DNV)",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
        observacao="Documento controlado pelo Ministério da Saúde.",
    ),
    _rule(
        codigo="3-1-3",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Declaração de Óbito (DO)",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
        observacao="Documento controlado pelo Ministério da Saúde.",
    ),
    _rule(
        codigo="3-1-5-1",
        assunto="Registro Civil das Pessoas Naturais",
        documento="Retificações de qualquer espécie e processos judiciais",
        fase_corrente_text="5 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=5,
        eliminacao=True,
        base_legal="Art. 109 § 11 da Lei nº 6.015/73",
    ),
    # --- Casamento (3-1-6) — eliminação só após digitalização/microfilmagem ---
    _rule(
        codigo="3-1-6-2-1",
        assunto="Registro Civil das Pessoas Naturais — Casamento",
        documento="Casamentos celebrados",
        fase_corrente_text="3 anos após data do registro",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=3,
        eliminacao=True,
        requer_microfilmagem=True,
        requer_digitalizacao=True,
        observacao=(
            "Eliminação só permitida se a documentação estiver digitalizada ou "
            "microfilmada e cumprir requisitos do art. 8º da Lei nº 6.015/73."
        ),
        base_legal="Art. 8º da Lei nº 6.015/73",
    ),
    # --- Registro de Imóveis (3-2) ---
    _rule(
        codigo="3-2-1-1",
        assunto="Registro de Imóveis",
        documento="Indicador real",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
    ),
    _rule(
        codigo="3-2-1-2",
        assunto="Registro de Imóveis",
        documento="Indicador pessoal",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
    ),
    # --- Tabelionato de Protesto (3-4) ---
    _rule(
        codigo="3-4-1-1",
        assunto="Tabelionato de Protesto",
        documento="Protocolo",
        fase_corrente_text="5 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=5,
        eliminacao=True,
        base_legal="Art. 35 § 2º da Lei nº 9.492/97",
    ),
    _rule(
        codigo="3-4-1-2",
        assunto="Tabelionato de Protesto",
        documento="Registro de protesto",
        fase_corrente_text="10 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=10,
        eliminacao=True,
        base_legal="Art. 35 § 2º da Lei nº 9.492/97",
    ),
    # --- Ofício de Notas (3-5) ---
    _rule(
        codigo="3-5-1-2",
        assunto="Ofício de Notas",
        documento="Testamentos públicos",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
    ),
    _rule(
        codigo="3-5-1-4",
        assunto="Ofício de Notas",
        documento="Escrituras e atas notariais",
        fase_corrente_text="Permanente",
        fase_corrente_kind=RetentionPhaseKind.PERMANENT,
        guarda_permanente=True,
    ),
    _rule(
        codigo="3-5-3-1",
        assunto="Ofício de Notas",
        documento="Publicações em jornais (Diário Oficial)",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
    ),
    _rule(
        codigo="3-5-3-8",
        assunto="Ofício de Notas",
        documento="Documentos que instruíram o registro",
        fase_corrente_text="10 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=10,
        eliminacao=True,
        base_legal="Art. 205 do Código Civil",
    ),
    # --- Documentos Comuns (3-8) ---
    _rule(
        codigo="3-8-2",
        assunto="Documentos Comuns",
        documento="Certidões recebidas para registros e averbações",
        fase_corrente_text="10 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=10,
        eliminacao=True,
        requer_microfilmagem=True,
        requer_digitalizacao=True,
        observacao=(
            "Eliminação só permitida se a documentação estiver microfilmada ou digitalizada."
        ),
    ),
    _rule(
        codigo="3-8-5",
        assunto="Documentos Comuns",
        documento="Publicações em jornais (Diário Oficial)",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
    ),
    _rule(
        codigo="3-8-6",
        assunto="Documentos Comuns",
        documento="Requerimentos de registro",
        fase_corrente_text="1 ano",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=1,
        eliminacao=True,
    ),
    # --- Administrativo do cartório (3-9) ---
    _rule(
        codigo="3-9-2",
        assunto="Documentos administrativos do cartório",
        documento="Certidão não procurada pelas partes — cópia retida",
        fase_corrente_text="3 meses",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_months=3,
        eliminacao=True,
    ),
    _rule(
        codigo="3-9-4",
        assunto="Documentos administrativos do cartório",
        documento="Ofícios e requerimentos",
        fase_corrente_text="5 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=5,
        eliminacao=True,
    ),
    _rule(
        codigo="3-9-5",
        assunto="Documentos administrativos do cartório",
        documento="Relatórios de correição",
        fase_corrente_text="5 anos",
        fase_corrente_kind=RetentionPhaseKind.DURATION,
        fase_corrente_years=5,
        eliminacao=True,
    ),
]


def run(session: Session) -> dict[str, int]:
    """Executa o seed de forma idempotente. Retorna contagem antes/depois."""

    before = repository.count(session)
    for payload in SEED_RULES:
        repository.upsert(session, payload)
    session.flush()
    after = repository.count(session)
    return {
        "rules_in_seed": len(SEED_RULES),
        "count_before": before,
        "count_after": after,
        "inserted_or_updated": len(SEED_RULES),
    }


def main() -> None:  # pragma: no cover - chamado manualmente pelo operador
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        result = run(session)
        session.commit()
        print(result)


if __name__ == "__main__":  # pragma: no cover
    main()
