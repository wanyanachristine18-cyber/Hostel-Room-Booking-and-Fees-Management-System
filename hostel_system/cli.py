"""Menu-driven command-line interface for the Hostel Room Booking and Fees Management System.

Designed for a hostel warden with no programming background, featuring
strict input validation, clear formatting, and structured reports.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, List, Optional
from hostel_system.manager import HostelManager
from hostel_system.models import Student


def print_banner(title: str) -> None:
    """Print a visually distinct header banner."""
    line = "=" * 68
    print(f"\n{line}")
    print(f" {title.center(66)} ")
    print(f"{line}")


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n--- {title} " + "-" * max(0, 60 - len(title)))


def prompt_string(
    prompt_text: str,
    allow_empty: bool = False,
    to_upper: bool = False,
) -> str:
    """Prompt the user for a string with non-empty validation."""
    while True:
        try:
            val = input(f"{prompt_text}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            raise
        if not val and not allow_empty:
            print("  [!] Input cannot be blank. Please enter a valid value.")
            continue
        return val.upper() if to_upper else val


def prompt_float(
    prompt_text: str,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
    default: Optional[float] = None,
) -> float:
    """Prompt the user for a floating-point number with range validation."""
    while True:
        suffix = f" (default: {default})" if default is not None else ""
        try:
            raw = input(f"{prompt_text}{suffix}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            raise
        if not raw and default is not None:
            return default
        try:
            val = float(raw)
        except ValueError:
            print("  [!] Invalid number. Please enter a valid numeric value.")
            continue

        if min_val is not None and val < min_val:
            print(f"  [!] Value must be at least {min_val}.")
            continue
        if max_val is not None and val > max_val:
            print(f"  [!] Value must not exceed {max_val}.")
            continue
        return val


def prompt_int(
    prompt_text: str,
    min_val: int,
    max_val: int,
) -> int:
    """Prompt for an integer within a specific inclusive range."""
    while True:
        try:
            raw = input(f"{prompt_text} [{min_val}-{max_val}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            raise
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  [!] Choice out of range. Please choose between {min_val} and {max_val}.")
        except ValueError:
            print(f"  [!] Invalid entry. Please enter a whole number between {min_val} and {max_val}.")


def pause() -> None:
    """Pause execution until user presses Enter."""
    try:
        input("\nPress [Enter] to return to the menu...")
    except (KeyboardInterrupt, EOFError):
        pass


class HostelCLI:
    """Console interface driving warden interactions with the HostelManager."""

    def __init__(self, manager: HostelManager) -> None:
        self.manager = manager

    def display_startup_overview(self) -> None:
        """Display the initial occupancy overview when the application starts."""
        print_banner("UNIVERSITY HOSTEL ROOM BOOKING & FEES SYSTEM")
        if self.manager.init_message:
            print(f"\n[NOTICE] {self.manager.init_message}\n")
        self.display_occupancy_overview(pause_after=False)

    def display_occupancy_overview(self, pause_after: bool = True) -> None:
        """Render a formatted summary table of all hostel blocks and current occupancy."""
        overview = self.manager.get_brief_overview()
        print_section("Hostel Blocks Occupancy Overview")

        header = f"{'Block Name':<14} | {'Base Fee':<10} | {'Rooms':<6} | {'Capacity':<9} | {'Occupied':<9} | {'Available':<10} | {'Occupancy %':<11}"
        sep = "-" * len(header)
        print(header)
        print(sep)

        for b in overview["blocks"]:
            fee_str = f"${b['base_fee']:,.2f}"
            rate_str = f"{b['occupancy_rate']:.1f}%"
            print(
                f"{b['block_name']:<14} | {fee_str:<10} | {b['rooms_count']:<6} | "
                f"{b['total_capacity']:<9} | {b['occupied_beds']:<9} | {b['available_beds']:<10} | {rate_str:<11}"
            )

        print(sep)
        tot = overview["totals"]
        tot_rate = f"{tot['overall_occupancy_rate']:.1f}%"
        print(
            f"{'TOTALS':<14} | {'-':<10} | {tot['total_rooms']:<6} | "
            f"{tot['total_capacity']:<9} | {tot['occupied_beds']:<9} | {tot['available_beds']:<10} | {tot_rate:<11}"
        )
        print(f"\nRegistered Active Students in System: {tot['total_students']}")
        if pause_after:
            pause()

    def handle_room_allocation(self) -> None:
        """Guide warden through registering a student and allocating a room."""
        print_section("Register Student & Allocate Room")
        print("Tip: Enter student registration number, full name, and desired room code (e.g. A-101).")

        name = prompt_string("Enter Student Full Name")
        reg_no = prompt_string("Enter Student Registration Number", to_upper=True)

        # Show quick list of available rooms per block
        print("\nCurrently Available Rooms:")
        for block_name, block in self.manager.blocks.items():
            avail = self.manager.get_available_rooms_in_block(block_name)
            avail_str = ", ".join(sorted(avail)) if avail else "FULL (None available)"
            print(f"  * {block_name}: {avail_str}")

        room_number = prompt_string("\nEnter Room to Allocate (e.g., A-101)", to_upper=True)

        success, message, _ = self.manager.allocate_student(name, reg_no, room_number)
        if success:
            print(f"\n[OK] {message}")
        else:
            print(f"\n[ERROR] {message}")
        pause()

    def handle_fee_payment(self) -> None:
        """Guide warden through recording full or partial fee payments."""
        print_section("Record Student Fee Payment")
        reg_no = prompt_string("Enter Student Registration Number", to_upper=True)
        student = self.manager.get_student(reg_no)

        if not student:
            print(f"\n[ERROR] No student found with registration number '{reg_no}'.")
            pause()
            return

        print(f"\nStudent Details:")
        print(f"  * Name            : {student.name}")
        print(f"  * Allocated Room  : {student.allocated_room or 'None'}")
        print(f"  * Total Fee Due   : ${student.total_fee:,.2f}")
        print(f"  * Total Paid      : ${student.paid_fee:,.2f}")
        print(f"  * Current Balance : ${student.balance:,.2f}")

        if student.balance <= 0.0:
            print("\n[OK] This student has already cleared all hostel fees. No balance remains.")
            pause()
            return

        print(f"\nYou can record a full payment (${student.balance:,.2f}) or any partial payment.")
        amount = prompt_float(
            "Enter Payment Amount ($)",
            min_val=0.01,
            max_val=student.balance,
            default=student.balance,
        )
        remarks = prompt_string("Enter Payment Remarks/Reference (optional)", allow_empty=True)

        success, message, tx = self.manager.record_fee_payment(reg_no, amount, remarks)
        if success and tx:
            print(f"\n[OK] {message}")
            print(f"   Timestamp: {tx.timestamp}")
        else:
            print(f"\n[ERROR] {message}")
        pause()

    def handle_student_search(self) -> None:
        """Search for students by name or registration number."""
        print_section("Search Student Records")
        query = prompt_string("Enter Student Name or Registration Number to search")
        results = self.manager.search_students(query)

        if not results:
            print(f"\nNo student records matched '{query}'.")
            pause()
            return

        print(f"\nFound {len(results)} matching student(s):")
        header = f"{'Reg No':<12} | {'Name':<22} | {'Room':<8} | {'Total Fee':<11} | {'Paid':<11} | {'Balance':<11} | {'Status':<10}"
        sep = "-" * len(header)
        print(header)
        print(sep)

        for s in results:
            status = "CLEARED" if s.balance == 0 else f"DUE (${s.balance:.2f})"
            print(
                f"{s.reg_no:<12} | {s.name[:22]:<22} | {s.allocated_room or '-':<8} | "
                f"${s.total_fee:<10.2f} | ${s.paid_fee:<10.2f} | ${s.balance:<10.2f} | {status:<10}"
            )
        print(sep)
        pause()

    def handle_full_occupancy_report(self) -> None:
        """Display comprehensive room-by-room breakdown per block."""
        print_section("Detailed Hostel Block Occupancy Report")
        report = self.manager.generate_occupancy_report()

        for block in report["blocks"]:
            print(f"\n>>> {block['block_name']} (Base Fee: ${block['base_fee']:,.2f})")
            print(
                f"   Capacity: {block['total_occupants']}/{block['total_capacity']} beds "
                f"({block['occupancy_rate']}% occupied, {block['available_spots']} vacant)"
            )
            header = f"   {'Room':<8} | {'Capacity':<9} | {'Occupied':<9} | {'Vacant':<7} | {'Status':<16} | {'Current Occupants'}"
            sep = "   " + "-" * (len(header) - 3)
            print(header)
            print(sep)

            for room in block["rooms"]:
                occupants_summary = ", ".join(f"{o['name']} ({o['reg_no']})" for o in room["occupants"])
                if not occupants_summary:
                    occupants_summary = "[None]"
                print(
                    f"   {room['room_number']:<8} | {room['capacity']:<9} | "
                    f"{room['current_occupancy']:<9} | {room['available_spots']:<7} | "
                    f"{room['status']:<16} | {occupants_summary}"
                )
            print()
        pause()

    def handle_defaulters_report(self) -> None:
        """Display list of students with outstanding fee balances exceeding a threshold."""
        print_section("Fee Defaulters Report")
        print("Identify students who owe more than a specified debt threshold.")
        threshold = prompt_float("Enter Outstanding Balance Threshold ($)", min_val=0.0, default=0.0)

        defaulters = self.manager.get_fee_defaulters(threshold)

        if not defaulters:
            print(f"\n[OK] Good news! No students have an outstanding balance exceeding ${threshold:,.2f}.")
            pause()
            return

        total_debt = sum(d["balance"] for d in defaulters)
        print(f"\nFound {len(defaulters)} student(s) owing more than ${threshold:,.2f} (Total Outstanding: ${total_debt:,.2f}):")

        header = f"{'Reg No':<12} | {'Name':<22} | {'Room':<8} | {'Total Fee':<11} | {'Paid':<11} | {'Balance Due':<12} | {'Last Payment'}"
        sep = "-" * len(header)
        print(header)
        print(sep)

        for d in defaulters:
            print(
                f"{d['reg_no']:<12} | {d['name'][:22]:<22} | {d['allocated_room']:<8} | "
                f"${d['total_fee']:<10.2f} | ${d['paid_fee']:<10.2f} | "
                f"${d['balance']:<11.2f} | {d['last_payment_date']}"
            )
        print(sep)
        pause()

    def handle_payment_history(self) -> None:
        """Display full ledger and transaction audit trail for an individual student."""
        print_section("Student Ledger & Payment History")
        reg_no = prompt_string("Enter Student Registration Number", to_upper=True)
        student = self.manager.get_student(reg_no)

        if not student:
            print(f"\n[ERROR] Student with registration number '{reg_no}' was not found.")
            pause()
            return

        print(f"\nAccount Summary for {student.name} ({student.reg_no}):")
        print(f"  * Room Allocated   : {student.allocated_room or 'None'}")
        print(f"  * Total Hostel Fee : ${student.total_fee:,.2f}")
        print(f"  * Total Amount Paid: ${student.paid_fee:,.2f}")
        print(f"  * Remaining Balance: ${student.balance:,.2f}")
        print(f"  * Status           : {'CLEARED' if student.balance == 0 else 'OUTSTANDING'}")

        if not student.payments:
            print("\n  [!] No payment transactions have been recorded yet for this student.")
        else:
            print(f"\nTransaction History ({len(student.payments)} transaction(s)):")
            header = f"  {'TXN ID':<16} | {'Date & Time':<20} | {'Amount':<11} | {'Remarks'}"
            sep = "  " + "-" * (len(header) - 2)
            print(header)
            print(sep)
            for tx in student.payments:
                print(f"  {tx.transaction_id:<16} | {tx.timestamp:<20} | ${tx.amount:<10.2f} | {tx.remarks}")
            print(sep)
        pause()

    def handle_export_reports(self) -> None:
        """Export occupancy or defaulters reports to CSV or TXT files."""
        print_section("Export Reports to File")
        print("Select export format:")
        print("  [1] Export Block Occupancy Report (CSV)")
        print("  [2] Export Fee Defaulters Report (CSV)")
        print("  [3] Export Comprehensive Summary Report (TXT)")
        print("  [4] Export All Reports (CSV + TXT)")
        print("  [5] Cancel")

        choice = prompt_int("Choose export option", min_val=1, max_val=5)
        if choice == 5:
            return

        export_dir = Path("exports")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if choice == 1:
            dest = export_dir / f"occupancy_report_{ts}.csv"
            out = self.manager.export_occupancy_report_csv(dest)
            print(f"\n[OK] Occupancy report exported successfully to:\n     {out.resolve()}")
        elif choice == 2:
            threshold = prompt_float("Enter balance threshold for defaulters ($)", min_val=0.0, default=0.0)
            dest = export_dir / f"fee_defaulters_{ts}.csv"
            out = self.manager.export_defaulters_report_csv(dest, threshold=threshold)
            print(f"\n[OK] Fee defaulters report exported successfully to:\n     {out.resolve()}")
        elif choice == 3:
            threshold = prompt_float("Enter balance threshold for defaulters ($)", min_val=0.0, default=0.0)
            dest = export_dir / f"hostel_summary_{ts}.txt"
            out = self.manager.export_summary_text_report(dest, threshold=threshold)
            print(f"\n[OK] Comprehensive text summary exported successfully to:\n     {out.resolve()}")
        elif choice == 4:
            threshold = prompt_float("Enter balance threshold for defaulters ($)", min_val=0.0, default=0.0)
            out1 = self.manager.export_occupancy_report_csv(export_dir / f"occupancy_report_{ts}.csv")
            out2 = self.manager.export_defaulters_report_csv(export_dir / f"fee_defaulters_{ts}.csv", threshold=threshold)
            out3 = self.manager.export_summary_text_report(export_dir / f"hostel_summary_{ts}.txt", threshold=threshold)
            print(f"\n[OK] All 3 reports exported successfully to '{export_dir.resolve()}':")
            print(f"  * {out1.name}")
            print(f"  * {out2.name}")
            print(f"  * {out3.name}")

        pause()

    def handle_seed_demo_data(self) -> None:
        """Seed sample students, room allocations, and payments for testing."""
        print_section("Load Sample Demonstration Data")
        print("This will populate the system with 9 realistic students across all blocks,")
        print("including fully occupied rooms, partial payments, and cleared accounts.")
        print("Warning: This will reset existing active ledger data.")

        confirm = prompt_string("Proceed with demo seeding? (y/n)", to_upper=True)
        if confirm in ("Y", "YES"):
            count = self.manager.seed_sample_data(reset=True)
            print(f"\n[OK] Successfully loaded {count} demonstration students into the system.")
        else:
            print("\nSeeding cancelled.")
        pause()

    def run(self) -> None:
        """Main interaction loop."""
        self.display_startup_overview()

        while True:
            print_banner("MAIN WARDEN MENU")
            print("  [1] View Brief Occupancy Overview")
            print("  [2] Register Student & Allocate Room")
            print("  [3] Record Fee Payment (Full or Partial)")
            print("  [4] Search Student (by Name or Reg Number)")
            print("  [5] Generate Full Block Occupancy Report")
            print("  [6] Generate Fee Defaulters Report")
            print("  [7] View Student Payment History & Ledger")
            print("  [8] Export Reports to File (CSV / TXT)")
            print("  [9] Load Sample Demonstration Data")
            print("  [10] Save & Exit System")
            print("-" * 68)

            try:
                choice = prompt_int("Enter option", min_val=1, max_val=10)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting system safely. Goodbye!")
                break

            if choice == 1:
                self.display_occupancy_overview()
            elif choice == 2:
                self.handle_room_allocation()
            elif choice == 3:
                self.handle_fee_payment()
            elif choice == 4:
                self.handle_student_search()
            elif choice == 5:
                self.handle_full_occupancy_report()
            elif choice == 6:
                self.handle_defaulters_report()
            elif choice == 7:
                self.handle_payment_history()
            elif choice == 8:
                self.handle_export_reports()
            elif choice == 9:
                self.handle_seed_demo_data()
            elif choice == 10:
                try:
                    self.manager.save_data()
                    print("\n[OK] All records saved successfully to file.")
                except IOError as e:
                    print(f"\n[WARNING] Could not save data on exit: {e}")
                print("Thank you for using the Hostel Management System. Goodbye!")
                break
