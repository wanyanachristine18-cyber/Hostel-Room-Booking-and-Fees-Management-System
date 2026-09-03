"""Unit tests for the storage persistence layer and corruption recovery."""

import unittest
import tempfile
import json
import sys
from pathlib import Path

# Ensure project root is in sys.path when running this test file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hostel_system.storage import StorageManager, get_default_blocks
from hostel_system.models import Student


class TestStorageManager(unittest.TestCase):
    """Test file persistence, missing file handling, and corruption recovery."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "test_hostel_data.json"
        self.storage = StorageManager(self.file_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_file_initializes_defaults_gracefully(self):
        self.assertFalse(self.file_path.exists())
        blocks, students, msg = self.storage.load_data()
        self.assertIsNotNone(msg)
        self.assertIn("was not found", msg)
        self.assertIn("Block A", blocks)
        self.assertIn("Block B", blocks)
        self.assertIn("Block C", blocks)
        self.assertEqual(len(students), 0)
        # Verify file was created
        self.assertTrue(self.file_path.exists())

    def test_save_and_load_round_trip(self):
        blocks = get_default_blocks()
        blocks["Block A"].rooms["A-101"].add_occupant("REG001")

        student = Student(
            reg_no="REG001",
            name="Bob Smith",
            allocated_room="A-101",
            total_fee=1200.0,
            paid_fee=0.0,
        )
        student.record_payment(400.0, remarks="Deposit")
        students = {"REG001": student}

        self.storage.save_data(blocks, students)
        self.assertTrue(self.file_path.exists())

        loaded_blocks, loaded_students, msg = self.storage.load_data()
        self.assertIsNone(msg)
        self.assertIn("REG001", loaded_students)
        loaded_student = loaded_students["REG001"]
        self.assertEqual(loaded_student.name, "Bob Smith")
        self.assertEqual(loaded_student.allocated_room, "A-101")
        self.assertEqual(loaded_student.balance, 800.0)
        self.assertEqual(len(loaded_student.payments), 1)
        self.assertEqual(loaded_blocks["Block A"].rooms["A-101"].occupant_reg_nos, ["REG001"])

    def test_corrupted_json_recovers_gracefully_with_backup(self):
        # Write damaged content to the data file
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("{ invalid json content !!! [ }")

        blocks, students, warning_msg = self.storage.load_data()

        # System should NOT crash, should return default blocks and empty students
        self.assertIsNotNone(warning_msg)
        self.assertIn("damaged or invalid", warning_msg)
        self.assertIn("Block A", blocks)
        self.assertEqual(len(students), 0)

        # A backup file should have been created
        backup_files = list(self.temp_dir.name.glob("*.bak") if hasattr(self.temp_dir.name, "glob") else Path(self.temp_dir.name).glob("*.bak"))
        self.assertGreater(len(backup_files), 0)

    def test_missing_required_schema_keys_recovers_gracefully(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump({"unrelated_key": 123}, f)

        blocks, students, warning_msg = self.storage.load_data()
        self.assertIsNotNone(warning_msg)
        self.assertIn("damaged or invalid", warning_msg)
        self.assertIn("Block A", blocks)
        self.assertEqual(len(students), 0)


if __name__ == "__main__":
    unittest.main()
