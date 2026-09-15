from app.compare import compare_tables, guess_key_and_value_columns
from app.models import ColumnInfo


def test_guess_classic_ini_columns():
    columns = [
        ColumnInfo(name="SECTION", type="varchar", primary_key=True),
        ColumnInfo(name="IDENT", type="varchar", primary_key=True),
        ColumnInfo(name="VALUE", type="varchar"),
    ]
    keys, values = guess_key_and_value_columns(columns, ["SECTION", "IDENT"])
    assert keys == ["SECTION", "IDENT"]
    assert values == ["VALUE"]


def test_guess_entry_style_columns():
    columns = ["SECTIONNAME", "ENTRYNAME", "ENTRYVALUE"]
    keys, values = guess_key_and_value_columns(columns)
    assert keys == ["SECTIONNAME", "ENTRYNAME"]
    assert values == ["ENTRYVALUE"]


def test_guess_ignores_surrogate_id():
    columns = [
        ColumnInfo(name="ID", type="int", primary_key=True),
        ColumnInfo(name="SECTION", type="varchar"),
        ColumnInfo(name="KEY", type="varchar"),
        ColumnInfo(name="VALUE", type="varchar"),
    ]
    keys, values = guess_key_and_value_columns(columns, ["ID"])
    assert "ID" not in keys
    assert keys == ["SECTION", "KEY"]
    assert values == ["VALUE"]


def test_compare_detects_changed_and_only_sides():
    left = [
        {"SECTION": "Mail", "IDENT": "Port", "VALUE": "25"},
        {"SECTION": "Mail", "IDENT": "Host", "VALUE": "mail.local"},
        {"SECTION": "Legacy", "IDENT": "On", "VALUE": "1"},
    ]
    right = [
        {"SECTION": "Mail", "IDENT": "Port", "VALUE": "587"},
        {"SECTION": "Mail", "IDENT": "Host", "VALUE": "mail.local"},
        {"SECTION": "Features", "IDENT": "Beta", "VALUE": "1"},
    ]
    rows, summary, warnings = compare_tables(left, right, ["SECTION", "IDENT"], ["VALUE"])
    assert not warnings
    assert summary.identical == 1
    assert summary.changed == 1
    assert summary.left_only == 1
    assert summary.right_only == 1
    by_key = { (row.key["SECTION"], row.key["IDENT"]): row.status for row in rows }
    assert by_key[("Mail", "Port")] == "changed"
    assert by_key[("Mail", "Host")] == "identical"
    assert by_key[("Legacy", "On")] == "left_only"
    assert by_key[("Features", "Beta")] == "right_only"


def test_compare_is_case_insensitive_on_keys_and_trims_values():
    left = [{"SECTION": "UI", "IDENT": "Theme", "VALUE": " modern "}]
    right = [{"SECTION": "ui", "IDENT": "THEME", "VALUE": "modern"}]
    rows, summary, _ = compare_tables(left, right, ["SECTION", "IDENT"], ["VALUE"])
    assert summary.identical == 1
    assert rows[0].status == "identical"
    assert rows[0].key["SECTION"] == "UI"


def test_include_identical_false_drops_matches():
    left = [{"SECTION": "A", "IDENT": "K", "VALUE": "1"}, {"SECTION": "B", "IDENT": "K", "VALUE": "2"}]
    right = [{"SECTION": "A", "IDENT": "K", "VALUE": "1"}, {"SECTION": "B", "IDENT": "K", "VALUE": "9"}]
    rows, summary, _ = compare_tables(left, right, ["SECTION", "IDENT"], ["VALUE"], include_identical=False)
    assert summary.identical == 1
    assert summary.changed == 1
    assert [row.status for row in rows] == ["changed"]


def test_duplicate_keys_warn_and_keep_first():
    left = [
        {"SECTION": "A", "IDENT": "K", "VALUE": "first"},
        {"SECTION": "A", "IDENT": "K", "VALUE": "second"},
    ]
    right = [{"SECTION": "A", "IDENT": "K", "VALUE": "first"}]
    rows, summary, warnings = compare_tables(left, right, ["SECTION", "IDENT"], ["VALUE"])
    assert summary.duplicate_keys_left == 1
    assert summary.identical == 1
    assert rows[0].left["VALUE"] == "first"
    assert any("duplicate" in warning.lower() for warning in warnings)
