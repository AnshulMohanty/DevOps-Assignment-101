def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}

def test_ready_checks_the_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "TaskBoard API"

def test_create_task(client):
    response = client.post("/api/tasks", json={"title": "Deploy application", "priority": "HIGH", "assignee": "Student"})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Deploy application"
    assert body["status"] == "TODO"
    assert body["id"] > 0

def test_create_task_rejects_bad_input(client):
    assert client.post("/api/tasks", json={"title": ""}).status_code == 422
    assert client.post("/api/tasks", json={"title": "x", "priority": "URGENT"}).status_code == 422

def test_list_tasks_newest_first(client, task):
    tasks = client.get("/api/tasks").json()
    assert tasks[0]["id"] == task["id"]
    assert [t["id"] for t in tasks] == sorted((t["id"] for t in tasks), reverse=True)

def test_get_task(client, task):
    response = client.get(f"/api/tasks/{task['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Write Helm chart"

def test_get_missing_task_returns_404(client):
    response = client.get("/api/tasks/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"

def test_update_task_status(client, task):
    response = client.put(f"/api/tasks/{task['id']}", json={"status": "IN_PROGRESS"})
    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"
    assert response.json()["title"] == "Write Helm chart"  # untouched fields stay

def test_delete_task(client, task):
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 204
    assert client.get(f"/api/tasks/{task['id']}").status_code == 404

def test_stats_count_by_status(client):
    before = client.get("/api/tasks/stats").json()
    created = client.post("/api/tasks", json={"title": "Finish report", "status": "DONE"}).json()
    after = client.get("/api/tasks/stats").json()
    assert after["total"] == before["total"] + 1
    assert after["done"] == before["done"] + 1
    assert after["total"] == after["todo"] + after["inProgress"] + after["done"]
    client.delete(f"/api/tasks/{created['id']}")

def test_metrics_endpoint_is_prometheus_format(client):
    client.get("/api/tasks")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
