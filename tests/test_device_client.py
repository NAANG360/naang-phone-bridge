import unittest

from relay.device_client import is_allowed_method


class DeviceClientTests(unittest.TestCase):
    def test_allows_typed_phone_methods(self):
        self.assertTrue(is_allowed_method("device.info"))
        self.assertTrue(is_allowed_method("ui.tap"))
        self.assertTrue(is_allowed_method("ui.screenshot"))

    def test_rejects_arbitrary_shell_methods(self):
        self.assertFalse(is_allowed_method("shell.exec"))
        self.assertFalse(is_allowed_method("su"))


if __name__ == "__main__":
    unittest.main()
