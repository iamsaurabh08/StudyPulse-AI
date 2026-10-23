import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure backend package can be imported regardless of execution path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from backend.app import app

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    print("=" * 60)
    print("🚀 StudyPulse AI - Student Productivity & Study Planner")
    print("🌐 Running from project root...")
    print(f"🔗 Access the application at: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
    print(f"⚙️ Mode: {'Debug' if debug else 'Production (Standard)'}")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
