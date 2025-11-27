#!/usr/bin/env python
"""
Quick Start Script for the Modern Web Dashboard

Run this script to start the FastAPI web dashboard:
    python run_dashboard.py

The dashboard will be available at:
    http://localhost:8000

Features:
- Modern TailwindCSS UI with dark mode
- Real-time statistics and charts
- Thread filtering and search
- Responsive design
- Interactive visualizations with Chart.js
"""

import sys
import webbrowser
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Start the web dashboard"""
    try:
        from web_dashboard import start_dashboard
        
        # Open browser automatically after a short delay
        import threading
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open("http://localhost:8000")
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Start dashboard
        start_dashboard(host="127.0.0.1", port=8000)
        
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
