"""
Minimal Flask App for Single-Pass VOFC Processing
"""

from flask import Flask
from routes.processing import processing_bp

app = Flask(__name__)
app.register_blueprint(processing_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

