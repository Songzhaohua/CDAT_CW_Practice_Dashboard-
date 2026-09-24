import unittest
from pathlib import Path

from sync_data import refresh_local_snapshot


class RefreshLocalSnapshotTests(unittest.TestCase):
    def test_refresh_local_snapshot_copies_source_file(self):
        source = Path("test_source.csv")
        source.write_text("name,practice_lot_qty\nA,10\n", encoding="utf-8")
        destination = Path("test_snapshot.csv")

        try:
            ok, message = refresh_local_snapshot(str(source), destination)
            self.assertTrue(ok)
            self.assertEqual(destination.read_text(encoding="utf-8"), "name,practice_lot_qty\nA,10\n")
            self.assertIn("copied", message.lower())
        finally:
            source.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
