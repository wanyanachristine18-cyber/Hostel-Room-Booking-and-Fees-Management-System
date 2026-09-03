"""Unit tests for report exporting (CSV, TXT) and demo data seeding."""

import unittest
import tempfile
import csv
import sys
from pathlib import Path

# Ensure project root is in sys.path when running this test file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hostel_system.storage import StorageManager
from hostel_system.manager import HostelManager


class TestExportsAndSeeding(unittest.TestCase):
    """Test data seeding and report exporting functionality."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "test_hostel.json"
        self.storage = StorageManager(self.storage_path)
        self.manager = HostelManager(self.storage)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_sample_data(self):
        count = self.manager.seed_sample_data(reset=True)
        self.assertEqual(count, 9)
        self.assertEqual(len(self.manager.students), 9)

        # Verify Block A room A-101 is full (Alice and Bob)
        _, room_a101 = self.manager.find_room("A-101")
        self.assertTrue(room_a101.is_full)
        self.assertEqual(room_a101.current_occupancy, 2)

        # Verify Alice is fully paid ($1200.0, balance 0)
        alice = self.manager.get_student("UG-2026-001")
        self.assertEqual(alice.balance, 0.0)
        self.assertEqual(alice.paid_fee, 1200.0)

        # Verify Bob has partial payment (paid 600, balance 600)
        bob = self.manager.get_student("UG-2026-002")
        self.assertEqual(bob.paid_fee, 600.0)
        self.assertEqual(bob.balance, 600.0)

        # Verify Charlie has 0 payments (balance 1200)
        charlie = self.manager.get_student("UG-2026-003")
        self.assertEqual(charlie.paid_fee, 0.0)
        self.assertEqual(charlie.balance, 1200.0)

    def test_export_occupancy_report_csv(self):
        self.manager.seed_sample_data(reset=True)
        csv_path = Path(self.temp_dir.name) / "exports" / "test_occupancy.csv"
        out_path = self.manager.export_occupancy_report_csv(csv_path)

        self.assertTrue(out_path.exists())

        with open(out_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # 12 total rooms in the hostel
        self.assertEqual(len(rows), 12)

        # Verify A-101 row
        a101_row = next(r for r in rows if r["Room Number"] == "A-101")
        self.assertEqual(a101_row["Block"], "Block A")
        self.assertEqual(a101_row["Capacity"], "2")
        self.assertEqual(a101_row["Occupancy"], "2")
        self.assertEqual(a101_row["Vacant Beds"], "0")
        self.assertEqual(a101_row["Status"], "Full")
        self.assertIn("Alice Johnson", a101_row["Occupant Names"])
        self.assertIn("Bob Smith", a101_row["Occupant Names"])

    def test_export_defaulters_report_csv(self):
        self.manager.seed_sample_data(reset=True)
        csv_path = Path(self.temp_dir.name) / "exports" / "test_defaulters.csv"

        # Threshold $500: students with balance > 500
        # Bob (600), Charlie (1200), Frank (700), Grace (800) -> 4 students
        out_path = self.manager.export_defaulters_report_csv(csv_path, threshold=500.0)
        self.assertTrue(out_path.exists())

        with open(out_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 4)
        balances = [float(r["Balance Due ($)"]) for r in rows]
        # Should be sorted descending
        self.assertEqual(balances, sorted(balances, reverse=True))
        for b in balances:
            self.assertGreater(b, 500.0)

    def test_export_summary_text_report(self):
        self.manager.seed_sample_data(reset=True)
        txt_path = Path(self.temp_dir.name) / "exports" / "test_summary.txt"
        out_path = self.manager.export_summary_text_report(txt_path, threshold=300.0)

        self.assertTrue(out_path.exists())
        with open(out_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("UNIVERSITY HOSTEL MANAGEMENT SYSTEM - COMPREHENSIVE REPORT", content)
        self.assertIn("1. HOSTEL OCCUPANCY OVERVIEW", content)
        self.assertIn("2. DETAILED BLOCK & ROOM OCCUPANCY", content)
        self.assertIn("3. FEE DEFAULTERS REPORT", content)
        self.assertIn("Block A", content)
        self.assertIn("Block B", content)
        self.assertIn("Block C", content)
        self.assertIn("Alice Johnson", content)


if __name__ == "__main__":
    unittest.main()
