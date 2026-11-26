from app import create_app

def test_health_endpoint():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"

def test_library_requires_auth():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    response = client.get("/api/me/library")
    assert response.status_code == 401
