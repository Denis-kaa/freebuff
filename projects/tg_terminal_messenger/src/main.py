#!/usr/bin/env python3
"""Entry point for tg-terminal-toolkit TUI."""
import sys
***REMOVED***

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ui.app import TGApp


def main() -> None:
    app = TGApp()
    app.run()


if __name__ == "__main__":
    main()
