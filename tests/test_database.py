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


if __name__ == "__main__":
    unittest.main()
