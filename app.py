from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os

app = Flask(__name__)

# Define allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:5500",  # Local development with Live Server
    "https://www.jayisaacai.com",  # Production domain
    "isaacaiautomation1-k20kqgdp3-jay-turners-projects-16621d09.vercel.app"  # Vercel deployment URL
]

# Configure CORS with specific origins
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

@app.route('/api/debug', methods=['GET'])
def debug():
    logger.debug("Debug endpoint accessed")
    return jsonify({"status": "running", "env": os.environ.get('FLASK_ENV', 'unknown')}), 200

@app.route('/api/success')
def success():
    logger.debug("Serving /success")
    return jsonify({"message": "Payment completed successfully"})

@app.route('/api/cancel')
def cancel():
    logger.debug("Serving /cancel")
    return jsonify({"message": "Payment cancelled"})

@app.route('/api')
def hello():
    logger.debug("Serving /api")
    return jsonify({"message": "Hello from Flask on Vercel!"})

# Vercel handles serverless execution; no app.run() needed