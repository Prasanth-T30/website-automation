"""Full-stack proof: submit -> claim -> approve/reject, over real HTTP against
the real Firestore + Storage emulator — same discipline as test_auth_e2e.py.
"""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_firestore
from app.core.security import hash_password
from app.models.user import UserRole
from app.repositories.users import UserRepository
from tests.conftest import requires_emulator

pytestmark = requires_emulator


@pytest.fixture
def client():
    from app.main import app

    # Same rationale as test_auth_e2e.py: TestClient always reports the same
    # loopback address, so the limiter must be reset between tests or later
    # ones in the run trip the public form's 5/hour cap.
    app.state.limiter.reset()
    return TestClient(app)


@pytest.fixture
def user_repo():
    return UserRepository(get_firestore())


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _login_as(client: TestClient, user_repo: UserRepository, *, role: UserRole) -> str:
    email = f"{_unique('e2e-app')}@dvein.in"
    user_repo.create(
        email=email, full_name="E2E Applications", role=role,
        password_hash=hash_password("a-real-password-1"), phone=None,
        must_change_password=False,
    )
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "a-real-password-1"})
    assert res.status_code == 200
    return client.cookies["dvein_csrf"]


def _submit_application(client: TestClient, *, transaction_id: str, category: str = "Internship"):
    form = {
        "title": "Ms.",
        "name": "Jane Applicant",
        "email": f"{_unique('applicant')}@example.com",
        "phone": "9876543210",
        "college": "Test Engineering College",
        "place": "Chennai",
        "department": "",
        "year": "3rd Year",
        "applicant_type": "student",
        "category": category,
        "domain": "Full Stack Python",
        "duration": "30 Days",
        "start_date": "2026-09-01",
        "end_date": "2026-10-01",
        "amount": "6000",
        "transaction_id": transaction_id,
        "hr_name": "Aruna Devi", "declaration": "true",
    }
    files = {"payment_screenshot": ("proof.png", io.BytesIO(b"\x89PNG\r\n fake"), "image/png")}
    return client.post("/api/v1/public/applications", data=form, files=files)


def test_public_submission_creates_a_pending_application(client: TestClient):
    res = _submit_application(client, transaction_id=_unique("TXN"))
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "pending"
    assert body["registration_id"].startswith("REG")
    assert body["owner_id"] is None


def test_submission_rejects_unchecked_declaration(client: TestClient):
    form = {
        "name": "No Declaration", "email": "nodecl@example.com", "phone": "9876543210",
        "college": "College", "place": "Chennai", "applicant_type": "student",
        "category": "Internship", "domain": "Full Stack Python", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01", "amount": "6000",
        "transaction_id": _unique("TXN"), "hr_name": "Aruna Devi", "declaration": "false",
    }
    files = {"payment_screenshot": ("proof.png", io.BytesIO(b"fake"), "image/png")}
    res = client.post("/api/v1/public/applications", data=form, files=files)
    assert res.status_code == 422


def test_submission_rejects_bad_file_type(client: TestClient):
    form = {
        "name": "Bad File", "email": "badfile@example.com", "phone": "9876543210",
        "college": "College", "place": "Chennai", "applicant_type": "student",
        "category": "Internship", "domain": "Full Stack Python", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01", "amount": "6000",
        "transaction_id": _unique("TXN"), "hr_name": "Aruna Devi", "declaration": "true",
    }
    files = {"payment_screenshot": ("proof.pdf", io.BytesIO(b"%PDF fake"), "application/pdf")}
    res = client.post("/api/v1/public/applications", data=form, files=files)
    assert res.status_code == 415


def test_duplicate_transaction_id_is_rejected_over_http(client: TestClient):
    txn = _unique("TXN")
    first = _submit_application(client, transaction_id=txn)
    assert first.status_code == 201
    second = _submit_application(client, transaction_id=txn)
    assert second.status_code == 409


def test_choices_endpoint_returns_the_real_lists(client: TestClient):
    res = client.get("/api/v1/public/choices")
    assert res.status_code == 200
    body = res.json()
    assert "Full Stack Python" in body["domains"]
    assert body["categories"] == ["Internship", "Course", "Project"]
    assert "30 Days" in body["durations"]


def test_full_claim_and_approve_flow_creates_a_student(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"), category="Project")
    app_id = submitted.json()["id"]

    csrf = _login_as(client, user_repo, role=UserRole.hr)

    claim_res = client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    assert claim_res.status_code == 200
    assert claim_res.json()["status"] == "claimed"

    approve_res = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""},
        headers={"X-CSRF-Token": csrf},
    )
    assert approve_res.status_code == 200
    approved = approve_res.json()
    assert approved["status"] == "approved"
    assert approved["converted_student_id"]
    # Project category: EMAIL_ENABLED_CATEGORIES excludes it, so no PDF/email
    # attempt happens — nothing to assert about email here, only that the
    # approval itself succeeded without one.


