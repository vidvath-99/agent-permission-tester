import copy
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from api import create_app
from gateway import Gateway


class APIPermissionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        token_a = secrets.token_urlsafe(32)
        token_b = secrets.token_urlsafe(32)

        self.headers_a = {"Authorization": f"Bearer {token_a}"}
        self.headers_b = {"Authorization": f"Bearer {token_b}"}

        audit_file = Path(temp.name) / "audit.jsonl"

        def build_gateway(*, broken=False):
            return Gateway(
                broken=broken,
                audit_file=audit_file,
            )

        with patch.dict(
            os.environ,
            {
                "DEMO_TOKEN_A": token_a,
                "DEMO_TOKEN_B": token_b,
            },
        ):
            with patch("api.Gateway", side_effect=build_gateway):
                self.app = create_app()

        self.client = self.enterContext(TestClient(self.app))

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_missing_credentials_blocked(self):
        response = self.client.get("/tickets/INC-001")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.headers.get("www-authenticate"),
            "Bearer",
        )

    def test_invalid_credentials_blocked(self):
        response = self.client.get(
            "/tickets/INC-001",
            headers={"Authorization": "Bearer invalid-test-token"},
        )
        self.assertEqual(response.status_code, 401)

    def test_company_a_read_allowed(self):
        response = self.client.get(
            "/tickets/INC-001",
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tenant"], "company-a")

    def test_company_b_read_allowed(self):
        response = self.client.get(
            "/tickets/INC-002",
            headers=self.headers_b,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tenant"], "company-b")

    def test_cross_company_reads_blocked_both_directions(self):
        cases = (
            (self.headers_a, "INC-002"),
            (self.headers_b, "INC-001"),
        )

        for headers, ticket_id in cases:
            with self.subTest(ticket=ticket_id):
                response = self.client.get(
                    f"/tickets/{ticket_id}",
                    headers=headers,
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(
                    response.json(),
                    {"detail": "Ticket unavailable"},
                )

    def test_missing_and_cross_company_responses_match(self):
        forbidden = self.client.get(
            "/tickets/INC-002",
            headers=self.headers_a,
        )
        missing = self.client.get(
            "/tickets/DOES-NOT-EXIST",
            headers=self.headers_a,
        )
        self.assertEqual(forbidden.status_code, 404)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(forbidden.json(), missing.json())

    def test_delete_blocked_and_state_unchanged(self):
        before = copy.deepcopy(self.app.state.gateway.tickets)

        response = self.client.delete(
            "/tickets/INC-001",
            headers=self.headers_a,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.app.state.gateway.tickets,
            before,
        )

        read = self.client.get(
            "/tickets/INC-001",
            headers=self.headers_a,
        )
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.json(), before["INC-001"])

    def test_revocation_blocks_next_request(self):
        first = self.client.get(
            "/tickets/INC-001",
            headers=self.headers_a,
        )
        self.assertEqual(first.status_code, 200)

        self.app.state.gateway.identities["soc-agent"]["active"] = False

        second = self.client.get(
            "/tickets/INC-001",
            headers=self.headers_a,
        )
        self.assertEqual(second.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
