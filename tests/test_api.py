from fastapi.testclient import TestClient

from app.demo import LEFT_SETTINGS, RIGHT_SETTINGS
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_compare_matches_sample_drift():
    response = client.get("/api/demo")
    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]
    assert payload["left"]["table"].upper() == "TBLINISETTINGS"
    assert payload["key_columns"] == ["SECTION", "IDENT"]
    assert payload["value_columns"] == ["VALUE"]
    assert summary["total"] == len({(r["SECTION"], r["IDENT"]) for r in LEFT_SETTINGS + RIGHT_SETTINGS})
    assert summary["changed"] >= 6
    assert summary["left_only"] == 2  # Legacy keys
    assert summary["right_only"] == 2  # PlacesAPI + BetaGrid
    statuses = { (row["key"]["SECTION"], row["key"]["IDENT"]): row["status"] for row in payload["rows"] }
    assert statuses[("Database", "CommandTimeout")] == "changed"
    assert statuses[("Legacy", "UseOldReports")] == "left_only"
    assert statuses[("Integrations", "PlacesAPI")] == "right_only"
    assert statuses[("Database", "MaxPoolSize")] == "identical"


def test_demo_can_hide_identical_rows():
    response = client.get("/api/demo", params={"include_identical": False})
    payload = response.json()
    assert payload["summary"]["identical"] >= 1
    assert all(row["status"] != "identical" for row in payload["rows"])


def test_inspect_demo_sqlite():
    from app.demo import ensure_sample_databases

    path, _ = ensure_sample_databases()
    response = client.post(
        "/api/inspect",
        json={
            "connection": {
                "label": "A",
                "driver": "sqlite",
                "database": str(path),
                "schema_name": None,
                "table": "TBLINISETTINGS",
            }
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["suggested_key_columns"] == ["SECTION", "IDENT"]
    assert body["snapshot"]["row_count"] == len(LEFT_SETTINGS)
    assert len(body["preview"]) == 8
    assert body["preview"][0]["SECTION"] == "Database"


def test_inspect_missing_table():
    from app.demo import ensure_sample_databases

    path, _ = ensure_sample_databases()
    response = client.post(
        "/api/inspect",
        json={
            "connection": {
                "label": "A",
                "driver": "sqlite",
                "database": str(path),
                "schema_name": None,
                "table": "NOPE",
            }
        },
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()