def test_reject_flow_records_the_reason(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"))
    app_id = submitted.json()["id"]
    csrf = _login_as(client, user_repo, role=UserRole.hr)

    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    res = client.post(
        f"/api/v1/applications/{app_id}/reject",
        json={"reason": "Payment could not be verified against the bank statement."},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"


def test_second_hr_cannot_claim_an_already_claimed_application(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"))
    app_id = submitted.json()["id"]

    csrf1 = _login_as(client, user_repo, role=UserRole.hr)
    claimed = client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf1})
    assert claimed.status_code == 200

    csrf2 = _login_as(client, user_repo, role=UserRole.hr)
    second_attempt = client.post(
        f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf2}
    )
    assert second_attempt.status_code == 409


def test_non_owner_hr_cannot_approve_someone_elses_claim(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"))
    app_id = submitted.json()["id"]

    csrf1 = _login_as(client, user_repo, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf1})

    csrf2 = _login_as(client, user_repo, role=UserRole.hr)
    res = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""},
        headers={"X-CSRF-Token": csrf2},
    )
    assert res.status_code == 403


def test_admin_can_approve_any_claimed_application(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"), category="Project")
    app_id = submitted.json()["id"]

    hr_csrf = _login_as(client, user_repo, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": hr_csrf})

    admin_csrf = _login_as(client, user_repo, role=UserRole.admin)
    res = client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""},
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert res.status_code == 200


def test_offer_letter_downloads_a_real_pdf_after_approval(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"), category="Internship")
    app_id = submitted.json()["id"]
    csrf = _login_as(client, user_repo, role=UserRole.hr)

    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})
    client.post(
        f"/api/v1/applications/{app_id}/approve",
        json={"subject": "", "body": ""},
        headers={"X-CSRF-Token": csrf},
    )

    res = client.get(f"/api/v1/applications/{app_id}/offer-letter")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    assert len(res.content) > 1000


def test_offer_letter_unavailable_before_approval(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"))
    app_id = submitted.json()["id"]
    csrf = _login_as(client, user_repo, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})

    res = client.get(f"/api/v1/applications/{app_id}/offer-letter")
    assert res.status_code == 400


def test_list_applications_mine_filter(client: TestClient, user_repo):
    submitted = _submit_application(client, transaction_id=_unique("TXN"))
    app_id = submitted.json()["id"]

    csrf = _login_as(client, user_repo, role=UserRole.hr)
    client.post(f"/api/v1/applications/{app_id}/claim", headers={"X-CSRF-Token": csrf})

    mine = client.get("/api/v1/applications", params={"mine": "true"})
    assert mine.status_code == 200
    ids = {a["id"] for a in mine.json()}
    assert app_id in ids


def _live_site_payload(**overrides) -> dict:
    """Exactly what the retired Vercel form posted.

    Note `salutation` rather than `title`, the `mode` and `project_topic`
    fields, and a domain from the older list the deployed site still ships.
    """
    form = {
        "salutation": "Ms.", "name": "Anitha Selvam",
        "email": f"{_unique('live')}@example.com", "phone": "9876500123",
        "college": "Kumaraguru College of Technology", "place": "Coimbatore",
        "department": "CSE", "year": "3rd Year", "applicant_type": "student",
        "category": "Internship", "domain": "Java", "duration": "30 Days",
        "mode": "Online",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "18000", "transaction_id": _unique("TXN"), "declaration": "true",
        "hr_name": "Aruna Devi",
    }
    form.update(overrides)
    return form


def _shot():
    return {"payment_screenshot": ("proof.png", io.BytesIO(b"fake"), "image/png")}


def test_deployed_site_payload_is_accepted(client: TestClient):
    """The live form sends `salutation`, not `title`. Rejecting it would drop
    a paid registration on the floor."""
    res = client.post("/api/v1/public/applications", data=_live_site_payload(), files=_shot())
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["title"] == "Ms."      # salutation mapped onto title
    assert body["mode"] == "Online"
    assert body["status"] == "pending"


def test_retired_domain_names_are_translated_not_rejected(client: TestClient):
    """The deployed site still offers the older domain list."""
    res = client.post(
        "/api/v1/public/applications",
        data=_live_site_payload(domain="Java"), files=_shot(),
    )
    assert res.status_code == 201, res.text
    assert res.json()["domain"] == "Full Stack Java"


def test_a_genuinely_unknown_domain_is_still_refused(client: TestClient):
    res = client.post(
        "/api/v1/public/applications",
        data=_live_site_payload(domain="Underwater Basket Weaving"), files=_shot(),
    )
    assert res.status_code == 422


