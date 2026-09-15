from fastapi.testclient import TestClient

from app.demo import LEFT_SETTINGS, RIGHT_SETTINGS
from app.main import app
from app.query import SETTINGS_SELECT

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_servers_dropdown_catalog():
    response = client.get("/api/servers")
    assert response.status_code == 200
    payload = response.json()["servers"]
    names = [server["name"] for server in payload]
    assert "sql-butterfly.appian.trimblemaps.com" in names
    assert "sql01.staging.appiantesting.com" in names
    assert "law-sql02.staging.appiantesting.com" in names
    assert all("password" not in server for server in payload)
    butterfly = next(server for server in payload if server["name"].startswith("sql-butterfly"))
    staging = next(server for server in payload if "staging" in server["name"])
    assert butterfly["username"] == "AppianAppUser2025"
    assert staging["username"] == "AppianAppStageUser2025"


def test_config_exposes_server_names_and_query():
    response = client.get("/api/config")
    payload = response.json()
    assert payload["query"] == SETTINGS_SELECT
    assert payload["table"] == "TBLINISETTINGS"
    assert "username" not in payload or payload.get("username") in (None, "")
    names = {server["name"] for server in payload["servers"]}
    assert "sql-tadpole.appian.trimblemaps.com" in names
    assert "law-sql01.appian.trimblemaps.com" in names


def test_demo_compare_matches_sample_drift():
    response = client.get("/api/demo")
    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]
    assert payload["left"]["table"].upper() == "TBLINISETTINGS"
    assert payload["key_columns"] == ["SECTION", "NAME"]
    assert payload["value_columns"] == [
        "INIVALUE",
        "DESCRIPTION",
        "EXPOSED",
        "DATATYPE",
        "DATAFORMAT",
    ]
    assert "INIVALUE" in payload["query"]
    assert summary["total"] == len({(r["SECTION"], r["NAME"]) for r in LEFT_SETTINGS + RIGHT_SETTINGS})
    assert summary["changed"] >= 6
    assert summary["left_only"] == 2
    assert summary["right_only"] == 2
    statuses = {(row["key"]["SECTION"], row["key"]["NAME"]): row["status"] for row in payload["rows"]}
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
    assert body["suggested_key_columns"] == ["SECTION", "NAME"]
    assert body["suggested_value_columns"][0] == "INIVALUE"
    assert body["snapshot"]["row_count"] == len(LEFT_SETTINGS)
    assert len(body["preview"]) == 8
    assert set(body["preview"][0]) >= {"SECTION", "NAME", "INIVALUE", "DESCRIPTION"}


def test_inspect_missing_table():
    from sqlalchemy import create_engine

    path = "/tmp/empty-db-compare.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    engine.dispose()
    response = client.post(
        "/api/inspect",
        json={
            "connection": {
                "label": "A",
                "driver": "sqlite",
                "database": path,
                "schema_name": None,
                "table": "TBLINISETTINGS",
            }
        },
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


def test_compare_rejects_unknown_server_name():
    response = client.post(
        "/api/compare",
        json={
            "left_server": "NOT-A-SERVER",
            "right_server": "sql-tadpole.appian.trimblemaps.com",
            "database": "AppDB",
        },
    )
    assert response.status_code == 400
    assert "unknown server" in response.json()["detail"].lower()


def test_api_does_not_leak_passwords():
    for path in ("/api/config", "/api/servers"):
        body = client.get(path).text
        assert "password" not in body.lower() or "password_configured" in body
        assert "XcB+" not in body
        assert "yBUc" not in body
        assert "~7qgE" not in body
        assert "2}kqe" not in body
