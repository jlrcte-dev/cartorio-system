"""Seed runner para a Matriz INOVA V1.

- Determinístico
- Idempotente por código de requisito/política
- Calcula sha256 do dataset serializado
- Se checksum igual ao registrado, não duplica/recria registros
- Não roda em alembic upgrade — chamado pelo operador
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.compliance.models import (
    ComplianceEvidenceTemplate,
    CompliancePolicyDocument,
    ComplianceRequirement,
    ComplianceRequirementDeadline,
    ComplianceRequirementPolicy,
    ComplianceSeedMeta,
)
from app.modules.compliance.seed_data import (
    SEED_DEADLINES,
    SEED_EVIDENCE_TEMPLATES,
    SEED_META,
    SEED_POLICIES,
    SEED_REQUIREMENT_POLICIES,
    SEED_REQUIREMENTS,
)


def compute_checksum() -> str:
    """Hash sha256 estável do dataset serializado.

    Ordena listas para neutralizar a ordem de definição e produz JSON
    canônico (sort_keys, sem espaços supérfluos).
    """

    payload: dict[str, Any] = {
        "seed_name": SEED_META["seed_name"],
        "seed_version": SEED_META["seed_version"],
        "requirements": sorted(
            (
                {
                    "code": r["code"],
                    "source": r["source"].value,
                    "article_label": r["article_label"],
                    "article_text": r["article_text"],
                    "classification": r["classification"].value,
                    "stage": r["stage"].value,
                    "notes": r["notes"],
                }
                for r in SEED_REQUIREMENTS
            ),
            key=lambda x: x["code"],
        ),
        "policies": sorted(
            (
                {
                    "code": p["code"],
                    "title": p["title"],
                    "kind": p["kind"].value,
                    "classification": p["classification"].value,
                    "inova_filename": p["inova_filename"],
                    "description": p["description"],
                }
                for p in SEED_POLICIES
            ),
            key=lambda x: x["code"],
        ),
        "requirement_policies": sorted(
            (
                {
                    "requirement_code": rp["requirement_code"],
                    "policy_code": rp["policy_code"],
                    "policy_section_notes": rp["policy_section_notes"],
                }
                for rp in SEED_REQUIREMENT_POLICIES
            ),
            key=lambda x: (x["requirement_code"], x["policy_code"], x["policy_section_notes"]),
        ),
        "deadlines": sorted(
            (
                {
                    "requirement_code": d["requirement_code"],
                    "serventia_class": d["serventia_class"].value,
                    "value": d["value"],
                    "unit": d["unit"].value,
                    "stage_label": d["stage_label"],
                    "notes": d["notes"],
                }
                for d in SEED_DEADLINES
            ),
            key=lambda x: (x["requirement_code"], x["serventia_class"]),
        ),
        "evidence_templates": sorted(
            (
                {
                    "requirement_code": e["requirement_code"],
                    "description": e["description"],
                    "sort_order": e["sort_order"],
                    "notes": e["notes"],
                }
                for e in SEED_EVIDENCE_TEMPLATES
            ),
            key=lambda x: (x["requirement_code"], x["sort_order"]),
        ),
    }
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _upsert_requirements(db: Session) -> dict[str, ComplianceRequirement]:
    by_code: dict[str, ComplianceRequirement] = {
        r.code: r for r in db.scalars(select(ComplianceRequirement)).all()
    }
    for spec in SEED_REQUIREMENTS:
        existing = by_code.get(spec["code"])
        if existing is None:
            obj = ComplianceRequirement(
                code=spec["code"],
                source=spec["source"],
                article_label=spec["article_label"],
                article_text=spec["article_text"],
                classification=spec["classification"],
                stage=spec["stage"],
                notes=spec["notes"],
            )
            db.add(obj)
            by_code[spec["code"]] = obj
        else:
            existing.source = spec["source"]
            existing.article_label = spec["article_label"]
            existing.article_text = spec["article_text"]
            existing.classification = spec["classification"]
            existing.stage = spec["stage"]
            existing.notes = spec["notes"]
    db.flush()
    return by_code


def _upsert_policies(db: Session) -> dict[str, CompliancePolicyDocument]:
    by_code: dict[str, CompliancePolicyDocument] = {
        p.code: p for p in db.scalars(select(CompliancePolicyDocument)).all()
    }
    for spec in SEED_POLICIES:
        existing = by_code.get(spec["code"])
        if existing is None:
            obj = CompliancePolicyDocument(
                code=spec["code"],
                title=spec["title"],
                kind=spec["kind"],
                classification=spec["classification"],
                inova_filename=spec["inova_filename"],
                description=spec["description"],
            )
            db.add(obj)
            by_code[spec["code"]] = obj
        else:
            existing.title = spec["title"]
            existing.kind = spec["kind"]
            existing.classification = spec["classification"]
            existing.inova_filename = spec["inova_filename"]
            existing.description = spec["description"]
    db.flush()
    return by_code


def _sync_requirement_policies(
    db: Session,
    requirements: dict[str, ComplianceRequirement],
    policies: dict[str, CompliancePolicyDocument],
) -> int:
    existing = {
        (link.requirement_id, link.policy_id, link.policy_section_notes): link
        for link in db.scalars(select(ComplianceRequirementPolicy)).all()
    }
    desired_keys: set[tuple[int, int, str]] = set()
    for spec in SEED_REQUIREMENT_POLICIES:
        req = requirements.get(spec["requirement_code"])
        pol = policies.get(spec["policy_code"])
        if req is None or pol is None:
            continue
        notes = spec["policy_section_notes"]
        key = (req.id, pol.id, notes)
        desired_keys.add(key)
        if key in existing:
            continue
        db.add(
            ComplianceRequirementPolicy(
                requirement_id=req.id,
                policy_id=pol.id,
                policy_section_notes=notes,
            )
        )
    db.flush()
    return len(desired_keys)


def _sync_deadlines(
    db: Session,
    requirements: dict[str, ComplianceRequirement],
) -> int:
    existing = {
        (d.requirement_id, d.serventia_class): d
        for d in db.scalars(select(ComplianceRequirementDeadline)).all()
    }
    desired = 0
    for spec in SEED_DEADLINES:
        req = requirements.get(spec["requirement_code"])
        if req is None:
            continue
        desired += 1
        key = (req.id, spec["serventia_class"])
        current = existing.get(key)
        if current is None:
            db.add(
                ComplianceRequirementDeadline(
                    requirement_id=req.id,
                    serventia_class=spec["serventia_class"],
                    value=spec["value"],
                    unit=spec["unit"],
                    stage_label=spec["stage_label"],
                    notes=spec["notes"],
                )
            )
        else:
            current.value = spec["value"]
            current.unit = spec["unit"]
            current.stage_label = spec["stage_label"]
            current.notes = spec["notes"]
    db.flush()
    return desired


def _sync_evidence_templates(
    db: Session,
    requirements: dict[str, ComplianceRequirement],
) -> int:
    existing = {
        (e.requirement_id, e.sort_order): e
        for e in db.scalars(select(ComplianceEvidenceTemplate)).all()
    }
    desired = 0
    for spec in SEED_EVIDENCE_TEMPLATES:
        req = requirements.get(spec["requirement_code"])
        if req is None:
            continue
        desired += 1
        key = (req.id, spec["sort_order"])
        current = existing.get(key)
        if current is None:
            db.add(
                ComplianceEvidenceTemplate(
                    requirement_id=req.id,
                    description=spec["description"],
                    sort_order=spec["sort_order"],
                    notes=spec["notes"],
                )
            )
        else:
            current.description = spec["description"]
            current.notes = spec["notes"]
    db.flush()
    return desired


def run_seed(db: Session, *, seeded_by: str = "gestor") -> ComplianceSeedMeta:
    """Executa o seed `matriz_v1` de forma idempotente.

    Se houver `ComplianceSeedMeta` com mesmo `seed_name` e `data_checksum`
    igual ao calculado, retorna sem alterações. Caso contrário, sincroniza
    requisitos, políticas, vínculos, prazos e evidências.
    """

    checksum = compute_checksum()
    meta = db.scalar(
        select(ComplianceSeedMeta).where(ComplianceSeedMeta.seed_name == SEED_META["seed_name"])
    )

    if meta is not None and meta.data_checksum == checksum:
        return meta

    requirements = _upsert_requirements(db)
    policies = _upsert_policies(db)
    rp_count = _sync_requirement_policies(db, requirements, policies)
    deadline_count = _sync_deadlines(db, requirements)
    evidence_count = _sync_evidence_templates(db, requirements)

    if meta is None:
        meta = ComplianceSeedMeta(
            seed_name=SEED_META["seed_name"],
            seed_version=SEED_META["seed_version"],
            source_document=SEED_META["source_document"],
            source_file_reference=SEED_META["source_file_reference"],
            record_count_requirements=len(SEED_REQUIREMENTS),
            record_count_policies=len(SEED_POLICIES),
            record_count_requirement_policies=rp_count,
            record_count_deadlines=deadline_count,
            record_count_evidence_templates=evidence_count,
            data_checksum=checksum,
            seeded_by=seeded_by,
            notes=SEED_META["notes"],
        )
        db.add(meta)
    else:
        meta.seed_version = SEED_META["seed_version"]
        meta.source_document = SEED_META["source_document"]
        meta.source_file_reference = SEED_META["source_file_reference"]
        meta.record_count_requirements = len(SEED_REQUIREMENTS)
        meta.record_count_policies = len(SEED_POLICIES)
        meta.record_count_requirement_policies = rp_count
        meta.record_count_deadlines = deadline_count
        meta.record_count_evidence_templates = evidence_count
        meta.data_checksum = checksum
        meta.seeded_by = seeded_by
        meta.notes = SEED_META["notes"]

    db.flush()
    return meta


def main() -> None:  # pragma: no cover - chamado manualmente pelo operador
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        meta = run_seed(session)
        session.commit()
        print(
            {
                "seed_name": meta.seed_name,
                "seed_version": meta.seed_version,
                "checksum": meta.data_checksum,
                "requirements": meta.record_count_requirements,
                "policies": meta.record_count_policies,
                "requirement_policies": meta.record_count_requirement_policies,
                "deadlines": meta.record_count_deadlines,
                "evidence_templates": meta.record_count_evidence_templates,
            }
        )


if __name__ == "__main__":  # pragma: no cover
    main()
