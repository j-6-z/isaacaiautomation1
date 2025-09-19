from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import requests
import os
import time

app = Flask(__name__)

# Define allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:5500",  # Local development with Live Server
    "https://www.jayisaacai.com",  # Production domain
    "isaacaiautomation1-k20kqgdp3-jay-turners-projects-16621d09.vercel.app"  # Vercel deployment URL (replace with your actual Vercel domain)
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

PAYPAL_CLIENT_ID = 'Aekwyfll3MQb7o-g9o1Z5BrlEB6eXiT3j4Km5FjkWMVHtEXhKLQxAMRuC9Mf9PuUT1WtuL5GC_zdCFgC'
PAYPAL_CLIENT_SECRET = 'EJJsSBmFUFn3usBfaNvKeFPkJXrUgnicCGqgszNVyhpPvjYaIWF-0UBO6aEFhQOkYqWfNgGW49BF-MNI'

ONE_TIME_PLANS = {
    "basic-purchase": {"amount": 79900, "description": "Basic One-Time Purchase"},
    "standard-purchase": {"amount": 1199900, "description": "Standard One-Time Purchase"},
    "enterprise-purchase": {"amount": 2500000, "description": "Enterprise One-Time Purchase"}
}

def get_paypal_access_token():
    logger.debug("Fetching PayPal access token")
    url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    auth = (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    if not auth[0] or not auth[1]:
        logger.error("Missing PayPal credentials")
        return jsonify({"error": "Missing PayPal credentials"}), 500
    data = {"grant_type": "client_credentials"}
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    for attempt in range(3):  # Retry up to 3 times
        try:
            response = requests.post(url, auth=auth, data=data, headers=headers, timeout=10)
            logger.debug("Token fetch attempt %d - Status: %d", attempt + 1, response.status_code)
            response.raise_for_status()
            token = response.json()["access_token"]
            logger.debug("Access token retrieved successfully: %s", token[:10] + "...")
            return token
        except requests.RequestException as e:
            logger.error("Token fetch attempt %d failed: %s - Response: %s", attempt + 1, str(e), response.text if 'response' in locals() else 'N/A')
            if attempt < 2:
                time.sleep(1)  # Wait before retrying
            else:
                return jsonify({"error": f"Token fetch failed after 3 attempts: {str(e)}", "details": response.text if 'response' in locals() else 'N/A'}), 500

@app.route('/api/debug', methods=['GET'])
def debug():
    logger.debug("Debug endpoint accessed")
    return jsonify({"status": "running", "env": os.environ.get('FLASK_ENV', 'unknown'), "client_id": PAYPAL_CLIENT_ID}), 200

@app.route('/api/create_payment', methods=['POST'])
def create_payment():
    try:
        data = request.get_json(silent=True)
        logger.debug("Received create_payment request data: %s", data)
        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "No JSON data provided"}), 400

        plan = data.get('plan')
        account_type = data.get('account_type')
        form_data = data.get('form_data', {})  # Default to empty dict

        logger.debug("Parsed fields - plan: %s, account_type: %s, form_data: %s", plan, account_type, form_data)
        if not plan or not account_type:
            logger.error("Missing fields - plan: %s, account_type: %s", plan, account_type)
            return jsonify({"error": "Missing required fields"}), 400

        if account_type not in ['personal', 'business']:
            logger.error("Invalid account type: %s", account_type)
            return jsonify({"error": "Invalid account type"}), 400

        if plan not in ONE_TIME_PLANS:
            logger.error("Invalid plan: %s", plan)
            return jsonify({"error": "Invalid plan selected"}), 400

        logger.debug("Creating order for plan: %s", plan)
        token = get_paypal_access_token()
        if isinstance(token, tuple):
            logger.error("Token fetch returned error: %s", token[0])
            return token
        url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        plan_details = ONE_TIME_PLANS[plan]
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "description": plan_details['description'],
                "amount": {
                    "currency_code": "CAD",
                    "value": f"{plan_details['amount'] / 100:.2f}"
                }
            }],
            "application_context": {
                "return_url": "https://www.jayisaacai.com/success",
                "cancel_url": "https://www.jayisaacai.com/cancel"
            }
        }
        logger.debug("Sending PayPal API request: %s", body)
        for attempt in range(3):  # Retry up to 3 times
            try:
                response = requests.post(url, headers=headers, json=body, timeout=10)
                logger.debug("Order creation attempt %d - Status: %d", attempt + 1, response.status_code)
                response.raise_for_status()
                order = response.json()
                logger.debug("Order created: %s", order['id'])
                return jsonify({"order_id": order["id"]}), 200
            except requests.RequestException as e:
                logger.error("Order creation attempt %d failed: %s - Response: %s", attempt + 1, str(e), response.text if 'response' in locals() else 'N/A')
                if attempt < 2:
                    time.sleep(1)  # Wait before retrying
                else:
                    return jsonify({"error": "Failed to create payment", "details": response.text if 'response' in locals() else str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error in create_payment: %s", str(e))
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500

@app.route('/api/execute_payment', methods=['POST'])
def execute_payment():
    try:
        data = request.get_json(silent=True)
        logger.debug("Execute payment request data: %s", data)
        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "No JSON data provided"}), 400

        order_id = data.get('payment_id')
        payer_id = data.get('payer_id')
        if not order_id or not payer_id:
            logger.error("Missing payment_id or payer_id - payment_id: %s, payer_id: %s", order_id, payer_id)
            return jsonify({"error": "Missing payment_id or payer_id"}), 400

        token = get_paypal_access_token()
        if isinstance(token, tuple):
            logger.error("Token fetch returned error: %s", token[0])
            return token
        url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        logger.debug("Sending PayPal capture request for order: %s", order_id)
        for attempt in range(3):  # Retry up to 3 times
            try:
                response = requests.post(url, headers=headers, timeout=10)
                logger.debug("Order capture attempt %d - Status: %d", attempt + 1, response.status_code)
                response.raise_for_status()
                logger.debug("Order captured: %s", order_id)
                return jsonify({"status": "success", "payment_id": order_id}), 200
            except requests.RequestException as e:
                logger.error("Order capture attempt %d failed: %s - Response: %s", attempt + 1, str(e), response.text if 'response' in locals() else 'N/A')
                if attempt < 2:
                    time.sleep(1)  # Wait before retrying
                else:
                    return jsonify({"error": "Payment execution failed", "details": response.text if 'response' in locals() else str(e)}), 500
    except Exception as e:
        logger.error("Unexpected error in execute_payment: %s", str(e))
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500

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