from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from backend.app.auth.deps import get_current_user
from backend.app.main import create_app
from backend.app.routers import monitor as monitor_router
from backend.app.schemas.auth import AuthenticatedUser


class StubRagService:
    """Provide deterministic monitor API responses for router tests."""

    def __init__(self) -> None:
        self.recent_limit: int | None = None
        self.recent_page: int | None = None
        self.recent_errors_only: bool | None = None

    def monitor_summary(self) -> dict:
        """Return the legacy summary shape exposed by the service."""
        return {
            "trace_count": 2,
            "stage_summary": {
                "generation": {
                    "count": 2,
                    "success_count": 1,
                    "success_rate": 0.5,
                    "avg_elapsed_sec": 0.25,
                    "avg_throughput": 3.0,
                    "throughput_unit": "tokens/sec",
                }
            },
        }

    def monitor_recent(self, limit: int = 20, page: int = 1, errors_only: bool = False) -> dict:
        """Return the legacy recent shape and capture the requested limit."""
        self.recent_limit = limit
        self.recent_page = page
        self.recent_errors_only = errors_only
        return {
            "items": [{"trace_id": "trace-1", "stages": []}],
            "rows": [],
            "paging": {"limit": limit, "page": page, "errors_only": errors_only},
        }


@pytest.fixture
def stub_service(monkeypatch: pytest.MonkeyPatch) -> StubRagService:
    """Replace the shared RAG service with a deterministic test double."""
    service = StubRagService()
    monkeypatch.setattr(monitor_router, "get_rag_service", lambda: service)
    return service


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Create an isolated app client with dependency overrides reset after use."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _override_user(client: TestClient, roles: list[str]) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
        username="test-user",
        roles=roles,
    )


def test_monitor_summary_requires_admin_role(client: TestClient, stub_service: StubRagService) -> None:
    _override_user(client, ["user"])

    response = client.get("/api/monitor/summary")

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient role."}


def test_monitor_summary_preserves_legacy_contract(client: TestClient, stub_service: StubRagService) -> None:
    _override_user(client, ["admin"])

    response = client.get("/api/monitor/summary")

    assert response.status_code == 200
    assert response.json() == stub_service.monitor_summary()


def test_monitor_recent_preserves_legacy_contract_and_limit(
    client: TestClient,
    stub_service: StubRagService,
) -> None:
    _override_user(client, ["admin"])

    response = client.get("/api/monitor/recent?limit=50&page=2&errors_only=true")

    assert response.status_code == 200
    assert response.json() == {
        "items": [{"trace_id": "trace-1", "stages": []}],
        "rows": [],
        "paging": {"limit": 50, "page": 2, "errors_only": True},
    }
    assert stub_service.recent_limit == 50
    assert stub_service.recent_page == 2
    assert stub_service.recent_errors_only is True
