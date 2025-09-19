from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import requests
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all origins

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# PayPal Sandbox Credentials (use env vars in production)
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID', 'Aekwyfll3MQb7o-g9o1Z5BrlEB6eXiT3j4Km5FjkWMVHtEXhKLQxAMRuC9Mf9PuUT1WtuL5GC_zdCFgC')
PAYPAL_CLIENT_SECRET = os.environ.get('PAYPAL_CLIENT_SECRET', 'EJJsSBmFUFn3usBfaNvKeFPkJXrUgnicCGqgszNVyhpPvjYaIWF-0UBO6aEFhQOkYqWfNgGW49BF-MNI')

# One-time purchase plans (amounts in cents)
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
        raise ValueError("PayPal credentials missing")
    data = {"grant_type": "client_credentials"}
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    try:
        response = requests.post(url, auth=auth, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        token = response.json()["access_token"]
        logger.debug("Access token retrieved successfully")
        return token
    except requests.RequestException as e:
        logger.error(f"Token fetch failed: {str(e)} - Response: {response.text if 'response' in locals() else 'N/A'}")
        raise

@app.route('/debug', methods=['GET'])
def debug():
    logger.debug("Debug endpoint accessed")
    return jsonify({"status": "running", "env": os.environ.get('FLASK_ENV', 'unknown')}), 200

@app.route('/create_payment', methods=['POST'])
def create_payment():
    try:
        data = request.get_json(silent=True)
        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "No JSON data provided"}), 400

        plan = data.get('plan')
        account_type = data.get('account_type')
        form_data = data.get('form_data')
        
        if not plan or not account_type or not form_data:
            logger.error(f"Missing fields - plan: {plan}, account_type: {account_type}, form_data: {form_data}")
            return jsonify({"error": "Missing required fields"}), 400

        # Validation (personal/business)
        if account_type == 'personal':
            if not form_data.get('name') or not form_data.get('email'):
                return jsonify({"error": "Missing personal fields"}), 400
            if form_data.get('email') != form_data.get('verifyEmail'):
                return jsonify({"error": "Emails do not match"}), 400
        elif account_type == 'business':
            if not form_data.get('companyName') or not form_data.get('businessEmail'):
                return jsonify({"error": "Missing business fields"}), 400
            if form_data.get('businessEmail') != form_data.get('businessVerifyEmail'):
                return jsonify({"error": "Business emails do not match"}), 400
        else:
            return jsonify({"error": "Invalid account type"}), 400

        if plan not in ONE_TIME_PLANS:
            return jsonify({"error": "Invalid plan selected"}), 400

        logger.debug(f"Creating order for plan: {plan}")
        token = get_paypal_access_token()
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
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            order = response.json()
            logger.debug(f"Order created: {order['id']}")
            return jsonify({"order_id": order["id"]}), 200
        except requests.RequestException as e:
            logger.error(f"Order creation failed: {str(e)}")
            return jsonify({"error": "Failed to create payment", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Error in create_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/execute_payment', methods=['POST'])
def execute_payment():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        order_id = data.get('payment_id')
        payer_id = data.get('payer_id')
        if not order_id or not payer_id:
            return jsonify({"error": "Missing payment_id or payer_id"}), 400

        token = get_paypal_access_token()
        url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        try:
            response = requests.post(url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.debug(f"Order captured: {order_id}")
            return jsonify({"status": "success", "payment_id": order_id}), 200
        except requests.RequestException as e:
            logger.error(f"Order capture failed: {str(e)}")
            return jsonify({"error": "Payment execution failed", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Error in execute_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/success')
def success():
    return jsonify({"message": "Payment completed successfully"})

@app.route('/cancel')
def cancel():
    return jsonify({"message": "Payment cancelled"})

@app.route('/Purchasepage.html')
def serve_purchase():
    if not os.path.exists('Purchasepage.html'):
        return jsonify({"error": "Purchasepage.html not found"}), 404
    return send_from_directory('.', 'Purchasepage.html')

@app.route('/')
def serve_root():
    return send_from_directory('.', 'index.html')  # Serves landing page at root

if __name__ == '__main__':
    app.run(debug=True, port=5000)