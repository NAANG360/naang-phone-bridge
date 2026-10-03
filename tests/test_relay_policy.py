import unittest

from relay.policy import is_allowed_method


class RelayPolicyTests(unittest.TestCase):
    def test_relay_accepts_typed_method(self):
        self.assertTrue(is_allowed_method("ui.tap"))

    def test_relay_rejects_shell_method(self):
        self.assertFalse(is_allowed_method("shell.exec"))


if __name__ == "__main__":
    unittest.main()
