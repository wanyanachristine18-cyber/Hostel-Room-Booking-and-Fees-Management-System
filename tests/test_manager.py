"""Unit tests for HostelManager: allocation, fee payments, search, and reporting."""

import unittest
import tempfile
import sys
from pathlib import Path

# Ensure project root is in sys.path when running this test file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hostel_system.storage import StorageManager
from hostel_system.manager import HostelManager


class TestHostelManager(unittest.TestCase):
    """Test suite for core hostel business workflows."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "test_hostel.json"
        self.storage = StorageManager(self.file_path)
        self.manager = HostelManager(self.storage)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_brief_overview_initial_state(self):
        overview = self.manager.get_brief_overview()
        self.assertIn("blocks", overview)
        self.assertEqual(len(overview["blocks"]), 3)
        totals = overview["totals"]
        self.assertEqual(totals["total_rooms"], 12)  # 5 + 4 + 3
        self.assertEqual(totals["total_capacity"], 34)  # 5*2 + 4*3 + 3*4 = 10 + 12 + 12 = 34
        self.assertEqual(totals["occupied_beds"], 0)
        self.assertEqual(totals["available_beds"], 34)
        self.assertEqual(totals["overall_occupancy_rate"], 0.0)

    def test_allocate_student_happy_path(self):
        success, msg, student = self.manager.allocate_student(
            name="Charlie Brown",
            reg_no="REG-001",
            room_number="A-101",
        )
        self.assertTrue(success)
        self.assertIsNotNone(student)
        self.assertEqual(student.name, "Charlie Brown")
        self.assertEqual(student.reg_no, "REG-001")
        self.assertEqual(student.allocated_room, "A-101")
        self.assertEqual(student.total_fee, 1200.0)
        self.assertEqual(student.balance, 1200.0)

        # Check room occupancy
        _, room = self.manager.find_room("A-101")
        self.assertEqual(room.current_occupancy, 1)
        self.assertIn("REG-001", room.occupant_reg_nos)

    def test_allocate_student_room_full_rejection_error_path(self):
        # Room A-101 has capacity 2
        s1, _, _ = self.manager.allocate_student("Student One", "S001", "A-101")
        s2, _, _ = self.manager.allocate_student("Student Two", "S002", "A-101")
        self.assertTrue(s1)
        self.assertTrue(s2)

        # 3rd allocation to A-101 must be rejected
        s3, err_msg, student3 = self.manager.allocate_student("Student Three", "S003", "A-101")
        self.assertFalse(s3)
        self.assertIsNone(student3)
        self.assertIn("Allocation Rejected", err_msg)
        self.assertIn("is FULL", err_msg)
        self.assertIn("Capacity: 2/2", err_msg)
        self.assertIn("Available rooms in Block A", err_msg)

    def test_allocate_student_duplicate_reg_no_error_path(self):
        self.manager.allocate_student("Alice", "REG-DUP", "A-101")
        success, err_msg, _ = self.manager.allocate_student("Alice Again", "REG-DUP", "A-102")
        self.assertFalse(success)
        self.assertIn("already exists", err_msg)

    def test_allocate_student_non_existent_room_error_path(self):
        success, err_msg, _ = self.manager.allocate_student("Bob", "REG-NON", "Z-999")
        self.assertFalse(success)
        self.assertIn("does not exist", err_msg)

    def test_allocate_student_validation_errors(self):
        s1, m1, _ = self.manager.allocate_student("", "REG-X", "A-101")
        self.assertFalse(s1)
        self.assertIn("cannot be empty", m1)

        s2, m2, _ = self.manager.allocate_student("Bob", "", "A-101")
        self.assertFalse(s2)
        self.assertIn("cannot be empty", m2)

    def test_fee_payment_happy_path(self):
        # Allocate student to Block B (base fee $1000.0)
        self.manager.allocate_student("David", "REG-B1", "B-101")

        # Payment 1: partial payment of $350
        p1, m1, tx1 = self.manager.record_fee_payment("REG-B1", 350.0, remarks="Deposit")
        self.assertTrue(p1)
        self.assertEqual(tx1.amount, 350.0)
        student = self.manager.get_student("REG-B1")
        self.assertEqual(student.balance, 650.0)

        # Payment 2: partial payment of $400
        p2, m2, tx2 = self.manager.record_fee_payment("REG-B1", 400.0, remarks="Second installment")
        self.assertTrue(p2)
        self.assertEqual(student.balance, 250.0)

        # Payment 3: final payment of $250
        p3, m3, tx3 = self.manager.record_fee_payment("REG-B1", 250.0, remarks="Settled")
        self.assertTrue(p3)
        self.assertEqual(student.balance, 0.0)
        self.assertEqual(len(student.payments), 3)

    def test_fee_payment_non_existent_student_error_path(self):
        success, err_msg, _ = self.manager.record_fee_payment("NON-EXISTENT", 100.0)
        self.assertFalse(success)
        self.assertIn("not found", err_msg)

    def test_fee_payment_overpayment_rejected_error_path(self):
        self.manager.allocate_student("Eve", "REG-E1", "C-101")  # Fee: 800.0
        success, err_msg, _ = self.manager.record_fee_payment("REG-E1", 900.0)
        self.assertFalse(success)
        self.assertIn("exceeds outstanding balance", err_msg)

    def test_fee_payment_already_cleared_error_path(self):
        self.manager.allocate_student("Frank", "REG-F1", "C-101")  # Fee: 800.0
        self.manager.record_fee_payment("REG-F1", 800.0)
        success, err_msg, _ = self.manager.record_fee_payment("REG-F1", 10.0)
        self.assertFalse(success)
        self.assertIn("already fully cleared", err_msg)

    def test_search_students(self):
        self.manager.allocate_student("Michael Scott", "REG-M1", "A-101")
        self.manager.allocate_student("Dwight Schrute", "REG-D1", "A-102")
        self.manager.allocate_student("Jim Halpert", "REG-J1", "B-101")

        # Search by exact reg_no
        res1 = self.manager.search_students("REG-M1")
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0].name, "Michael Scott")

        # Search by partial name (case-insensitive)
        res2 = self.manager.search_students("dwight")
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0].reg_no, "REG-D1")

        # Search matching multiple ("sc")
        res3 = self.manager.search_students("sc")
        names = [s.name for s in res3]
        self.assertIn("Michael Scott", names)
        self.assertIn("Dwight Schrute", names)

        # Search not found
        res4 = self.manager.search_students("Pam")
        self.assertEqual(len(res4), 0)

    def test_generate_occupancy_report(self):
        self.manager.allocate_student("Alice", "REG-A1", "A-101")
        report = self.manager.generate_occupancy_report()
        self.assertIn("blocks", report)
        self.assertEqual(len(report["blocks"]), 3)

        block_a_report = next(b for b in report["blocks"] if b["block_name"] == "Block A")
        self.assertEqual(block_a_report["total_occupants"], 1)
        room_a101 = next(r for r in block_a_report["rooms"] if r["room_number"] == "A-101")
        self.assertEqual(room_a101["current_occupancy"], 1)
        self.assertEqual(room_a101["status"], "Partially Occupied")
        self.assertEqual(room_a101["occupants"][0]["reg_no"], "REG-A1")

    def test_fee_defaulters_threshold(self):
        # Alice owes 1200
        self.manager.allocate_student("Alice", "REG-1", "A-101")
        # Bob owes 1000 - 600 = 400
        self.manager.allocate_student("Bob", "REG-2", "B-101")
        self.manager.record_fee_payment("REG-2", 600.0)
        # Charlie owes 800 - 800 = 0
        self.manager.allocate_student("Charlie", "REG-3", "C-101")
        self.manager.record_fee_payment("REG-3", 800.0)

        # Defaulters threshold 500: only Alice (1200 > 500)
        defaulters_500 = self.manager.get_fee_defaulters(threshold=500.0)
        self.assertEqual(len(defaulters_500), 1)
        self.assertEqual(defaulters_500[0]["reg_no"], "REG-1")

        # Defaulters threshold 0: Alice (1200) and Bob (400), Charlie (0) excluded
        defaulters_0 = self.manager.get_fee_defaulters(threshold=0.0)
        self.assertEqual(len(defaulters_0), 2)
        self.assertEqual(defaulters_0[0]["reg_no"], "REG-1")  # Sorted descending
        self.assertEqual(defaulters_0[1]["reg_no"], "REG-2")


if __name__ == "__main__":
    unittest.main()
