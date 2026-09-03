"""Domain models for Hostel Room Booking and Fees Management System.

Defines core entities: Room, Block, Student, and PaymentTransaction,
with encapsulation of business invariants and serialization support.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class PaymentTransaction:
    """Represents an individual fee payment transaction made by a student."""

    transaction_id: str
    student_reg_no: str
    amount: float
    timestamp: str
    remarks: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to a dictionary suitable for JSON serialization."""
        return {
            "transaction_id": self.transaction_id,
            "student_reg_no": self.student_reg_no,
            "amount": round(self.amount, 2),
            "timestamp": self.timestamp,
            "remarks": self.remarks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PaymentTransaction:
        """Construct a PaymentTransaction from a dictionary."""
        return cls(
            transaction_id=str(data["transaction_id"]),
            student_reg_no=str(data["student_reg_no"]).strip(),
            amount=float(data["amount"]),
            timestamp=str(data["timestamp"]),
            remarks=str(data.get("remarks", "")),
        )


@dataclass
class Room:
    """Represents a hostel room with fixed capacity and tracked occupants."""

    room_number: str
    block_name: str
    capacity: int
    occupant_reg_nos: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError(f"Room capacity must be positive, got {self.capacity}")

    @property
    def current_occupancy(self) -> int:
        """Current number of allocated occupants."""
        return len(self.occupant_reg_nos)

    @property
    def is_full(self) -> bool:
        """True if current occupancy has reached maximum capacity."""
        return self.current_occupancy >= self.capacity

    @property
    def available_spots(self) -> int:
        """Remaining capacity in the room."""
        return max(0, self.capacity - self.current_occupancy)

    def add_occupant(self, reg_no: str) -> None:
        """Allocate an occupant to this room if space remains."""
        clean_reg = reg_no.strip()
        if not clean_reg:
            raise ValueError("Registration number cannot be empty.")
        if self.is_full:
            raise ValueError(
                f"Room '{self.room_number}' in {self.block_name} is full "
                f"(Capacity: {self.capacity}/{self.capacity})."
            )
        if clean_reg in self.occupant_reg_nos:
            raise ValueError(f"Student '{clean_reg}' is already allocated to room '{self.room_number}'.")
        self.occupant_reg_nos.append(clean_reg)

    def remove_occupant(self, reg_no: str) -> None:
        """Remove an occupant from this room."""
        clean_reg = reg_no.strip()
        if clean_reg in self.occupant_reg_nos:
            self.occupant_reg_nos.remove(clean_reg)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Room to a dictionary for JSON serialization."""
        return {
            "room_number": self.room_number,
            "block_name": self.block_name,
            "capacity": self.capacity,
            "occupant_reg_nos": list(self.occupant_reg_nos),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Room:
        """Construct a Room from a dictionary."""
        return cls(
            room_number=str(data["room_number"]).strip(),
            block_name=str(data["block_name"]).strip(),
            capacity=int(data["capacity"]),
            occupant_reg_nos=[str(r).strip() for r in data.get("occupant_reg_nos", [])],
        )


@dataclass
class Block:
    """Represents a hostel block containing multiple rooms and a base fee."""

    name: str
    base_fee: float
    rooms: Dict[str, Room] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.base_fee < 0:
            raise ValueError(f"Base fee cannot be negative, got {self.base_fee}")

    @property
    def total_capacity(self) -> int:
        """Total student capacity across all rooms in this block."""
        return sum(room.capacity for room in self.rooms.values())

    @property
    def total_occupants(self) -> int:
        """Total currently allocated occupants in this block."""
        return sum(room.current_occupancy for room in self.rooms.values())

    @property
    def available_spots(self) -> int:
        """Total available spots in this block."""
        return max(0, self.total_capacity - self.total_occupants)

    @property
    def occupancy_rate(self) -> float:
        """Percentage of occupied beds in this block."""
        if self.total_capacity == 0:
            return 0.0
        return round((self.total_occupants / self.total_capacity) * 100, 1)

    def add_room(self, room: Room) -> None:
        """Add a room to this block."""
        self.rooms[room.room_number] = room

    def get_room(self, room_number: str) -> Optional[Room]:
        """Retrieve a room by room number."""
        return self.rooms.get(room_number.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Convert Block to a dictionary for JSON serialization."""
        return {
            "name": self.name,
            "base_fee": round(self.base_fee, 2),
            "rooms": {r_num: r.to_dict() for r_num, r in self.rooms.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Block:
        """Construct a Block from a dictionary."""
        block = cls(
            name=str(data["name"]).strip(),
            base_fee=float(data.get("base_fee", 0.0)),
        )
        rooms_dict = data.get("rooms", {})
        for r_num, r_data in rooms_dict.items():
            block.rooms[r_num] = Room.from_dict(r_data)
        return block


@dataclass
class Student:
    """Represents a registered student, their allocated room, and financial ledger."""

    reg_no: str
    name: str
    allocated_room: Optional[str] = None
    total_fee: float = 0.0
    paid_fee: float = 0.0
    payments: List[PaymentTransaction] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reg_no = self.reg_no.strip().upper()
        self.name = self.name.strip()
        if not self.reg_no:
            raise ValueError("Student registration number cannot be empty.")
        if not self.name:
            raise ValueError("Student name cannot be empty.")
        if self.total_fee < 0:
            raise ValueError("Total fee cannot be negative.")
        if self.paid_fee < 0:
            raise ValueError("Paid fee cannot be negative.")

    @property
    def balance(self) -> float:
        """Outstanding balance remaining to be paid."""
        return max(0.0, round(self.total_fee - self.paid_fee, 2))

    def is_defaulter(self, threshold: float) -> bool:
        """True if outstanding balance is strictly greater than the threshold."""
        return self.balance > threshold

    def record_payment(
        self,
        amount: float,
        remarks: str = "",
        transaction_id: Optional[str] = None,
        timestamp: Optional[str] = None,
    ) -> PaymentTransaction:
        """Record a valid fee payment against this student's account.

        Raises ValueError if amount <= 0 or if payment exceeds outstanding balance.
        """
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        rounded_amount = round(amount, 2)
        current_balance = self.balance

        if rounded_amount > current_balance:
            raise ValueError(
                f"Payment amount (${rounded_amount:.2f}) exceeds outstanding balance (${current_balance:.2f})."
            )

        tx_id = transaction_id or f"TXN-{uuid.uuid4().hex[:8].upper()}"
        ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        transaction = PaymentTransaction(
            transaction_id=tx_id,
            student_reg_no=self.reg_no,
            amount=rounded_amount,
            timestamp=ts,
            remarks=remarks.strip(),
        )

        self.payments.append(transaction)
        self.paid_fee = round(self.paid_fee + rounded_amount, 2)
        return transaction

    def to_dict(self) -> Dict[str, Any]:
        """Convert Student to a dictionary for JSON serialization."""
        return {
            "reg_no": self.reg_no,
            "name": self.name,
            "allocated_room": self.allocated_room,
            "total_fee": round(self.total_fee, 2),
            "paid_fee": round(self.paid_fee, 2),
            "payments": [p.to_dict() for p in self.payments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Student:
        """Construct a Student from a dictionary."""
        student = cls(
            reg_no=str(data["reg_no"]),
            name=str(data["name"]),
            allocated_room=data.get("allocated_room"),
            total_fee=float(data.get("total_fee", 0.0)),
            paid_fee=float(data.get("paid_fee", 0.0)),
        )
        payments_data = data.get("payments", [])
        student.payments = [PaymentTransaction.from_dict(p) for p in payments_data]
        return student
