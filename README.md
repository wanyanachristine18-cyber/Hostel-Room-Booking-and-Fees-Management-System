# University Hostel Room Booking and Fees Management System

A Python-based management system designed to replace paper ledgers used by university hostel wardens. Built with robust domain modeling, capacity-aware room allocation, partial/full fee payment recording, student search, block occupancy reports, fee defaulter tracking, fault-tolerant JSON file persistence, and report exporting (CSV/TXT).

---

## Key Features

1. **Hostel Data Setup**:
   - Preconfigured with 3 distinct hostel blocks:
     - **Block A (Alpha Hall)**: 5 rooms (A-101 to A-105), capacity 2 students/room, base fee: $1,200.00
     - **Block B (Bravo Hall)**: 4 rooms (B-101 to B-104), capacity 3 students/room, base fee: $1,000.00
     - **Block C (Charlie Hall)**: 3 rooms (C-101 to C-103), capacity 4 students/room, base fee: $800.00
   - Immediate startup overview displaying block-by-block capacities, current occupancies, and vacancies.

2. **Student Registration & Room Allocation**:
   - Enforces space constraints: allows allocation only if vacant beds remain.
   - Graceful rejection: clearly explains when a room is at capacity (e.g., `Capacity: 2/2`) and suggests available rooms in the same block.
   - Prevents duplicate student registrations.

3. **Fee Payment Recording & Balance Tracking**:
   - Supports both full payments and multiple partial installment payments over time.
   - Automatically computes remaining outstanding balance.
   - Generates unique transaction IDs and ISO timestamps.
   - Rejects invalid amounts (zero, negative, or payments exceeding remaining balance).

4. **Search and Reporting**:
   - Search by student name (case-insensitive substring match) or registration number (exact or prefix match).
   - Detailed block occupancy reports showing room status (`Empty`, `Partially Occupied`, `Full`) and current occupant names/IDs.
   - Fee defaulters reporting with user-configurable debt thresholds.

5. **File Persistence & Fault Tolerance**:
   - Saves all blocks, rooms, occupants, students, and payment records to `data/hostel_data.json`.
   - Automatic atomic writes to prevent partial file writes.
   - Automatically creates initial data file if missing.
   - Handles corrupted/damaged JSON files gracefully by creating a timestamped backup (`hostel_data.json.corrupt_<timestamp>.bak`) and initializing a clean working state without crashing.

6. **Report Exporting (CSV & TXT)**:
   - Export detailed block occupancy reports to CSV format.
   - Export fee defaulters lists to CSV format.
   - Export comprehensive human-readable summary reports to TXT format.
   - All exported files saved neatly to the `exports/` folder.

7. **Sample Demo Data Seeding**:
   - Pre-packaged demo data generator (`seed_demo_data.py` or menu option `[9]`).
   - Populates 9 realistic students across blocks with cleared accounts, partial payment plans, and unpaid debt for immediate testing.

8. **Warden-Friendly Menu Interface**:
   - Clear 10-option looping CLI menu with formatted ASCII tables.
   - Bulletproof input validation for strings, numbers, choices, and ranges.
   - Catches keyboard interrupts (`Ctrl+C`, `EOF`) gracefully.

---

## Directory Structure

```
Hostel Room Booking and Fees Management System/
│
├── hostel_system/
│   ├── __init__.py
│   ├── models.py              # Room, Block, Student, and PaymentTransaction entities
│   ├── storage.py             # Persistence layer, atomic file writes & corruption recovery
│   ├── manager.py             # Business logic: allocation, fees, search, reports, exports
│   └── cli.py                 # Menu-driven console interface & input validators
│
├── tests/
│   ├── __init__.py
│   ├── test_models.py         # Unit tests for domain models & balance calculations
│   ├── test_manager.py        # Unit tests for room allocation, payments & reports
│   ├── test_storage.py        # Unit tests for file persistence & recovery
│   ├── test_exports.py        # Unit tests for CSV/TXT report exporting & seeding
│   └── test_cli_integration.py# End-to-end simulated CLI integration test
│
├── data/
│   └── hostel_data.json       # Auto-generated runtime persistence file
│
├── exports/                   # Directory containing exported CSV and TXT reports
│
├── main.py                    # Application entry point
├── seed_demo_data.py          # Standalone demo data seeder script
└── README.md                  # System documentation
```

---

## Getting Started

### Prerequisites
- Python 3.10 or newer (tested with Python 3.14).
- No third-party dependencies required (pure standard library).

### Quick Demo Setup
To seed the system with realistic demonstration records:
```bash
py seed_demo_data.py
```

### Running the Application
```bash
py main.py
```
or
```bash
python main.py
```

### Running the Full Automated Test Suite (39 Tests)
```bash
py -m unittest discover -s tests -v
```
