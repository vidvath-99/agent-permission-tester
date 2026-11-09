import copy
import sys
import unittest

from gateway import AUDIT_FILE, Gateway

BROKEN = "--broken" in sys.argv


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.gateway = Gateway(broken=BROKEN)

    def test_own_company_read_allowed(self):
        result = self.gateway.call(
            "soc-agent", "tickets:read", "INC-001"
        )
        self.assertEqual(result["tenant"], "company-a")

    def test_cross_company_read_blocked(self):
        with self.assertRaisesRegex(
            PermissionError, "tenant_mismatch"
        ):
            self.gateway.call(
                "soc-agent", "tickets:read", "INC-002"
            )

        self.assertEqual(
            self.gateway.audit[-1]["decision"], "deny"
        )

    def test_delete_blocked_and_ticket_unchanged(self):
        before = copy.deepcopy(self.gateway.tickets)

        with self.assertRaisesRegex(
            PermissionError, "missing_permission"
        ):
            self.gateway.call(
                "soc-agent", "tickets:delete", "INC-001"
            )

        self.assertEqual(self.gateway.tickets, before)

    def test_revocation_blocks_next_call(self):
        self.gateway.call(
            "soc-agent", "tickets:read", "INC-001"
        )
        self.gateway.identities["soc-agent"]["active"] = False

        with self.assertRaisesRegex(
            PermissionError, "access_revoked"
        ):
            self.gateway.call(
                "soc-agent", "tickets:read", "INC-001"
            )

    def test_unknown_tool_blocked(self):
        with self.assertRaisesRegex(
            PermissionError, "unknown_tool"
        ):
            self.gateway.call(
                "soc-agent", "shell:execute", "INC-001"
            )

    def test_malicious_ticket_cannot_authorize_delete(self):
        result = self.gateway.call(
            "soc-agent", "tickets:read", "INC-003"
        )
        self.assertIn("Ignore all rules", result["body"])

        with self.assertRaisesRegex(
            PermissionError, "missing_permission"
        ):
            self.gateway.call(
                "soc-agent", "tickets:delete", "INC-001"
            )

        self.assertIn("INC-001", self.gateway.tickets)

    def test_unknown_identity_blocked(self):
        with self.assertRaisesRegex(
            PermissionError, "unknown_identity"
        ):
            self.gateway.call(
                "unregistered-agent", "tickets:read", "INC-001"
            )


if __name__ == "__main__":
    print("Mode:", "BROKEN" if BROKEN else "SECURE")
    print("Audit log:", AUDIT_FILE)
    unittest.main(argv=[sys.argv[0]], verbosity=2)
