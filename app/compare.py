from __future__ import annotations

import re
from typing import Any, Iterable

from app.models import ColumnInfo, CompareSummary, DiffRow, DiffStatus

KEY_NAME_HINTS = (
    "section",
    "inisection",
    "inifile",
    "filename",
    "file",
    "ident",
    "identifier",
    "entry",
    "entryname",
    "key",
    "setting",
    "settingname",
    "name",
    "item",
    "userid",
    "user",
    "company",
    "machine",
    "computer",
)

VALUE_NAME_HINTS = (
    "value",
    "entryvalue",
    "settingvalue",
    "inivalue",
    "stringvalue",
    "data",
    "content",
    "text",
)

ID_NAME_HINTS = ("id", "rowid", "pk", "recid", "settingid")


def normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if type(value).__name__ == "Decimal":
        return str(value)
    return value


def jsonable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: normalize_value(value) for key, value in row.items()}


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _matches_hint(norm: str, hint: str) -> bool:
    return norm == hint or norm.startswith(hint) or norm.endswith(hint)


def guess_key_and_value_columns(
    columns: Iterable[ColumnInfo | str],
    primary_key: Iterable[str] | None = None,
) -> tuple[list[str], list[str]]:
    names = [col.name if isinstance(col, ColumnInfo) else col for col in columns]
    if not names:
        return [], []

    by_norm = {_norm_name(name): name for name in names}
    pk = [name for name in (primary_key or []) if name in names]

    value_columns = [
        name
        for name in names
        if any(_norm_name(name).endswith(hint) or _norm_name(name) == hint for hint in VALUE_NAME_HINTS)
    ]
    if not value_columns:
        for hint in ("val", "data"):
            match = by_norm.get(hint)
            if match:
                value_columns.append(match)

    identity_like = [name for name in names if _norm_name(name) in ID_NAME_HINTS]

    key_columns: list[str] = []
    for name in names:
        norm = _norm_name(name)
        if name in value_columns:
            continue
        if name in identity_like and len(names) > 2:
            continue
        if any(_matches_hint(norm, hint) for hint in KEY_NAME_HINTS):
            key_columns.append(name)

    if not key_columns:
        usable_pk = [name for name in pk if name not in value_columns]
        if usable_pk and not (len(usable_pk) == 1 and _norm_name(usable_pk[0]) in ID_NAME_HINTS):
            key_columns = usable_pk
        else:
            key_columns = [name for name in names if name not in value_columns and name not in identity_like]

    if not key_columns:
        key_columns = [names[0]]

    if not value_columns:
        value_columns = [name for name in names if name not in key_columns]
    if not value_columns:
        value_columns = names[-1:]
        key_columns = [name for name in names if name not in value_columns] or names[:1]

    # Preserve original column order.
    key_columns = [name for name in names if name in key_columns]
    value_columns = [name for name in names if name in value_columns]
    return key_columns, value_columns


def row_key(row: dict[str, Any], key_columns: list[str]) -> tuple[Any, ...]:
    return tuple(_key_part(row.get(column)) for column in key_columns)


def _key_part(value: Any) -> Any:
    normalized = normalize_value(value)
    if isinstance(normalized, str):
        return normalized.casefold()
    return normalized


def values_equal(left: dict[str, Any] | None, right: dict[str, Any] | None, value_columns: list[str]) -> bool:
    if left is None or right is None:
        return False
    for column in value_columns:
        if _comparable(left.get(column)) != _comparable(right.get(column)):
            return False
    return True


def _comparable(value: Any) -> Any:
    normalized = normalize_value(value)
    if isinstance(normalized, str):
        return normalized.strip()
    return normalized


def compare_tables(
    left_rows: list[dict[str, Any]],
    right_rows: list[dict[str, Any]],
    key_columns: list[str],
    value_columns: list[str],
    include_identical: bool = True,
) -> tuple[list[DiffRow], CompareSummary, list[str]]:
    warnings: list[str] = []
    left_map, left_dupes = _index_rows(left_rows, key_columns)
    right_map, right_dupes = _index_rows(right_rows, key_columns)

    if left_dupes:
        warnings.append(f"Left instance has {left_dupes} duplicate key(s); the first row for each key was used.")
    if right_dupes:
        warnings.append(f"Right instance has {right_dupes} duplicate key(s); the first row for each key was used.")

    all_keys = sorted(
        set(left_map) | set(right_map),
        key=lambda parts: tuple("" if part is None else str(part) for part in parts),
    )

    summary = CompareSummary(
        duplicate_keys_left=left_dupes,
        duplicate_keys_right=right_dupes,
    )
    rows: list[DiffRow] = []

    for key in all_keys:
        left = left_map.get(key)
        right = right_map.get(key)
        status = _status(left, right, value_columns)
        if status == "identical":
            summary.identical += 1
        elif status == "changed":
            summary.changed += 1
        elif status == "left_only":
            summary.left_only += 1
        else:
            summary.right_only += 1

        if status == "identical" and not include_identical:
            continue

        key_payload = {}
        source = left or right or {}
        for column in key_columns:
            key_payload[column] = normalize_value(source.get(column))

        rows.append(
            DiffRow(
                status=status,
                key=key_payload,
                left=_project(left, value_columns) if left is not None else None,
                right=_project(right, value_columns) if right is not None else None,
            )
        )

    summary.total = summary.identical + summary.changed + summary.left_only + summary.right_only
    return rows, summary, warnings


def _index_rows(
    rows: list[dict[str, Any]],
    key_columns: list[str],
) -> tuple[dict[tuple[Any, ...], dict[str, Any]], int]:
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    duplicates = 0
    for row in rows:
        key = row_key(row, key_columns)
        if key in indexed:
            duplicates += 1
            continue
        indexed[key] = row
    return indexed, duplicates


def _status(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
    value_columns: list[str],
) -> DiffStatus:
    if left is not None and right is None:
        return "left_only"
    if left is None and right is not None:
        return "right_only"
    if values_equal(left, right, value_columns):
        return "identical"
    return "changed"


def _project(row: dict[str, Any], columns: list[str]) -> dict[str, Any]:
    return {column: normalize_value(row.get(column)) for column in columns}
