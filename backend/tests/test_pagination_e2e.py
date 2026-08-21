"""Cursor pagination: opt-in, complete, and non-overlapping.

The dangerous failure here is not slowness, it is a page being mistaken for
the whole set — the console derives its dashboard and Finance totals from
these lists, so a silently truncated response would make every figure wrong
rather than merely late. These tests pin both halves: paging works when asked
for, and the unpaged call still returns everything.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.pagination import MAX_PAGE_SIZE, clamp_page_size
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client():
    from app.main import app

    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def user_repo():
    from app.core.firebase import get_firestore

    return UserRepository(get_firestore())


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-page')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Pagination", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _make_students(client: TestClient, csrf: str, n: int) -> set[str]:
    ids = set()
    for i in range(n):
        res = client.post(
            "/api/v1/students",
            json={
                "name": f"Page Student {i}", "email": f"{_unique('pg')}@example.com",
                "phone": "9876543210", "college": "PSG College of Technology",
                "place": "Coimbatore", "category": "Internship", "domain": "DevOps",
                "duration": "30 Days", "total_fees": 1000, "fees_paid": 0,
            },
            headers={"X-CSRF-Token": csrf},
        )
        assert res.status_code == 201, res.text
        ids.add(res.json()["id"])
    return ids


def _walk(client: TestClient, path: str, size: int, **params) -> list[dict]:
    """Follow X-Next-Cursor to the end, as a real caller must."""
    seen, cursor, guard = [], None, 0
    while True:
        guard += 1
        assert guard < 100, "pagination did not terminate"
        q = {"limit": size, **params}
        if cursor:
            q["cursor"] = cursor
        res = client.get(path, params=q)
        assert res.status_code == 200, res.text
        seen.extend(res.json())
        cursor = res.headers.get("X-Next-Cursor")
        if not cursor:
            return seen


def test_omitting_limit_still_returns_the_whole_list(client: TestClient, user_repo):
    """Existing callers must not silently start getting one page."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    made = _make_students(client, csrf, 7)

    everything = {s["id"] for s in client.get("/api/v1/students").json()}
    assert made <= everything
    assert "X-Next-Cursor" not in client.get("/api/v1/students").headers


def test_a_page_is_capped_at_the_requested_size(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    _make_students(client, csrf, 7)

    res = client.get("/api/v1/students", params={"limit": 3})
    assert res.status_code == 200
    assert len(res.json()) <= 3
    assert res.headers.get("X-Next-Cursor"), "more remained but no cursor was offered"


def test_walking_the_cursor_returns_every_student_exactly_once(
    client: TestClient, user_repo
):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    made = _make_students(client, csrf, 7)

    walked = _walk(client, "/api/v1/students", 2)
    ids = [s["id"] for s in walked]
    assert made <= set(ids), "paging lost students"
    assert len(ids) == len(set(ids)), "paging returned duplicates"
    assert set(ids) == {s["id"] for s in client.get("/api/v1/students").json()}


def test_the_last_page_offers_no_cursor(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    _make_students(client, csrf, 3)

    cursor, guard = None, 0
    while True:
        guard += 1
        assert guard < 100
        q = {"limit": 50}
        if cursor:
            q["cursor"] = cursor
        res = client.get("/api/v1/students", params=q)
        cursor = res.headers.get("X-Next-Cursor")
        if not cursor:
            break
    assert cursor is None


def test_pagination_respects_per_hr_scoping(client: TestClient, user_repo):
    """A page must not be a way around the isolation rules."""
    csrf_a = _login_as(client, user_repo, role=UserRole.hr)
    theirs = _make_students(client, csrf_a, 3)

    _login_as(client, user_repo, role=UserRole.hr)
    walked = {s["id"] for s in _walk(client, "/api/v1/students", 2)}
    assert not (theirs & walked), "paging leaked another HR's students"


def test_the_claim_pool_pages_completely(client: TestClient, user_repo):
    _login_as(client, user_repo, role=UserRole.hr)
    unpaged = {a["id"] for a in client.get("/api/v1/applications").json()}
    walked = {a["id"] for a in _walk(client, "/api/v1/applications", 4)}
    assert walked == unpaged


def test_the_ledger_pages_completely(client: TestClient, user_repo):
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    student = _make_students(client, csrf, 1).pop()
    for _ in range(3):
        client.post(
            "/api/v1/payments/record",
            json={"student_id": student, "amount": 100},
            headers={"X-CSRF-Token": csrf},
        )

    unpaged = {p["id"] for p in client.get("/api/v1/payments").json()}
    walked = {p["id"] for p in _walk(client, "/api/v1/payments", 2)}
    assert walked == unpaged


def test_a_page_size_beyond_the_ceiling_is_refused(client: TestClient, user_repo):
    """A caller must not be able to ask for the entire collection in one hit
    and call it a page."""
    _login_as(client, user_repo, role=UserRole.hr)
    assert client.get("/api/v1/students", params={"limit": 10_000}).status_code == 422


def test_the_repository_clamps_rather_than_trusting_its_caller():
    assert clamp_page_size(None) > 0
    assert clamp_page_size(0) == 1
    assert clamp_page_size(-5) == 1
    assert clamp_page_size(10_000) == MAX_PAGE_SIZE


def test_an_unknown_cursor_does_not_error(client: TestClient, user_repo):
    """A stale bookmark should return an empty tail, not a 500."""
    _login_as(client, user_repo, role=UserRole.hr)
    res = client.get("/api/v1/students", params={"limit": 5, "cursor": "no-such-doc-id"})
    assert res.status_code == 200


def test_a_short_page_does_not_mean_the_end(client: TestClient, user_repo):
    """Secondary filters run in Python after the Firestore query, so a page
    can arrive short while later pages still hold matches. A caller that stops
    at the first short page would silently miss records."""
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    made = _make_students(client, csrf, 6)

    # `no_batch` is applied after the read, which is exactly the case at risk.
    walked = {s["id"] for s in _walk(client, "/api/v1/students", 2, no_batch="true")}
    assert made <= walked
