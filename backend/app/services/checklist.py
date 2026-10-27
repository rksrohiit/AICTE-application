"""Configurable AICTE checklist loading and evaluation.

The checklist is deliberately data-driven: rules live in ``rules/*.yaml`` and
the evaluator returns evidence for every decision so results remain suitable
for officer review and audit.
"""

from __future__ import annotations

import difflib
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from app.models.validation import FindingStatus

RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


def load_rules(application_type: str | None = None) -> list[dict[str, Any]]:
    """Load configured rules, optionally filtering by application type."""
    rules: list[dict[str, Any]] = []
    for path in sorted(RULES_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(data, dict):
            file_type = data.get("application_type") or data.get("applies_to")
            if application_type and file_type and file_type not in {
                application_type,
                application_type.lower(),
                application_type.replace("_", " "),
            }:
                continue
            entries = data.get("rules", [])
        else:
            entries = data if isinstance(data, list) else []
        rules.extend(item for item in entries if isinstance(item, dict))
    return rules


def _field_value(document: Any, name: str) -> Any:
    fields = (document.extracted_data or {}).get("fields", {})
    value = fields.get(name)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _documents_of(documents: Iterable[Any], doc_type: str | None) -> list[Any]:
    if not doc_type:
        return list(documents)
    return [doc for doc in documents if getattr(doc.doc_type, "value", doc.doc_type) == doc_type]


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value).strip()


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def _result(status: FindingStatus, message: str, evidence: str | None = None, document_id: Any = None) -> dict[str, Any]:
    return {
        "status": status,
        "message": message,
        "evidence": evidence,
        "document_id": str(document_id) if document_id else None,
    }


