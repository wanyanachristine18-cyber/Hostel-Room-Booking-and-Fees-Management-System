"""Entry point for the Hostel Room Booking and Fees Management System.

Launches the application, initializes storage and business logic,
displays the startup occupancy overview, and enters the warden menu loop.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Ensure package can be imported from current working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from hostel_system.manager import HostelManager
from hostel_system.cli import HostelCLI


def main() -> None:
    """Initialize and run the hostel management application."""
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    try:
        manager = HostelManager()
        cli = HostelCLI(manager)
        cli.run()
    except (KeyboardInterrupt, EOFError):
        print("\n\nApplication terminated by user. Goodbye!")
        sys.exit(0)
    except Exception as exc:
        print(f"\n[CRITICAL ERROR] An unexpected error occurred: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
