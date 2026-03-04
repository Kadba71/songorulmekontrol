import tempfile
import unittest
from pathlib import Path

import database


class DatabaseTests(unittest.TestCase):
    def test_add_list_and_daily_violation(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            database.DB_PATH = Path(tmpdir) / "test_bot_data.sqlite3"
            try:
                database.init_db()
                database.set_department_threshold("satis", 20)
                database.add_personnel("@ali", "@yonetici", "satis")

                rows = database.list_personnel()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["username"], "ali")
                self.assertEqual(rows[0]["department_name"], "satis")

                personnel_id = int(rows[0]["id"])
                database.add_violation_event(
                    personnel_id=personnel_id,
                    minutes=22,
                    occurred_at_iso="2026-03-02T10:00:00+03:00",
                    occurred_date="2026-03-02",
                )

                counts = database.get_daily_violation_counts("2026-03-02")
                self.assertEqual(len(counts), 1)
                self.assertEqual(int(counts[0]["violation_count"]), 1)
            finally:
                database.DB_PATH = original_db_path

    def test_set_and_get_break_window(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            database.DB_PATH = Path(tmpdir) / "test_bot_data.sqlite3"
            try:
                database.init_db()
                database.set_break_window("14:00", "15:00")
                start_hhmm, end_hhmm = database.get_break_window()
                self.assertEqual(start_hhmm, "14:00")
                self.assertEqual(end_hhmm, "15:00")
            finally:
                database.DB_PATH = original_db_path

    def test_cancel_personnel_hourly_off_with_department(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            database.DB_PATH = Path(tmpdir) / "test_bot_data.sqlite3"
            try:
                database.init_db()
                database.add_personnel("@ali", "@yonetici", "satis")
                database.set_personnel_hourly_off("@ali", "2026-03-02T12:00:00+03:00")

                self.assertTrue(database.cancel_personnel_hourly_off("@ali", "satis"))
                self.assertFalse(database.cancel_personnel_hourly_off("@ali", "satis"))
                self.assertFalse(database.cancel_personnel_hourly_off("@ali", "muhasebe"))
            finally:
                database.DB_PATH = original_db_path

    def test_cancel_personnel_day_off_with_department(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            database.DB_PATH = Path(tmpdir) / "test_bot_data.sqlite3"
            try:
                database.init_db()
                database.add_personnel("@veli", "@yonetici", "satis")
                database.set_personnel_day_off_today("@veli", "2026-03-02")

                self.assertTrue(database.cancel_personnel_day_off("@veli", "satis"))
                self.assertFalse(database.cancel_personnel_day_off("@veli", "satis"))
                self.assertFalse(database.cancel_personnel_day_off("@veli", "muhasebe"))
            finally:
                database.DB_PATH = original_db_path

    def test_list_departments_with_weekly_off(self) -> None:
        original_db_path = database.DB_PATH
        with tempfile.TemporaryDirectory() as tmpdir:
            database.DB_PATH = Path(tmpdir) / "test_bot_data.sqlite3"
            try:
                database.init_db()
                database.add_department("satis")
                database.add_department("muhasebe")
                database.set_department_weekly_off("satis", "çarşamba")

                rows = database.list_departments_with_weekly_off()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["name"], "satis")
                self.assertEqual(rows[0]["weekly_off_day"], "çarşamba")
            finally:
                database.DB_PATH = original_db_path


if __name__ == "__main__":
    unittest.main()
