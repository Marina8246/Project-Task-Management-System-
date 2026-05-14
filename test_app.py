import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app) 


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_token(username: str, password: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, f"Login failed for {username}: {response.text}"
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────────────────────────────────────────
#  Auth Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_register_and_login():
    # Register
    res = client.post("/auth/register", json={
        "username": "testuser_001",
        "password": "pass1234",
        "role": "employee"
    })
    assert res.status_code in [200, 201, 400]  # 400 if already exists

    # Login
    res = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password():
    res = client.post("/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert res.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
#  Task Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_create_task_as_admin():
    token = get_token("admin", "admin123")

    # First create a project
    proj_res = client.post("/projects/", json={
        "name": "Test Project",
        "description": "Project for testing"
    }, headers=auth_headers(token))
    assert proj_res.status_code in [200, 201]
    project_id = proj_res.json()["id"]

    # Create task
    res = client.post("/tasks/", json={
        "title": "Test Task",
        "description": "A task for testing",
        "priority": "high",
        "project_id": project_id
    }, headers=auth_headers(token))
    assert res.status_code == 201
    assert res.json()["title"] == "Test Task"
    assert res.json()["status"] == "todo"


def test_get_all_tasks_as_admin():
    token = get_token("admin", "admin123")
    res = client.get("/tasks/", headers=auth_headers(token))
    assert res.status_code == 200
    assert "tasks" in res.json()


def test_get_task_by_id_not_found():
    token = get_token("admin", "admin123")
    res = client.get("/tasks/99999", headers=auth_headers(token))
    assert res.status_code == 404


def test_update_task_as_admin():
    token = get_token("admin", "admin123")

    # Get first task
    tasks_res = client.get("/tasks/", headers=auth_headers(token))
    tasks = tasks_res.json()["tasks"]
    if not tasks:
        pytest.skip("No tasks available to update")

    task_id = tasks[0]["id"]
    res = client.put(f"/tasks/{task_id}", json={
        "status": "in_progress"
    }, headers=auth_headers(token))
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


def test_delete_task_as_admin():
    token = get_token("admin", "admin123")

    # Get first task
    tasks_res = client.get("/tasks/", headers=auth_headers(token))
    tasks = tasks_res.json()["tasks"]
    if not tasks:
        pytest.skip("No tasks available to delete")

    task_id = tasks[0]["id"]
    res = client.delete(f"/tasks/{task_id}", headers=auth_headers(token))
    assert res.status_code == 204


def test_employee_cannot_delete_task():
    # Register employee
    client.post("/auth/register", json={
        "username": "emp_test_001",
        "password": "pass1234",
        "role": "employee"
    })
    token = get_token("emp_test_001", "pass1234")

    res = client.delete("/tasks/1", headers=auth_headers(token))
    assert res.status_code == 403


# ──────────────────────────────────────────────────────────────────────────────
#  Monitoring Tests
# ──────────────────────────────────────────────────────────────────────────────

def test_health_check():
    res = client.get("/monitoring/health")
    assert res.status_code == 200
    assert res.json()["server"] == "running"
    assert "redis" in res.json()


def test_cache_stats_admin_only():
    token = get_token("admin", "admin123")
    res = client.get("/monitoring/stats", headers=auth_headers(token))
    assert res.status_code == 200
    assert "cached_keys" in res.json()


def test_cache_stats_unauthorized():
    res = client.get("/monitoring/stats")
    assert res.status_code == 401
