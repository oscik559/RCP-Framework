#!/usr/bin/env python
"""
Web Interface Launcher

Convenience launcher for the Flask web interface.
Provides quick access to the web UI from the project root.

Usage:
    python run_web.py [--host HOST] [--port PORT] [--debug]

Examples:
    python run_web.py                    # Run on localhost:5000
    python run_web.py --port 8080        # Custom port
    python run_web.py --debug            # Enable Flask debug mode
    python run_web.py --host 0.0.0.0     # Listen on all interfaces

Note:
    Package should be installed with: pip install -e .
    This enables clean imports without sys.path manipulation.
"""

import argparse
import os
import sys

# Ensure UTF-8 encoding for Windows (must be before any import that prints)
if sys.platform.startswith("win"):
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from Layer_3_User_Interface.web_app import app


def main():
    """Launch the Flask web interface."""
    parser = argparse.ArgumentParser(
        description="Launch the Flask web interface for agentic reasoning system"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1, use 0.0.0.0 for all interfaces)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on (default: 5000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Flask debug mode (default: use FLASK_DEBUG env var)",
    )

    args = parser.parse_args()

    # Override debug mode if specified
    debug_mode = args.debug or os.getenv("FLASK_DEBUG", "false").lower() == "true"

    print("=" * 60)
    print("🌐 RCP Framework - Agentic Reasoning Web Interface")
    print("=" * 60)
    print(f"📍 URL: http://{args.host}:{args.port}")
    print(f"🔧 Debug Mode: {'ON' if debug_mode else 'OFF'}")
    print(f"💡 Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    try:
        app.run(debug=debug_mode, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n\n👋 Web server stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
