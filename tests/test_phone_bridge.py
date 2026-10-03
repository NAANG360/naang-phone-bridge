import unittest

from magisk.phone_bridge import parse_current_activity


class PhoneBridgeTests(unittest.TestCase):
    def test_parse_current_activity_returns_package_and_activity(self):
        line = "mCurrentFocus=Window{49a u0 com.termux/com.termux.app.TermuxActivity}"
        self.assertEqual(parse_current_activity(line), {
            "package": "com.termux",
            "activity": "com.termux.app.TermuxActivity",
        })

    def test_parse_current_activity_rejects_unrelated_line(self):
        self.assertIsNone(parse_current_activity("InsetsPolicy status: WINDOW_STATE_SHOWING"))


if __name__ == "__main__":
    unittest.main()
