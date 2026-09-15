from app.compare import compare_tables, guess_key_and_value_columns
from app.models import ColumnInfo
from app.query import KEY_COLUMNS, SETTINGS_SELECT, VALUE_COLUMNS, settings_select_sql


def test_canonical_query_matches_requested_select_list():
    assert SETTINGS_SELECT == (
        "SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT "
        "FROM TBLINISETTINGS"
    )
    sql = settings_select_sql("mssql", "dbo")
    assert sql == (
        "SELECT SECTION, NAME, INIVALUE, DESCRIPTION, EXPOSED, DATATYPE, DATAFORMAT "
        "FROM dbo.TBLINISETTINGS"
    )


def test_guess_tblinisettings_columns():
    columns = [
        ColumnInfo(name="SECTION", type="varchar", primary_key=True),
        ColumnInfo(name="NAME", type="varchar", primary_key=True),
        ColumnInfo(name="INIVALUE", type="varchar"),
        ColumnInfo(name="DESCRIPTION", type="varchar"),
        ColumnInfo(name="EXPOSED", type="varchar"),
        ColumnInfo(name="DATATYPE", type="varchar"),
        ColumnInfo(name="DATAFORMAT", type="varchar"),
    ]
    keys, values = guess_key_and_value_columns(columns, ["SECTION", "NAME"])
    assert keys == ["SECTION", "NAME"]
    assert "INIVALUE" in values


def test_compare_detects_changed_and_only_sides():
    left = [
        {"SECTION": "Mail", "NAME": "Port", "INIVALUE": "25", "DESCRIPTION": "SMTP port"},
        {"SECTION": "Mail", "NAME": "Host", "INIVALUE": "mail.local", "DESCRIPTION": "SMTP host"},
        {"SECTION": "Legacy", "NAME": "On", "INIVALUE": "1", "DESCRIPTION": "Legacy flag"},
    ]
    right = [
        {"SECTION": "Mail", "NAME": "Port", "INIVALUE": "587", "DESCRIPTION": "SMTP port"},
        {"SECTION": "Mail", "NAME": "Host", "INIVALUE": "mail.local", "DESCRIPTION": "SMTP host"},
        {"SECTION": "Features", "NAME": "Beta", "INIVALUE": "1", "DESCRIPTION": "Beta flag"},
    ]
    rows, summary, warnings = compare_tables(
        left, right, list(KEY_COLUMNS), ["INIVALUE", "DESCRIPTION"]
    )
    assert not warnings
    assert summary.identical == 1
    assert summary.changed == 1
    assert summary.left_only == 1
    assert summary.right_only == 1
    by_key = {(row.key["SECTION"], row.key["NAME"]): row.status for row in rows}
    assert by_key[("Mail", "Port")] == "changed"
    assert by_key[("Mail", "Host")] == "identical"
    assert by_key[("Legacy", "On")] == "left_only"
    assert by_key[("Features", "Beta")] == "right_only"


def test_compare_is_case_insensitive_on_keys_and_trims_values():
    left = [{"SECTION": "UI", "NAME": "Theme", "INIVALUE": " modern "}]
    right = [{"SECTION": "ui", "NAME": "THEME", "INIVALUE": "modern"}]
    rows, summary, _ = compare_tables(left, right, list(KEY_COLUMNS), list(VALUE_COLUMNS[:1]))
    assert summary.identical == 1
    assert rows[0].status == "identical"
    assert rows[0].key["SECTION"] == "UI"


def test_include_identical_false_drops_matches():
    left = [
        {"SECTION": "A", "NAME": "K", "INIVALUE": "1"},
        {"SECTION": "B", "NAME": "K", "INIVALUE": "2"},
    ]
    right = [
        {"SECTION": "A", "NAME": "K", "INIVALUE": "1"},
        {"SECTION": "B", "NAME": "K", "INIVALUE": "9"},
    ]
    rows, summary, _ = compare_tables(
        left, right, list(KEY_COLUMNS), ["INIVALUE"], include_identical=False
    )
    assert summary.identical == 1
    assert summary.changed == 1
    assert [row.status for row in rows] == ["changed"]


def test_duplicate_keys_warn_and_keep_first():
    left = [
        {"SECTION": "A", "NAME": "K", "INIVALUE": "first"},
        {"SECTION": "A", "NAME": "K", "INIVALUE": "second"},
    ]
    right = [{"SECTION": "A", "NAME": "K", "INIVALUE": "first"}]
    rows, summary, warnings = compare_tables(left, right, list(KEY_COLUMNS), ["INIVALUE"])
    assert summary.duplicate_keys_left == 1
    assert summary.identical == 1
    assert rows[0].left["INIVALUE"] == "first"
    assert any("duplicate" in warning.lower() for warning in warnings)
