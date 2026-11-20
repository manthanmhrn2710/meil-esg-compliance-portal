"""BRSR-Report launcher"""
from app.routes import api
from app.models import bootstrap_database
from app.config import APP_SECRET
from flask import Flask, send_from_directory
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_app():
    app = Flask(__name__, static_folder=None, template_folder=None)
    app.secret_key = APP_SECRET
    app.register_blueprint(api)
    fr = os.path.join(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))), "frontend")

    @app.route("/")
    def index():
        return send_from_directory(fr, "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        return send_from_directory(fr, path)

    with app.app_context():
        bootstrap_database()
    return app


def main():
    app = create_app()
    print()
    print("=" * 60)
    print("  BRSR-Report")
    print("=" * 60)
    print()
    print("  Server:  http://localhost:5000")
    print()
    print("  Demo accounts (password: brsr@2026)")
    print("    director@meil.com     - Group Admin")
    print("    infra.esg@meil.com    - Subsidiary Admin")
    print("    tunnel.lead@meil.com  - BU Reviewer")
    print("    metro.hse@meil.com    - Project Officer")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
