from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _register_models() -> None:
    """Importa modelos para popular Base.metadata.

    Mantido em função para evitar import circular em tempo de import do módulo.
    """
    from app.modules.audit.findings import models as _audit_findings_models  # noqa: F401
    from app.modules.finance import models as _finance_models  # noqa: F401


_register_models()
