from fastapi.testclient import TestClient

from mirrorlens_dashboard.bus import bus
from mirrorlens_dashboard.server import build_app


def test_demo_reset_clears_replayed_dashboard_state():
    client = TestClient(build_app())
    client.post("/api/demo/reset")

    import anyio

    anyio.run(bus.publish, "status", {"event": "completed"})
    anyio.run(bus.publish, "analysis", {"type": "timeline", "data": [{"step": 1}]})

    before = client.get("/api/snapshot").json()
    assert before["data"]["status"]
    assert before["data"]["analysis"]

    response = client.post("/api/demo/reset")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    after = client.get("/api/snapshot").json()
    assert all(events == [] for events in after["data"].values())
