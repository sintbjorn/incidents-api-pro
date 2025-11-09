def test_crud_flow(client):
    # create
    r = client.post("/api/v1/incidents", json={"description": "Scooter offline", "source": "monitoring"})
    assert r.status_code == 201, r.text
    inc = r.json()
    assert inc["status"] == "NEW"
    iid = inc["id"]

    # list filter
    r = client.get("/api/v1/incidents", params={"status": "NEW"})
    assert r.status_code == 200
    assert any(i["id"] == iid for i in r.json())

    # update status: NEW -> IN_PROGRESS
    r = client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "IN_PROGRESS"})
    assert r.status_code == 200
    assert r.json()["status"] == "IN_PROGRESS"

    # invalid backward transition
    r = client.patch(f"/api/v1/incidents/{iid}/status", json={"status": "NEW"})
    assert r.status_code == 409

    # not found
    r = client.patch("/api/v1/incidents/999999/status", json={"status": "IN_PROGRESS"})
    assert r.status_code == 404
