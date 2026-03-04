"""
CapitalOps API - Application Entry Point

Starts the Flask JSON API server on port 5000. This is the main entry point
for both development (python main.py) and the Replit workflow.

The create_app() factory in app/__init__.py handles all initialization
including database setup, blueprint registration, and demo data seeding.

This is the API-only backend (capitalops-api). The React frontend
(capitalops-web) communicates with this server via Bearer JWT tokens.
"""

from app import create_app

# Initialize the Flask application using the factory pattern
app = create_app()

if __name__ == "__main__":
    # Run the development server.
    # host="0.0.0.0" binds to all interfaces (required for Replit).
    # port=5000 is the standard Replit webview port.
    # debug=True enables auto-reload on code changes.
    app.run(host="0.0.0.0", port=5000, debug=True)