def test_project_registration_carries_its_topic(client: TestClient):
    """A Project asks for a topic and no mode; everything else the reverse."""
    res = client.post(
        "/api/v1/public/applications",
        data=_live_site_payload(category="Project", project_topic="Smart attendance tracker"),
        files=_shot(),
    )
    assert res.status_code == 201, res.text
    assert res.json()["project_topic"] == "Smart attendance tracker"


def test_legacy_register_path_reaches_the_same_handler(client: TestClient):
    """The deployed site posts to /register. It must land in the same claim
    queue as /public/applications, not a parallel one."""
    res = client.post("/api/v1/register", data=_live_site_payload(), files=_shot())
    assert res.status_code == 201, res.text
    created = res.json()

    listed = client.get("/api/v1/public/choices")  # sanity: app still healthy
    assert listed.status_code == 200
    assert created["registration_id"].startswith("REG")
    assert created["status"] == "pending"
    assert created["owner_id"] is None


def test_mode_must_be_a_real_choice(client: TestClient):
    res = client.post(
        "/api/v1/public/applications",
        data=_live_site_payload(mode="Telepathic"), files=_shot(),
    )
    assert res.status_code == 422


# ── Native place and year of passing out ─────────────────────────────────
#
# Added to the public form after it was already live, which is the whole
# difficulty: the deployed site does not send either field, so the API has to
# accept both presence and absence. These pin down both halves.


def _payload_with(**extra) -> dict:
    form = {
        "title": "Mr.", "name": "Native Fields",
        "email": f"{_unique('native')}@example.com", "phone": "9876500999",
        "college": "PSG College of Technology", "place": "Coimbatore",
        "department": "ECE", "year": "Final Year", "applicant_type": "student",
        "category": "Internship", "domain": "Full Stack Python", "duration": "30 Days",
        "start_date": "2026-09-01", "end_date": "2026-10-01",
        "amount": "12000", "transaction_id": _unique("TXN"), "declaration": "true",
        "hr_name": "Aruna Devi",
    }
    form.update(extra)
    return form


def _shot_png() -> dict:
    return {"payment_screenshot": ("proof.png", io.BytesIO(b"\x89PNG\r\n fake"), "image/png")}


def test_native_place_and_passing_year_survive_the_round_trip(client: TestClient):
    """Submitted on the public form, readable back off the record.

    A field that validates but is dropped before Firestore looks identical to
    a working one at the point of submission — the applicant sees 201 either
    way. Reading it back is the only thing that proves it was stored.
    """
    res = client.post(
        "/api/v1/public/applications",
        data=_payload_with(native_place="Salem", passed_out_year="2027"),
        files=_shot_png(),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["native_place"] == "Salem"
    assert body["passed_out_year"] == "2027"

    stored = get_firestore().collection("applications").document(body["id"]).get().to_dict()
    assert stored["native_place"] == "Salem"
    assert stored["passed_out_year"] == "2027"


def test_the_older_deployed_form_still_submits_without_them(client: TestClient):
    """The live site predates both fields. It must not start failing."""
    res = client.post("/api/v1/public/applications", data=_payload_with(), files=_shot_png())
    assert res.status_code == 201, res.text
    assert res.json()["native_place"] is None
    assert res.json()["passed_out_year"] is None


def test_a_nonsense_passing_year_is_refused(client: TestClient):
    for bad in ("27", "twenty twenty six", "1985", "2099"):
        res = client.post(
            "/api/v1/public/applications",
            data=_payload_with(passed_out_year=bad),
            files=_shot_png(),
        )
        assert res.status_code == 422, f"{bad!r} was accepted: {res.text}"


def test_a_professional_who_graduated_years_ago_can_still_pick_their_year(client: TestClient):
    """The offered range has to cover the upskilling professionals, not just
    students. Ten years back is an ordinary case for them."""
    from datetime import UTC, datetime

    long_ago = str(datetime.now(UTC).year - 10)
    offered = client.get("/api/v1/public/choices").json()["passed_out_years"]
    assert long_ago in offered

    res = client.post(
        "/api/v1/public/applications",
        data=_payload_with(applicant_type="professional", category="Course",
                           passed_out_year=long_ago),
        files=_shot_png(),
    )
    assert res.status_code == 201, res.text
    assert res.json()["passed_out_year"] == long_ago


def test_the_offered_years_track_the_calendar(client: TestClient):
    """Hardcoding the list is the failure mode worth guarding: it works until
    the new year, then quietly stops offering the incoming batch a valid
    option — with no error anywhere to notice."""
    from datetime import UTC, datetime

    offered = client.get("/api/v1/public/choices").json()["passed_out_years"]
    this_year = datetime.now(UTC).year
    assert str(this_year) in offered
    assert str(this_year + 1) in offered, "next year's graduates have no option"
    assert offered == sorted(offered, reverse=True), "years should read newest first"
