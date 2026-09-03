"""Unit tests for domain models: Room, Block, Student, and PaymentTransaction."""

import unittest
import sys
from pathlib import Path

# Ensure project root is in sys.path when running this test file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hostel_system.models import Room, Block, Student, PaymentTransaction


class TestRoomModel(unittest.TestCase):
    """Test Room invariants, occupancy calculations, and occupant management."""

    def test_room_initialization_happy_path(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=2)
        self.assertEqual(room.room_number, "A-101")
        self.assertEqual(room.block_name, "Block A")
        self.assertEqual(room.capacity, 2)
        self.assertEqual(room.current_occupancy, 0)
        self.assertEqual(room.available_spots, 2)
        self.assertFalse(room.is_full)

    def test_room_capacity_non_positive_error_path(self):
        with self.assertRaises(ValueError):
            Room(room_number="A-101", block_name="Block A", capacity=0)
        with self.assertRaises(ValueError):
            Room(room_number="A-101", block_name="Block A", capacity=-1)

    def test_add_occupant_happy_path(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=2)
        room.add_occupant("REG001")
        self.assertEqual(room.current_occupancy, 1)
        self.assertEqual(room.available_spots, 1)
        self.assertFalse(room.is_full)

        room.add_occupant("REG002")
        self.assertEqual(room.current_occupancy, 2)
        self.assertEqual(room.available_spots, 0)
        self.assertTrue(room.is_full)

    def test_add_occupant_full_room_error_path(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=1)
        room.add_occupant("REG001")
        with self.assertRaises(ValueError) as ctx:
            room.add_occupant("REG002")
        self.assertIn("is full", str(ctx.exception))

    def test_add_occupant_duplicate_error_path(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=2)
        room.add_occupant("REG001")
        with self.assertRaises(ValueError) as ctx:
            room.add_occupant("REG001")
        self.assertIn("already allocated", str(ctx.exception))

    def test_add_occupant_empty_reg_error_path(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=2)
        with self.assertRaises(ValueError):
            room.add_occupant("   ")

    def test_remove_occupant(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=2)
        room.add_occupant("REG001")
        room.remove_occupant("REG001")
        self.assertEqual(room.current_occupancy, 0)
        self.assertEqual(room.available_spots, 2)

    def test_room_serialization_round_trip(self):
        room = Room(room_number="A-101", block_name="Block A", capacity=3, occupant_reg_nos=["R1", "R2"])
        d = room.to_dict()
        reconstructed = Room.from_dict(d)
        self.assertEqual(reconstructed.room_number, room.room_number)
        self.assertEqual(reconstructed.capacity, room.capacity)
        self.assertEqual(reconstructed.occupant_reg_nos, ["R1", "R2"])


class TestBlockModel(unittest.TestCase):
    """Test Block aggregations, fee invariants, and serialization."""

    def test_block_aggregations(self):
        block = Block(name="Block A", base_fee=1200.0)
        r1 = Room(room_number="A-101", block_name="Block A", capacity=2)
        r2 = Room(room_number="A-102", block_name="Block A", capacity=3)
        block.add_room(r1)
        block.add_room(r2)

        self.assertEqual(block.total_capacity, 5)
        self.assertEqual(block.total_occupants, 0)
        self.assertEqual(block.available_spots, 5)
        self.assertEqual(block.occupancy_rate, 0.0)

        r1.add_occupant("R1")
        r2.add_occupant("R2")
        self.assertEqual(block.total_occupants, 2)
        self.assertEqual(block.available_spots, 3)
        self.assertEqual(block.occupancy_rate, 40.0)

    def test_negative_base_fee_error_path(self):
        with self.assertRaises(ValueError):
            Block(name="Invalid Block", base_fee=-100.0)

    def test_block_serialization_round_trip(self):
        block = Block(name="Block B", base_fee=1000.0)
        r = Room(room_number="B-101", block_name="Block B", capacity=2)
        block.add_room(r)
        d = block.to_dict()
        reconstructed = Block.from_dict(d)
        self.assertEqual(reconstructed.name, "Block B")
        self.assertEqual(reconstructed.base_fee, 1000.0)
        self.assertIn("B-101", reconstructed.rooms)


class TestStudentModel(unittest.TestCase):
    """Test Student fee payments, balance tracking, and defaulter status."""

    def test_student_initialization_happy_path(self):
        student = Student(reg_no="REG100", name="Alice Johnson", allocated_room="A-101", total_fee=1200.0)
        self.assertEqual(student.reg_no, "REG100")
        self.assertEqual(student.name, "Alice Johnson")
        self.assertEqual(student.balance, 1200.0)
        self.assertEqual(student.paid_fee, 0.0)
        self.assertEqual(len(student.payments), 0)

    def test_student_empty_name_or_reg_error_path(self):
        with self.assertRaises(ValueError):
            Student(reg_no="", name="Alice")
        with self.assertRaises(ValueError):
            Student(reg_no="REG100", name="")

    def test_multiple_payments_over_time_happy_path(self):
        student = Student(reg_no="REG100", name="Alice Johnson", total_fee=1200.0)

        # Payment 1: Partial payment of $400
        tx1 = student.record_payment(400.0, remarks="First installment")
        self.assertEqual(student.paid_fee, 400.0)
        self.assertEqual(student.balance, 800.0)
        self.assertEqual(tx1.amount, 400.0)

        # Payment 2: Second partial payment of $500
        tx2 = student.record_payment(500.0, remarks="Second installment")
        self.assertEqual(student.paid_fee, 900.0)
        self.assertEqual(student.balance, 300.0)
        self.assertEqual(len(student.payments), 2)

        # Payment 3: Final payment clearing debt
        student.record_payment(300.0, remarks="Final balance")
        self.assertEqual(student.paid_fee, 1200.0)
        self.assertEqual(student.balance, 0.0)

    def test_payment_zero_or_negative_error_path(self):
        student = Student(reg_no="REG100", name="Alice", total_fee=1000.0)
        with self.assertRaises(ValueError) as ctx:
            student.record_payment(0.0)
        self.assertIn("greater than zero", str(ctx.exception))

        with self.assertRaises(ValueError):
            student.record_payment(-50.0)

    def test_overpayment_rejected_error_path(self):
        student = Student(reg_no="REG100", name="Alice", total_fee=1000.0, paid_fee=800.0)
        # Outstanding balance is 200.0
        with self.assertRaises(ValueError) as ctx:
            student.record_payment(250.0)
        self.assertIn("exceeds outstanding balance", str(ctx.exception))

    def test_is_defaulter(self):
        student = Student(reg_no="REG100", name="Alice", total_fee=1200.0, paid_fee=700.0)
        # balance = 500.0
        self.assertTrue(student.is_defaulter(threshold=0.0))
        self.assertTrue(student.is_defaulter(threshold=400.0))
        self.assertFalse(student.is_defaulter(threshold=500.0))
        self.assertFalse(student.is_defaulter(threshold=600.0))


if __name__ == "__main__":
    unittest.main()
