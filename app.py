from flask import Flask, request, jsonify, send_from_directory
import logging
import requests

app = Flask(__name__)

# Configure logging to debug issues
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Hardcoded PayPal Client ID and Secret (Replace with your actual PayPal sandbox credentials)
PAYPAL_CLIENT_ID = "Aekwyfll3MQb7o-g9o1Z5BrlEB6eXiT3j4Km5FjkWMVHtEXhKLQxAMRuC9Mf9PuUT1WtuL5GC_zdCFgC"  # Your provided PayPal Client ID
PAYPAL_CLIENT_SECRET = "EJJsSBmFUFn3usBfaNvKeFPkJXrUgnicCGqgszNVyhpPvjYaIWF-0UBO6aEFhQOkYqWfNgGW49BF-MNI"  # REPLACE WITH YOUR PAYPAL CLIENT SECRET

# Define one-time purchase plans
ONE_TIME_PLANS = {
    "basic-purchase": {"amount": 799, "description": "Basic One-Time Purchase"},
    "standard-purchase": {"amount": 11999, "description": "Standard One-Time Purchase"},
    "enterprise-purchase": {"amount": 25000, "description": "Enterprise One-Time Purchase"}
}

def get_paypal_access_token():
    """Fetch PayPal access token using client ID and secret."""
    logger.debug("Attempting to get PayPal access token")
    url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    auth = (PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    if not auth[0] or not auth[1] or auth[1] == "YOUR_PAYPAL_CLIENT_SECRET":
        logger.error("Invalid or missing PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET")
        raise ValueError("PayPal credentials invalid or missing")
    data = {"grant_type": "client_credentials"}
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    try:
        response = requests.post(url, auth=auth, data=data, headers=headers)
        response.raise_for_status()
        logger.debug("Successfully obtained PayPal access token")
        return response.json()["access_token"]
    except Exception as e:
        logger.error(f"Failed to get token: {str(e)} - Response: {response.text if 'response' in locals() else 'N/A'}")
        raise

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to verify server is running."""
    logger.debug("Test endpoint accessed")
    return jsonify({"status": "success", "message": "Server is running"}), 200

@app.route('/create_payment', methods=['POST'])
def create_payment():
    """Create a PayPal order for a one-time purchase."""
    try:
        data = request.get_json(silent=True)
        logger.debug(f"Received /create_payment request: {data}")
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({"error": "No JSON data provided"}), 400

        plan = data.get('plan')
        account_type = data.get('account_type')
        form_data = data.get('form_data')
        
        if not plan or not account_type or not form_data:
            logger.error(f"Missing required fields - plan: {plan}, account_type: {account_type}, form_data: {form_data}")
            return jsonify({"error": "Missing required fields"}), 400

        if account_type == 'personal':
            if not form_data.get('name') or not form_data.get('email'):
                logger.error("Missing required personal fields")
                return jsonify({"error": "Missing required personal fields"}), 400
            if form_data.get('email') != form_data.get('verifyEmail'):
                logger.error("Emails do not match")
                return jsonify({"error": "Emails do not match"}), 400
        elif account_type == 'business':
            if not form_data.get('companyName') or not form_data.get('businessEmail'):
                logger.error("Missing required business fields")
                return jsonify({"error": "Missing required business fields"}), 400
            if form_data.get('businessEmail') != form_data.get('businessVerifyEmail'):
                logger.error("Business emails do not match")
                return jsonify({"error": "Business emails do not match"}), 400
        else:
            logger.error(f"Invalid account type: {account_type}")
            return jsonify({"error": "Invalid account type"}), 400

        if plan in ONE_TIME_PLANS:
            logger.debug(f"Creating v2 Order for plan: {plan}")
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
                    "return_url": "https://www.jayisaacai.com/",
                    "cancel_url": "https://www.jayisaacai.com/"
                }
            }
            try:
                response = requests.post(url, headers=headers, json=body)
                response.raise_for_status()
                order = response.json()
                logger.debug(f"v2 Order created: {order['id']}")
                response_data = {"order_id": order["id"]}
                logger.debug(f"Sending response: {response_data}")
                return jsonify(response_data), 200
            except Exception as e:
                logger.error(f"Failed to create order: {str(e)} - Response: {response.text if 'response' in locals() else 'N/A'}")
                return jsonify({"error": "Failed to create payment", "details": str(e)}), 500
        logger.error(f"Invalid plan selected: {plan}")
        return jsonify({"error": "Invalid plan selected"}), 400
    except Exception as e:
        logger.error(f"Error in create_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/execute_payment', methods=['POST'])
def execute_payment():
    """Capture a PayPal order after approval."""
    try:
        data = request.get_json(silent=True)
        logger.debug(f"Received /execute_payment: {data}")
        if not data:
            logger.error("No JSON data received in request")
            return jsonify({"error": "No JSON data provided"}), 400

        order_id = data.get('payment_id')
        payer_id = data.get('payer_id')
        if not order_id or not payer_id:
            logger.error(f"Missing payment_id or payer_id - payment_id: {order_id}, payer_id: {payer_id}")
            return jsonify({"error": "Missing payment_id or payer_id"}), 400

        token = get_paypal_access_token()
        url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        try:
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            logger.debug(f"Order captured: {order_id}")
            response_data = {"status": "success", "payment_id": order_id}
            logger.debug(f"Sending response: {response_data}")
            return jsonify(response_data), 200
        except Exception as e:
            logger.error(f"Failed to capture order: {str(e)} - Response: {response.text if 'response' in locals() else 'N/A'}")
            return jsonify({"error": "Payment execution failed", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Error in execute_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/success')
def success():
    """Handle successful payment."""
    logger.debug("Serving /success endpoint")
    return jsonify({"message": "Payment completed successfully"})

@app.route('/cancel')
def cancel():
    """Handle cancelled payment."""
    logger.debug("Serving /cancel endpoint")
    return jsonify({"message": "Payment cancelled"})

@app.route('/')
def serve_purchase():
    """Serve the frontend Purchasepage.html."""
    logger.debug("Serving Purchasepage.html")
    return send_from_directory('.', 'Purchasepage.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)