"""Firebase Admin SDK bootstrap: Firestore client + Storage bucket.

Two modes, chosen by whether an emulator host is configured:

* **Local dev** — ``firestore_emulator_host`` / ``firebase_storage_emulator_host``
  are set (see ``.env.example``, backed by ``firebase.json``). The Admin SDK
  is initialised with no credential at all; as long as the emulator env vars
  are present before the client is constructed, both the Firestore and
  Storage clients route to the emulator and never attempt real GCP auth.
* **Production** — ``firebase_service_account_path`` points at a real
  service-account JSON, and requests hit the live Firebase project.

The Admin SDK bypasses Firestore/Storage security rules entirely, which is
why ``firestore.rules`` / ``storage.rules`` deny all client access: every
read and write in this app goes through this module, never through a
browser-side Firebase SDK.
"""

from __future__ import annotations

import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore import Client as FirestoreClient
from google.cloud.storage import Bucket

from app.core.config import settings


class _EmulatorCredential(credentials.Base):
    """Satisfies firebase_admin's credential interface without touching ADC.

    Passing no credential at all to `initialize_app` still resolves to
    `credentials.ApplicationDefault()`, which eagerly calls `google.auth.default()`
    and fails outside GCP even when every actual request is routed to the
    emulator. This supplies an explicit anonymous credential instead, which the
    emulator accepts and which never attempts real authentication.
    """

    def get_credential(self):
        return AnonymousCredentials()


@lru_cache
def get_app() -> firebase_admin.App:
    if firebase_admin._apps:  # already initialised (e.g. by an earlier import)
        return firebase_admin.get_app()

    # Must be set *before* the Firestore/Storage clients are constructed —
    # both libraries read these at client-creation time, not per-request.
    if settings.firestore_emulator_host:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
    if settings.firebase_storage_emulator_host:
        # google-cloud-storage expects a full URL, not just host:port.
        os.environ["STORAGE_EMULATOR_HOST"] = (
            f"http://{settings.firebase_storage_emulator_host}"
        )

    options = {
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.firebase_storage_bucket,
    }

    if settings.firebase_service_account_path:
        cred = credentials.Certificate(str(settings.firebase_service_account_path))
        return firebase_admin.initialize_app(cred, options)

    if settings.firestore_emulator_host or settings.firebase_storage_emulator_host:
        return firebase_admin.initialize_app(_EmulatorCredential(), options)

    # Neither a service account nor an emulator host is configured — this is
    # a genuine misconfiguration, so fail loudly via real ADC resolution
    # rather than silently defaulting to an emulator credential in production.
    return firebase_admin.initialize_app(options=options)


@lru_cache
def get_firestore() -> FirestoreClient:
    get_app()
    return firestore.client()


@lru_cache
def get_bucket() -> Bucket:
    get_app()
    return storage.bucket()
