"""
PSA Tool - Main Flask Application
Entry point for the PSA Processing Server
"""

from flask import Flask, send_from_directory
try:
    from flask_cors import CORS
except ImportError:
    # If flask-cors not installed, create a dummy CORS function
    def CORS(app):
        pass

from routes.system import system_bp
from routes.files import files_bp
from routes.process import process_bp
from routes.library import library_bp
from routes.analytics import bp as analytics_bp
from routes.disciplines import bp as disciplines_bp
from routes.learning import learning_bp

app = Flask(__name__)
CORS(app)  # Enable CORS for Next.js frontend

# Serve VOFC Viewer HTML file
@app.route('/viewer')
@app.route('/viewer/')
def viewer_index():
    """Serve the VOFC Library Viewer"""
    import os
    viewer_path = r'C:\Tools\Ollama\viewer'
    return send_from_directory(viewer_path, 'index.html')

# Register all blueprints
app.register_blueprint(system_bp)
app.register_blueprint(files_bp)
app.register_blueprint(process_bp)
app.register_blueprint(library_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(disciplines_bp)
app.register_blueprint(learning_bp)

# Start background queue worker
from services.queue_manager import start_worker
start_worker()

# Start approval monitor (syncs approved submissions with learning_events)
from services.approval_sync import start_approval_monitor
start_approval_monitor(interval_minutes=5)

# Start realtime approval listener (instant updates via Supabase Realtime)
from services.approval_realtime import start_realtime_approval_listener
start_realtime_approval_listener()

# Start analytics collector (aggregates metrics for dashboard)
from services.analytics_collector import start_collector
start_collector(interval_minutes=10)

# Start learning monitor (processes learning events and adjusts heuristics)
from services.learning_engine import start_learning_monitor
start_learning_monitor(interval_minutes=60)

if __name__ == "__main__":
    import os
    port = int(os.getenv('FLASK_PORT', '8080'))
    debug = os.getenv('FLASK_ENV', 'production') != 'production'
    
    print("=" * 50)
    print("Starting PSA Tool Flask Server")
    print("=" * 50)
    print(f"Port: {port}")
    print(f"Debug mode: {debug}")
    print("Note: Ollama and Tunnel are managed by NSSM services")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)

