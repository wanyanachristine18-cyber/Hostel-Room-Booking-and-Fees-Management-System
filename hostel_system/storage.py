"""Data persistence layer for Hostel Room Booking and Fees Management System.

Handles atomic saving, loading, corruption detection, backup creation,
and graceful fallback to default hostel setup.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple

from hostel_system.models import Block, Room, Student


DEFAULT_STORAGE_PATH = Path("data") / "hostel_data.json"


def get_default_blocks() -> Dict[str, Block]:
    """Predefine at least three hostel blocks with fixed rooms and capacities.

    Configuration:
    - Block A (Alpha Hall): 5 rooms, capacity 2 each, fee $1,200.00
    - Block B (Bravo Hall): 4 rooms, capacity 3 each, fee $1,000.00
    - Block C (Charlie Hall): 3 rooms, capacity 4 each, fee $800.00
    """
    blocks: Dict[str, Block] = {}

    # Block A
    block_a = Block(name="Block A", base_fee=1200.0)
    for i in range(101, 106):
        r_num = f"A-{i}"
        block_a.add_room(Room(room_number=r_num, block_name="Block A", capacity=2))
    blocks[block_a.name] = block_a

    # Block B
    block_b = Block(name="Block B", base_fee=1000.0)
    for i in range(101, 105):
        r_num = f"B-{i}"
        block_b.add_room(Room(room_number=r_num, block_name="Block B", capacity=3))
    blocks[block_b.name] = block_b

    # Block C
    block_c = Block(name="Block C", base_fee=800.0)
    for i in range(101, 104):
        r_num = f"C-{i}"
        block_c.add_room(Room(room_number=r_num, block_name="Block C", capacity=4))
    blocks[block_c.name] = block_c

    return blocks


class StorageManager:
    """Manages file storage, data serialization, and corruption recovery."""

    def __init__(self, filepath: Path | str = DEFAULT_STORAGE_PATH) -> None:
        self.filepath = Path(filepath)

    def save_data(
        self,
        blocks: Dict[str, Block],
        students: Dict[str, Student],
    ) -> None:
        """Atomically save hostel blocks and students to a JSON file."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "version": "1.0",
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "blocks": {name: block.to_dict() for name, block in blocks.items()},
            "students": {reg_no: student.to_dict() for reg_no, student in students.items()},
        }

        # Atomic write pattern: write to tmp file then rename
        temp_filepath = self.filepath.with_suffix(".tmp")
        try:
            with open(temp_filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            temp_filepath.replace(self.filepath)
        except OSError as e:
            if temp_filepath.exists():
                try:
                    temp_filepath.unlink()
                except OSError:
                    pass
            raise IOError(f"Failed to persist hostel data to '{self.filepath}': {e}") from e

    def load_data(self) -> Tuple[Dict[str, Block], Dict[str, Student], Optional[str]]:
        """Load data from disk.

        Returns:
            Tuple of (blocks, students, status_message).
            status_message is non-None if file was missing, newly created, or recovered from corruption.
        """
        if not self.filepath.exists():
            default_blocks = get_default_blocks()
            empty_students: Dict[str, Student] = {}
            # Persist initial setup so file exists for future runs
            try:
                self.save_data(default_blocks, empty_students)
                msg = f"Data file '{self.filepath}' was not found. Initialized new ledger with default hostel blocks."
            except IOError:
                msg = "Data file was not found. Using in-memory default hostel blocks."
            return default_blocks, empty_students, msg

        # Attempt to read and parse the existing file
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    raise ValueError("Data file is empty.")
                data = json.loads(content)

            if not isinstance(data, dict):
                raise ValueError("Root JSON element must be an object.")

            if "blocks" not in data or "students" not in data:
                raise KeyError("Missing required keys ('blocks', 'students') in data file.")

            # Reconstruct blocks
            blocks: Dict[str, Block] = {}
            for b_name, b_data in data["blocks"].items():
                blocks[b_name] = Block.from_dict(b_data)

            # Reconstruct students
            students: Dict[str, Student] = {}
            for s_reg, s_data in data["students"].items():
                student = Student.from_dict(s_data)
                students[student.reg_no] = student

            # Ensure default blocks are present if any were missing
            defaults = get_default_blocks()
            for def_name, def_block in defaults.items():
                if def_name not in blocks:
                    blocks[def_name] = def_block

            return blocks, students, None

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as err:
            # Corrupted data detected: gracefully backup and reset to defaults
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.filepath.with_suffix(f".corrupt_{timestamp}.bak")
            try:
                if self.filepath.exists():
                    self.filepath.replace(backup_path)
            except OSError:
                pass

            default_blocks = get_default_blocks()
            empty_students = {}
            try:
                self.save_data(default_blocks, empty_students)
            except IOError:
                pass

            warning_msg = (
                f"WARNING: The data file '{self.filepath}' was damaged or invalid ({err}). "
                f"A backup was saved to '{backup_path.name}'. "
                f"A clean system state has been initialized so you can continue safely."
            )
            return default_blocks, empty_students, warning_msg
