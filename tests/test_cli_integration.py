"""Integration test simulating Warden CLI interactions end-to-end."""

import unittest
import io
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

# Ensure project root is in sys.path when running this test file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hostel_system.storage import StorageManager
from hostel_system.manager import HostelManager
from hostel_system.cli import HostelCLI


class TestCLIIntegration(unittest.TestCase):
    """Simulate complete user journeys through the HostelCLI menu."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "hostel.json"
        self.storage = StorageManager(self.storage_path)
        self.manager = HostelManager(self.storage)
        self.cli = HostelCLI(self.manager)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_complete_warden_workflow(self):
        """Simulate a warden performing the complete series of actions:
        1. View overview (option 1, press enter)
        2. Allocate student 1 (option 2, name: Alice, reg: R001, room: A-101, press enter)
        3. Allocate student 2 (option 2, name: Bob, reg: R002, room: A-101, press enter)
        4. Attempt allocate student 3 into full room A-101 (option 2, name: Charlie, reg: R003, room: A-101, press enter)
        5. Record partial fee payment of $500 for Alice (option 3, reg: R001, amount: 500, remarks: "Part 1", press enter)
        6. Search for student "Alice" (option 4, query: Alice, press enter)
        7. Full occupancy report (option 5, press enter)
        8. Defaulters report with threshold $400 (option 6, threshold: 400, press enter)
        9. Payment history for Alice (option 7, reg: R001, press enter)
        10. Save and exit (option 8)
        """
        simulated_inputs = [
            # 1. View brief overview
            "1", "",
            # 2. Allocate Alice to A-101
            "2", "Alice Smith", "R001", "A-101", "",
            # 3. Allocate Bob to A-101
            "2", "Bob Jones", "R002", "A-101", "",
            # 4. Try allocating Charlie to full room A-101
            "2", "Charlie Brown", "R003", "A-101", "",
            # 5. Record fee payment for Alice ($500)
            "3", "R001", "500.0", "Installment 1", "",
            # 6. Search for Alice
            "4", "Alice", "",
            # 7. Detailed occupancy report
            "5", "",
            # 8. Fee defaulters report with threshold 400
            "6", "400.0", "",
            # 9. View payment history for Alice
            "7", "R001", "",
            # 10. Export all reports (option 8 -> choice 4 -> threshold 400 -> press enter)
            "8", "4", "400.0", "",
            # 11. Save and exit
            "10",
        ]

        output_buffer = io.StringIO()
        with patch("builtins.input", side_effect=simulated_inputs):
            with patch("sys.stdout", output_buffer):
                self.cli.run()

        output_text = output_buffer.getvalue()

        # Assertions on CLI output
        self.assertIn("UNIVERSITY HOSTEL ROOM BOOKING & FEES SYSTEM", output_text)
        self.assertIn("Hostel Blocks Occupancy Overview", output_text)
        self.assertIn("Alice Smith (R001) allocated to Room A-101", output_text)
        self.assertIn("Bob Jones (R002) allocated to Room A-101", output_text)
        self.assertIn("Allocation Rejected: Room 'A-101' in Block A is FULL", output_text)
        self.assertIn("Payment Recorded: $500.00 credited for Alice Smith", output_text)
        self.assertIn("Remaining Outstanding Balance: $700.00", output_text)
        self.assertIn("Found 1 matching student(s)", output_text)
        self.assertIn("Detailed Hostel Block Occupancy Report", output_text)
        self.assertIn("Fee Defaulters Report", output_text)
        self.assertIn("Installment 1", output_text)
        self.assertIn("All 3 reports exported successfully", output_text)
        self.assertIn("All records saved successfully to file", output_text)

        # Verify data persisted on disk
        reloaded_blocks, reloaded_students, _ = self.storage.load_data()
        self.assertIn("R001", reloaded_students)
        self.assertIn("R002", reloaded_students)
        self.assertNotIn("R003", reloaded_students)
        self.assertEqual(reloaded_students["R001"].paid_fee, 500.0)
        self.assertEqual(reloaded_students["R001"].balance, 700.0)


if __name__ == "__main__":
    unittest.main()
