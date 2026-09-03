"""Script to seed the Hostel Management System with realistic demonstration data.

Populates Block A, Block B, and Block C with sample students, room allocations,
full payments, partial installment payments, and unpaid balances for testing.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hostel_system.manager import HostelManager


def main() -> None:
    print("=" * 68)
    print("      SEEDING HOSTEL MANAGEMENT SYSTEM WITH SAMPLE DEMO DATA        ")
    print("=" * 68)

    manager = HostelManager()
    count = manager.seed_sample_data(reset=True)

    print(f"\n[OK] Successfully registered and allocated {count} demonstration students.")
    print(f"[OK] Ledger saved to '{manager.storage.filepath}'.\n")

    overview = manager.get_brief_overview()
    tot = overview["totals"]
    print(f"Summary:")
    print(f"  * Total Students   : {tot['total_students']}")
    print(f"  * Occupied Beds    : {tot['occupied_beds']} / {tot['total_capacity']}")
    print(f"  * Occupancy Rate   : {tot['overall_occupancy_rate']}%")
    print(f"  * Available Beds   : {tot['available_beds']}")

    print("\nYou can now launch the application using:")
    print("  py main.py\n")


if __name__ == "__main__":
    main()
