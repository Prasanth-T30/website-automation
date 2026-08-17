import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pymongo.errors import ServerSelectionTimeoutError

from app.database import connection as mongo_conn_mod


class MongoConnectionTlsFallbackTests(unittest.TestCase):
    def test_connect_retries_with_invalid_cert_for_local_dev(self):
        mongo_conn_mod.mongo_connection.client = None
        mongo_conn_mod.mongo_connection.db = None

        settings = SimpleNamespace(
            MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority",
            MONGO_DB_NAME="internship_portal",
            ENV="development",
        )

        calls = []

        class DummyDatabase:
            def __init__(self):
                self.registrations = SimpleNamespace(create_index=AsyncMock())
                self.admins = SimpleNamespace(create_index=AsyncMock())

        class DummyClient:
            def __init__(self):
                self.admin = SimpleNamespace(command=AsyncMock(return_value={"ok": 1}))

            def __getitem__(self, name):
                if name == settings.MONGO_DB_NAME:
                    return DummyDatabase()
                raise KeyError(name)

            def close(self):
                pass

        def fake_client_factory(*args, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise ServerSelectionTimeoutError("SSL handshake failed: tlsv1 alert internal error")
            return DummyClient()

        with patch.object(mongo_conn_mod, "settings", settings), \
             patch.object(mongo_conn_mod, "create_indexes", AsyncMock()), \
             patch.object(mongo_conn_mod, "AsyncIOMotorClient", side_effect=fake_client_factory):
            import asyncio
            asyncio.run(mongo_conn_mod.connect_to_mongo())

        self.assertEqual(len(calls), 2)
        self.assertFalse(calls[0].get("tlsAllowInvalidCertificates", False))
        self.assertTrue(calls[1].get("tlsAllowInvalidCertificates", False))


if __name__ == "__main__":
    unittest.main()
