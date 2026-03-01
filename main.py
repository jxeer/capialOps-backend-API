"""
CapitalOps - Application Entry Point

Starts the Flask web server on port 5000. This is the main entry point
for both development (python main.py) and the Replit workflow.

The create_app() factory in app/__init__.py handles all initialization
including database setup, blueprint registration, and demo data seeding.
"""

from app import create_app

# Initialize the Flask application using the factory pattern.
# This triggers database table creation and demo data seeding (in dev only).
app = create_app()

if __name__ == "__main__":
    # Run the development server.
    # host="0.0.0.0" binds to all interfaces (required for Replit).
    # port=5000 is the standard Replit webview port.
    # debug=True enables auto-reload on code changes and detailed error pages.
    app.run(host="0.0.0.0", port=5000, debug=True)
