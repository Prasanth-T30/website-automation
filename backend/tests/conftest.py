"""Shared fixtures.

The repository/integration tests in this suite talk to a *real* Firestore /
Storage emulator (see ../../firebase.json) rather than mocking the Admin SDK
— the emulator is fast enough that the round trip costs nothing, and it
proves the actual client wiring works, not just that our code calls a mock
correctly.

Requires `firebase emulators:start --only firestore,storage` to be running.
Tests here are skipped automatically if it isn't reachable.
"""

from __future__ import annotations

import os
import socket
import uuid

import pytest

os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
os.environ.setdefault("STORAGE_EMULATOR_HOST", "http://127.0.0.1:9199")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long")

# Give the whole run its own Firestore project, so the end-to-end tests — which
# drive the real FastAPI app rather than a repository directly — write into a
# throwaway namespace instead of the one local development uses.
#
# Without this the app reads FIREBASE_PROJECT_ID from .env (`demo-dvein-hrm`)
# and every `pytest` leaves dozens of fabricated students, payments and users
# sitting in the database you then open the console against. An environment
# variable takes precedence over .env in pydantic-settings, and this must be
# set before `app.core.config` is first imported.
os.environ.setdefault("FIREBASE_PROJECT_ID", f"test-run-{uuid.uuid4().hex[:8]}")

# Never send real email from a test run. Not setdefault — an overwrite: the
# developer's own .env carries working SMTP credentials, so without this every
# `pytest` posts real messages through the institute's mailbox, burns its daily
# quota, and mails whatever addresses the fixtures happen to invent.
# `smtp_configured` keys off the host alone, so blanking it is the whole switch.
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_PASSWORD"] = ""


def _emulator_reachable(host: str) -> bool:
    ip, port = host.split(":")
    try:
        with socket.create_connection((ip, int(port)), timeout=1):
            return True
    except OSError:
        return False


EMULATOR_UP = _emulator_reachable(os.environ["FIRESTORE_EMULATOR_HOST"])

requires_emulator = pytest.mark.skipif(
    not EMULATOR_UP,
    reason="Firestore/Storage emulator not running — start it with "
    "`firebase emulators:start --only firestore,storage`",
)


@pytest.fixture
def firestore_client():
    from google.cloud.firestore import Client

    # A fresh project ID per test keeps the emulator's data from one test
    # leaking into another — each project is an isolated namespace.
    #
    # This depends on `emulators.singleProject` being false in firebase.json.
    # With it true the emulator collapses every project into one, so this
    # isolation silently does nothing: tests then read the dev data seeded
    # under `demo-dvein-hrm` and write their own rows into it.
    return Client(project=f"test-{uuid.uuid4().hex[:8]}")


@pytest.fixture
def storage_bucket():
    from google.auth.credentials import AnonymousCredentials
    from google.cloud.storage import Client as StorageClient

    # The Storage emulator auto-provisions one default bucket per "demo-"
    # project rather than supporting arbitrary bucket creation — matching
    # settings.firebase_storage_bucket's naming scheme for demo-dvein-hrm.
    # Tests isolate via unique blob names (uuid), not unique buckets.
    project = f"demo-{uuid.uuid4().hex[:8]}"
    # google-cloud-storage insists on a real google.auth Credentials instance
    # even though every call is routed to the emulator via STORAGE_EMULATOR_HOST.
    client = StorageClient(project=project, credentials=AnonymousCredentials())
    return client.bucket(f"{project}.appspot.com")
