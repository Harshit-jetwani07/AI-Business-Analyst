import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from utils import auth
from utils.ai_agent import sanitized_dataframe
from utils.forecaster import Forecaster


class SecurityRegressionTests(unittest.TestCase):
    def test_demo_accounts_are_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(auth, "DB_PATH", str(Path(tmp) / "users.db")):
                with mock.patch.dict("os.environ", {}, clear=True):
                    auth.init_db()
                    self.assertEqual(auth.get_all_users(), [])

    def test_login_failures_lock_account_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(auth, "DB_PATH", str(Path(tmp) / "users.db")):
                auth.init_db()
                for _ in range(auth.MAX_LOGIN_FAILURES):
                    auth.record_login_failure("target")

                self.assertIsNotNone(auth.get_login_lock("target"))
                auth.clear_login_failures("target")
                self.assertIsNone(auth.get_login_lock("target"))

    def test_ai_context_masks_sensitive_values(self):
        df = pd.DataFrame({
            "email": ["person@example.com"],
            "notes": ["call +91 98765 43210 tomorrow"],
            "sales": [1200],
        })

        safe = sanitized_dataframe(df)

        self.assertEqual(safe.loc[0, "email"], "[REDACTED]")
        self.assertIn("[PHONE]", safe.loc[0, "notes"])
        self.assertEqual(safe.loc[0, "sales"], 1200)

    def test_forecast_uses_numeric_text_instead_of_row_counts(self):
        df = pd.DataFrame({
            "Date": pd.date_range("2024-01-01", periods=8),
            "Revenue": ["(1,000)", "1,100", "1,200", "1,300", "1,400", "1,500", "1,600", "1,700"],
        })

        fig, metrics = Forecaster(df, "Date", "Revenue").forecast(4)

        self.assertIsNotNone(fig, metrics)
        self.assertNotIn("error", metrics)


if __name__ == "__main__":
    unittest.main()
