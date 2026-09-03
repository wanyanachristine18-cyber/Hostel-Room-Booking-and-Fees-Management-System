"""Core business logic manager for Hostel Room Booking and Fees Management System.

Encapsulates room allocation, fee recording, search operations, reporting,
and persistence orchestration.
"""

from __future__ import annotations
import csv
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from hostel_system.models import Block, Room, Student, PaymentTransaction
from hostel_system.storage import StorageManager, DEFAULT_STORAGE_PATH, get_default_blocks


class HostelManager:
    """Coordinates business operations for hostel room bookings and fee management."""

    def __init__(self, storage: Optional[StorageManager] = None) -> None:
        self.storage = storage or StorageManager(DEFAULT_STORAGE_PATH)
        self.blocks: Dict[str, Block] = {}
        self.students: Dict[str, Student] = {}
        self.init_message: Optional[str] = None
        self.reload_data()

    def reload_data(self) -> None:
        """Load or reload all data from the storage persistence layer."""
        self.blocks, self.students, self.init_message = self.storage.load_data()

    def save_data(self) -> None:
        """Persist current state to disk."""
        self.storage.save_data(self.blocks, self.students)

    # -------------------------------------------------------------------------
    # a) Data setup & Occupancy Overview
    # -------------------------------------------------------------------------
    def get_brief_overview(self) -> Dict[str, Any]:
        """Generate a concise occupancy overview across all hostel blocks."""
        blocks_summary = []
        total_rooms = 0
        total_capacity = 0
        total_occupants = 0

        for block in self.blocks.values():
            r_count = len(block.rooms)
            b_cap = block.total_capacity
            b_occ = block.total_occupants
            b_avail = block.available_spots
            b_rate = block.occupancy_rate

            total_rooms += r_count
            total_capacity += b_cap
            total_occupants += b_occ

            blocks_summary.append({
                "block_name": block.name,
                "base_fee": block.base_fee,
                "rooms_count": r_count,
                "total_capacity": b_cap,
                "occupied_beds": b_occ,
                "available_beds": b_avail,
                "occupancy_rate": b_rate,
            })

        total_avail = max(0, total_capacity - total_occupants)
        overall_rate = round((total_occupants / total_capacity * 100), 1) if total_capacity > 0 else 0.0

        return {
            "blocks": blocks_summary,
            "totals": {
                "total_rooms": total_rooms,
                "total_capacity": total_capacity,
                "occupied_beds": total_occupants,
                "available_beds": total_avail,
                "overall_occupancy_rate": overall_rate,
                "total_students": len(self.students),
            },
        }

    # -------------------------------------------------------------------------
    # b) Student registration & Room allocation
    # -------------------------------------------------------------------------
    def find_room(self, room_number: str) -> Optional[Tuple[Block, Room]]:
        """Look up a room case-insensitively across all hostel blocks."""
        target = room_number.strip().upper()
        for block in self.blocks.values():
            for r_num, room in block.rooms.items():
                if r_num.upper() == target:
                    return block, room
        return None

    def get_available_rooms_in_block(self, block_name: str) -> List[str]:
        """List room numbers that still have remaining capacity in a block."""
        block = self.blocks.get(block_name)
        if not block:
            return []
        return [r.room_number for r in block.rooms.values() if not r.is_full]

    def allocate_student(
        self,
        name: str,
        reg_no: str,
        room_number: str,
    ) -> Tuple[bool, str, Optional[Student]]:
        """Register a new student and allocate them to a specified room.

        Invariants enforced:
        - Name and registration number must be non-empty.
        - Registration number must be unique.
        - Room must exist.
        - Room must have remaining capacity; rejects with clear explanation if full.
        """
        clean_name = name.strip()
        clean_reg = reg_no.strip().upper()
        clean_room = room_number.strip().upper()

        if not clean_name:
            return False, "Validation Error: Student name cannot be empty.", None

        if not clean_reg:
            return False, "Validation Error: Registration number cannot be empty.", None

        if clean_reg in self.students:
            existing = self.students[clean_reg]
            return (
                False,
                f"Registration Error: Student with registration number '{clean_reg}' already exists "
                f"({existing.name}, Room: {existing.allocated_room or 'None'}).",
                None,
            )

        lookup = self.find_room(clean_room)
        if not lookup:
            valid_rooms = [r for b in self.blocks.values() for r in b.rooms.keys()]
            return (
                False,
                f"Allocation Error: Room '{clean_room}' does not exist. "
                f"Valid rooms: {', '.join(sorted(valid_rooms))}",
                None,
            )

        block, room = lookup

        if room.is_full:
            available_rooms = self.get_available_rooms_in_block(block.name)
            avail_msg = (
                f"Available rooms in {block.name}: {', '.join(available_rooms)}"
                if available_rooms
                else f"No rooms currently available in {block.name}."
            )
            return (
                False,
                f"Allocation Rejected: Room '{room.room_number}' in {block.name} is FULL "
                f"(Capacity: {room.capacity}/{room.capacity}). {avail_msg}",
                None,
            )

        # Space remains: execute allocation
        room.add_occupant(clean_reg)
        student = Student(
            reg_no=clean_reg,
            name=clean_name,
            allocated_room=room.room_number,
            total_fee=block.base_fee,
            paid_fee=0.0,
            payments=[],
        )
        self.students[clean_reg] = student
        self.save_data()

        success_msg = (
            f"Success: Student {clean_name} ({clean_reg}) allocated to Room {room.room_number} "
            f"({block.name}). Current Room Occupancy: {room.current_occupancy}/{room.capacity}. "
            f"Semester Fee: ${block.base_fee:.2f}."
        )
        return True, success_msg, student

    # -------------------------------------------------------------------------
    # c) Fee payment recording
    # -------------------------------------------------------------------------
    def record_fee_payment(
        self,
        reg_no: str,
        amount: float,
        remarks: str = "",
    ) -> Tuple[bool, str, Optional[PaymentTransaction]]:
        """Record full or partial fee payments against a student's account.

        Invariants enforced:
        - Student must exist.
        - Amount must be positive.
        - Amount must not exceed outstanding balance.
        """
        clean_reg = reg_no.strip().upper()
        if clean_reg not in self.students:
            return False, f"Payment Error: Student with registration number '{clean_reg}' not found.", None

        student = self.students[clean_reg]

        if student.balance <= 0.0:
            return (
                False,
                f"Payment Error: Student {student.name} ({student.reg_no}) has already fully cleared all fees. "
                f"(Total Fee: ${student.total_fee:.2f}, Paid: ${student.paid_fee:.2f}).",
                None,
            )

        try:
            tx = student.record_payment(amount=amount, remarks=remarks)
            self.save_data()
            msg = (
                f"Payment Recorded: ${tx.amount:.2f} credited for {student.name} ({student.reg_no}). "
                f"Transaction ID: {tx.transaction_id}. "
                f"Remaining Outstanding Balance: ${student.balance:.2f}."
            )
            return True, msg, tx
        except ValueError as err:
            return False, f"Payment Rejected: {err}", None

    # -------------------------------------------------------------------------
    # d) Search and reporting
    # -------------------------------------------------------------------------
    def search_students(self, query: str) -> List[Student]:
        """Search students by registration number or name (case-insensitive substring match)."""
        clean_query = query.strip().upper()
        if not clean_query:
            return []

        results: List[Student] = []
        for student in self.students.values():
            if clean_query in student.reg_no.upper() or clean_query in student.name.upper():
                results.append(student)

        # Sort exact reg_no matches first, then alphabetically by name
        results.sort(key=lambda s: (s.reg_no.upper() != clean_query, s.name.lower()))
        return results

    def generate_occupancy_report(self) -> Dict[str, Any]:
        """Generate a full, detailed occupancy report for each hostel block."""
        report_blocks = []

        for block in self.blocks.values():
            block_data = {
                "block_name": block.name,
                "base_fee": block.base_fee,
                "total_capacity": block.total_capacity,
                "total_occupants": block.total_occupants,
                "available_spots": block.available_spots,
                "occupancy_rate": block.occupancy_rate,
                "rooms": [],
            }

            for r_num in sorted(block.rooms.keys()):
                room = block.rooms[r_num]
                occupant_details = []
                for o_reg in room.occupant_reg_nos:
                    student = self.students.get(o_reg)
                    occupant_details.append({
                        "reg_no": o_reg,
                        "name": student.name if student else "Unknown",
                    })

                status = "Full" if room.is_full else ("Empty" if room.current_occupancy == 0 else "Partially Occupied")
                block_data["rooms"].append({
                    "room_number": room.room_number,
                    "capacity": room.capacity,
                    "current_occupancy": room.current_occupancy,
                    "available_spots": room.available_spots,
                    "status": status,
                    "occupants": occupant_details,
                })

            report_blocks.append(block_data)

        return {"blocks": report_blocks}

    def get_fee_defaulters(self, threshold: float) -> List[Dict[str, Any]]:
        """Generate a list of fee defaulters whose outstanding balance is strictly above threshold."""
        clean_threshold = max(0.0, round(threshold, 2))
        defaulters = []

        for student in self.students.values():
            if student.is_defaulter(clean_threshold):
                last_tx = student.payments[-1] if student.payments else None
                defaulters.append({
                    "reg_no": student.reg_no,
                    "name": student.name,
                    "allocated_room": student.allocated_room or "Unassigned",
                    "total_fee": student.total_fee,
                    "paid_fee": student.paid_fee,
                    "balance": student.balance,
                    "last_payment_date": last_tx.timestamp if last_tx else "No payments made",
                    "total_payments_count": len(student.payments),
                })

        # Sort by balance descending (highest debt first)
        defaulters.sort(key=lambda d: d["balance"], reverse=True)
        return defaulters

    def get_student(self, reg_no: str) -> Optional[Student]:
        """Retrieve a student by registration number."""
        return self.students.get(reg_no.strip().upper())

    # -------------------------------------------------------------------------
    # Report Exporting (CSV & TXT)
    # -------------------------------------------------------------------------
    def export_occupancy_report_csv(self, filepath: str | Path) -> Path:
        """Export the detailed block occupancy report to a CSV file."""
        target_path = Path(filepath)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        report = self.generate_occupancy_report()

        fieldnames = [
            "Block",
            "Room Number",
            "Capacity",
            "Occupancy",
            "Vacant Beds",
            "Status",
            "Occupant Names",
            "Occupant Reg Nos",
        ]

        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for block in report["blocks"]:
                for room in block["rooms"]:
                    names = ", ".join(o["name"] for o in room["occupants"])
                    regs = ", ".join(o["reg_no"] for o in room["occupants"])
                    writer.writerow({
                        "Block": block["block_name"],
                        "Room Number": room["room_number"],
                        "Capacity": room["capacity"],
                        "Occupancy": room["current_occupancy"],
                        "Vacant Beds": room["available_spots"],
                        "Status": room["status"],
                        "Occupant Names": names,
                        "Occupant Reg Nos": regs,
                    })

        return target_path

    def export_defaulters_report_csv(self, filepath: str | Path, threshold: float = 0.0) -> Path:
        """Export the fee defaulters list to a CSV file."""
        target_path = Path(filepath)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        defaulters = self.get_fee_defaulters(threshold)

        fieldnames = [
            "Reg No",
            "Name",
            "Room",
            "Total Fee ($)",
            "Paid Fee ($)",
            "Balance Due ($)",
            "Payments Made",
            "Last Payment Date",
        ]

        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in defaulters:
                writer.writerow({
                    "Reg No": d["reg_no"],
                    "Name": d["name"],
                    "Room": d["allocated_room"],
                    "Total Fee ($)": f"{d['total_fee']:.2f}",
                    "Paid Fee ($)": f"{d['paid_fee']:.2f}",
                    "Balance Due ($)": f"{d['balance']:.2f}",
                    "Payments Made": d["total_payments_count"],
                    "Last Payment Date": d["last_payment_date"],
                })

        return target_path

    def export_summary_text_report(self, filepath: str | Path, threshold: float = 0.0) -> Path:
        """Export a comprehensive human-readable summary report to a text file."""
        target_path = Path(filepath)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        overview = self.get_brief_overview()
        report = self.generate_occupancy_report()
        defaulters = self.get_fee_defaulters(threshold)

        lines: List[str] = []
        lines.append("=" * 72)
        lines.append("     UNIVERSITY HOSTEL MANAGEMENT SYSTEM - COMPREHENSIVE REPORT")
        lines.append("=" * 72)
        lines.append("")

        # Section 1: Overview
        lines.append("1. HOSTEL OCCUPANCY OVERVIEW")
        lines.append("-" * 72)
        tot = overview["totals"]
        lines.append(f"Total Rooms     : {tot['total_rooms']}")
        lines.append(f"Total Capacity  : {tot['total_capacity']} beds")
        lines.append(f"Occupied Beds   : {tot['occupied_beds']} beds")
        lines.append(f"Available Beds  : {tot['available_beds']} beds")
        lines.append(f"Overall Rate    : {tot['overall_occupancy_rate']}%\n")

        # Section 2: Detailed block rooms
        lines.append("2. DETAILED BLOCK & ROOM OCCUPANCY")
        lines.append("-" * 72)
        for block in report["blocks"]:
            lines.append(f"\nBlock: {block['block_name']} (Base Fee: ${block['base_fee']:.2f})")
            lines.append(f"Capacity: {block['total_occupants']}/{block['total_capacity']} beds | Vacant: {block['available_spots']}")
            for r in block["rooms"]:
                occ_str = ", ".join(f"{o['name']} ({o['reg_no']})" for o in r["occupants"]) or "[None]"
                lines.append(f"  Room {r['room_number']:<6} | {r['current_occupancy']}/{r['capacity']} beds | {r['status']:<16} | Occupants: {occ_str}")
        lines.append("")

        # Section 3: Defaulters
        lines.append(f"3. FEE DEFAULTERS REPORT (Threshold: > ${threshold:.2f})")
        lines.append("-" * 72)
        if not defaulters:
            lines.append("No fee defaulters found matching this threshold.\n")
        else:
            tot_debt = sum(d["balance"] for d in defaulters)
            lines.append(f"Found {len(defaulters)} defaulter(s) - Total Outstanding Debt: ${tot_debt:.2f}\n")
            lines.append(f"{'Reg No':<12} | {'Name':<22} | {'Room':<8} | {'Total Fee':<10} | {'Paid':<10} | {'Balance Due'}")
            lines.append("-" * 72)
            for d in defaulters:
                lines.append(
                    f"{d['reg_no']:<12} | {d['name'][:22]:<22} | {d['allocated_room']:<8} | "
                    f"${d['total_fee']:<9.2f} | ${d['paid_fee']:<9.2f} | ${d['balance']:.2f}"
                )
        lines.append("\n" + "=" * 72)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return target_path

    # -------------------------------------------------------------------------
    # Demo Data Seeding
    # -------------------------------------------------------------------------
    def seed_sample_data(self, reset: bool = True) -> int:
        """Seed realistic sample students, room allocations, and payments across all blocks.

        Args:
            reset: If True, resets rooms to empty before seeding.

        Returns:
            The number of students seeded.
        """
        if reset:
            self.blocks = get_default_blocks()
            self.students = {}

        demo_students = [
            # Block A ($1200 base fee, capacity 2)
            {
                "name": "Alice Johnson",
                "reg_no": "UG-2026-001",
                "room": "A-101",
                "payments": [(1200.0, "Full semester fee cleared via Bank Transfer")],
            },
            {
                "name": "Bob Smith",
                "reg_no": "UG-2026-002",
                "room": "A-101",
                "payments": [(600.0, "First 50% installment")],
            },
            {
                "name": "Charlie Davis",
                "reg_no": "UG-2026-003",
                "room": "A-102",
                "payments": [],  # Zero payments made
            },
            # Block B ($1000 base fee, capacity 3)
            {
                "name": "David Miller",
                "reg_no": "UG-2026-004",
                "room": "B-101",
                "payments": [
                    (500.0, "First installment via Mobile Money"),
                    (250.0, "Second installment"),
                ],
            },
            {
                "name": "Emma Wilson",
                "reg_no": "UG-2026-005",
                "room": "B-101",
                "payments": [(1000.0, "Full payment upfront")],
            },
            {
                "name": "Frank Thomas",
                "reg_no": "UG-2026-006",
                "room": "B-102",
                "payments": [(300.0, "Deposit")],
            },
            # Block C ($800 base fee, capacity 4)
            {
                "name": "Grace Lee",
                "reg_no": "UG-2026-007",
                "room": "C-101",
                "payments": [],  # Zero payment
            },
            {
                "name": "Henry Clark",
                "reg_no": "UG-2026-008",
                "room": "C-101",
                "payments": [(400.0, "Part payment")],
            },
            {
                "name": "Ian Wright",
                "reg_no": "UG-2026-009",
                "room": "C-101",
                "payments": [(800.0, "Full settlement")],
            },
        ]

        for s_data in demo_students:
            success, _, student = self.allocate_student(
                name=s_data["name"],
                reg_no=s_data["reg_no"],
                room_number=s_data["room"],
            )
            if success and student:
                for amount, remarks in s_data["payments"]:
                    self.record_fee_payment(
                        reg_no=student.reg_no,
                        amount=amount,
                        remarks=remarks,
                    )

        self.save_data()
        return len(demo_students)