def evaluate_rule(rule: dict[str, Any], app: Any, documents: list[Any]) -> dict[str, Any]:
    """Evaluate one YAML rule against an application and its documents."""
    category = str(rule.get("category", "GENERAL")).upper()
    check_type = str(rule.get("check_type", "")).lower()
    doc_type = rule.get("document_type") or rule.get("required_doc_type")
    matching = _documents_of(documents, doc_type)

    if category in {"COMPLETENESS", "DOCUMENT_PRESENCE"} or check_type == "document_present":
        if matching:
            return _result(
                FindingStatus.PASS,
                f"Required document '{doc_type}' is present.",
                f"Document ID: {matching[0].id}",
                matching[0].id,
            )
        return _result(
            FindingStatus.FAIL,
            rule.get("message", f"Required document '{doc_type}' is missing."),
            "No document of this type was uploaded.",
        )

    if category == "OCR_COMPLETE" or check_type == "ocr_complete":
        if not matching:
            return _result(FindingStatus.SKIPPED, f"Document '{doc_type}' was not uploaded.")
        status = getattr(matching[0].ocr_status, "value", matching[0].ocr_status)
        return _result(
            FindingStatus.PASS if status == "COMPLETE" else FindingStatus.FAIL,
            f"OCR status for '{doc_type}': {status}.",
            f"Document ID: {matching[0].id}",
            matching[0].id,
        )

    if category == "VALIDITY" or check_type == "date_not_expired":
        if not matching:
            return _result(FindingStatus.SKIPPED, f"Document '{doc_type}' was not uploaded.")
        document = matching[0]
        value = _as_date(_field_value(document, rule.get("field")))
        if value is None:
            return _result(FindingStatus.WARN, rule.get("message", "A validity date could not be extracted."), "Date field missing or unreadable.", document.id)
        today = datetime.now(timezone.utc).date()
        max_age = rule.get("max_age_days")
        expired = value < today or (max_age is not None and value < today - timedelta(days=int(max_age)))
        return _result(
            FindingStatus.FAIL if expired else FindingStatus.PASS,
            rule.get("message", "Document validity checked."),
            f"{rule.get('field')}: {value.isoformat()}",
            document.id,
        )

    if category == "FORMAT":
        if not matching:
            return _result(FindingStatus.SKIPPED, f"Document '{doc_type}' was not uploaded.")
        document = matching[0]
        value = _field_value(document, rule.get("field"))
        valid = True
        evidence = f"{rule.get('field')}: {_as_text(value) or '<empty>'}"
        if check_type == "field_value_in_set":
            valid = _as_text(value).upper() in {str(item).upper() for item in rule.get("allowed_values", [])}
        elif check_type == "regex_match":
            valid = bool(re.fullmatch(str(rule.get("pattern", "")), _as_text(value)))
        elif check_type == "numeric_min":
            number = _as_number(value)
            valid = number is not None and number >= float(rule.get("min_value", 0))
        elif check_type in {"field_present", "required"}:
            valid = bool(value)
        return _result(FindingStatus.PASS if valid else FindingStatus.FAIL, rule.get("message", "Format check failed."), evidence, document.id)

    if category == "COMPLIANCE":
        if not matching:
            return _result(FindingStatus.SKIPPED, f"Document '{doc_type}' was not uploaded.")
        document = matching[0]
        if check_type == "ratio_min":
            numerator = _as_number(_field_value(document, rule.get("numerator_field")))
            denominator = _as_number(_field_value(document, rule.get("denominator_field")))
            ratio = numerator / denominator if numerator is not None and denominator else None
            valid = ratio is not None and ratio >= float(rule.get("min_ratio", 0))
            evidence = f"ratio: {ratio:.3f}" if ratio is not None else "ratio: unavailable"
        else:
            value = _field_value(document, rule.get("field"))
            valid = _as_text(value).upper() in {str(item).upper() for item in rule.get("allowed_values", [])}
            evidence = f"{rule.get('field')}: {_as_text(value) or '<empty>'}"
        return _result(FindingStatus.PASS if valid else FindingStatus.FAIL, rule.get("message", "Compliance check failed."), evidence, document.id)

    if category == "CONSISTENCY" or check_type.startswith("cross_doc"):
        source_types = rule.get("source_documents", [])
        values: list[tuple[Any, Any, str]] = []
        for source_type in source_types:
            source_docs = _documents_of(documents, source_type)
            if source_docs:
                values.append((source_docs[0], _field_value(source_docs[0], rule.get("field")), source_type))
        if len(values) < 2:
            return _result(FindingStatus.SKIPPED, "Not enough source documents contain this field.", "At least two source documents are required.")
        rendered = [(_as_text(value), source_type, doc.id) for doc, value, source_type in values]
        baseline = rendered[0][0]
        comparator = rule.get("comparator", "exact_match")
        if comparator == "fuzzy_match":
            threshold = float(rule.get("threshold", 0.9))
            matches = all(difflib.SequenceMatcher(None, baseline.lower(), item[0].lower()).ratio() >= threshold for item in rendered[1:])
        elif comparator == "lte":
            numbers = [_as_number(item[0]) for item in rendered]
            matches = all(number is not None for number in numbers) and numbers[0] <= max(numbers[1:])
        else:
            matches = all(item[0].casefold() == baseline.casefold() for item in rendered[1:])
        evidence = "; ".join(f"{source}: {value or '<empty>'}" for value, source, _ in rendered)
        return _result(FindingStatus.PASS if matches else FindingStatus.FAIL, rule.get("message", "Cross-document values are inconsistent."), evidence, rendered[0][2])

    return _result(FindingStatus.SKIPPED, f"Rule category '{category}' is not implemented.")


def evaluate_checklist(app: Any, documents: list[Any]) -> list[dict[str, Any]]:
    """Return all configured rule evaluations for an application."""
    return [
        {
            "rule_id": rule.get("id", "UNKNOWN"),
            "rule_name": rule.get("name", rule.get("id", "Unknown rule")),
            "category": rule.get("category", "GENERAL"),
            "severity": str(rule.get("severity", "MEDIUM")).upper(),
            "description": rule.get("message") or rule.get("description"),
            **evaluate_rule(rule, app, documents),
        }
        for rule in load_rules(getattr(getattr(app, "application_type", None), "value", None))
    ]
