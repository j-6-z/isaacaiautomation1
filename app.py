from flask import Flask, request, jsonify
import paypalrestsdk
import os
from dotenv import load_dotenv
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for client-side requests

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure PayPal SDK with Sandbox credentials
try:
    paypalrestsdk.configure({
        "mode": "sandbox",
        "client_id": os.getenv("PAYPAL_CLIENT_ID", "Aekwyfll3MQb7o-g9o1Z5BrlEB6eXiT3j4Km5FjkWMVHtEXhKLQxAMRuC9Mf9PuUT1WtuL5GC_zdCFgC"),
        "client_secret": os.getenv("PAYPAL_CLIENT_SECRET", "YOUR_CLIENT_SECRET")  # Replace with your actual secret
    })
    logger.info("PayPal SDK configured successfully")
except Exception as e:
    logger.error(f"Failed to configure PayPal SDK: {str(e)}")

# Define plan IDs from PayPal dashboard
PLAN_IDS = {
    "basic-subscription": "P-XXXXXXXXXXXXXXXXXXXX",  # Replace with actual PayPal plan IDs
    "mid-tier-subscription": "P-XXXXXXXXXXXXXXXXXXXX",
    "premium-subscription": "P-XXXXXXXXXXXXXXXXXXXX"
}

ONE_TIME_PLANS = {
    "basic-purchase": {"amount": 799, "description": "Basic One-Time Purchase"},
    "standard-purchase": {"amount": 11999, "description": "Standard One-Time Purchase"},
    "enterprise-purchase": {"amount": 25000, "description": "Enterprise One-Time Purchase"}
}

@app.route('/create_payment', methods=['POST'])
def create_payment():
    try:
        data = request.get_json()
        logger.debug(f"Received /create_payment request data: {data}")
        plan = data.get('plan')
        account_type = data.get('account_type')
        form_data = data.get('form_data')

        # Basic form validation
        if not plan or not account_type or not form_data:
            logger.error("Missing required fields: plan, account_type, or form_data")
            return jsonify({"error": "Missing required fields"}), 400

        if account_type == 'personal':
            if not form_data.get('name') or not form_data.get('email'):
                logger.error("Missing required personal fields: name or email")
                return jsonify({"error": "Missing required personal fields"}), 400
            if form_data.get('email') != form_data.get('verifyEmail'):
                logger.error("Emails do not match")
                return jsonify({"error": "Emails do not match"}), 400
        elif account_type == 'business':
            if not form_data.get('companyName') or not form_data.get('businessEmail'):
                logger.error("Missing required business fields: companyName or businessEmail")
                return jsonify({"error": "Missing required business fields"}), 400
            if form_data.get('businessEmail') != form_data.get('businessVerifyEmail'):
                logger.error("Business emails do not match")
                return jsonify({"error": "Business emails do not match"}), 400
        else:
            logger.error(f"Invalid account_type: {account_type}")
            return jsonify({"error": "Invalid account type"}), 400

        # Handle subscription
        if plan in PLAN_IDS:
            logger.debug(f"Creating subscription for plan: {plan}")
            payment = paypalrestsdk.BillingAgreement({
                "name": f"JAYISAAC AI {plan.replace('-', ' ').title()}",
                "description": f"Subscription for {plan.replace('-', ' ').title()}",
                "start_date": "2025-09-19T00:00:00Z",
                "plan": {"id": PLAN_IDS[plan]},
                "payer": {"payment_method": "paypal"}
            })

            if payment.create():
                logger.debug(f"Subscription created successfully: {payment.id}")
                for link in payment.links:
                    if link.rel == "approval_url":
                        logger.debug(f"Approval URL: {link.href}")
                        return jsonify({"approval_url": link.href})
            logger.error(f"Failed to create subscription: {payment.error}")
            return jsonify({"error": "Failed to create subscription", "details": str(payment.error)}), 500

        # Handle one-time purchase
        elif plan in ONE_TIME_PLANS:
            logger.debug(f"Creating one-time payment for plan: {plan}")
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "transactions": [{
                    "amount": {
                        "total": f"{ONE_TIME_PLANS[plan]['amount']:.2f}",
                        "currency": "CAD"
                    },
                    "description": ONE_TIME_PLANS[plan]['description']
                }],
                "redirect_urls": {
                    "return_url": "http://localhost:5000/success",
                    "cancel_url": "http://localhost:5000/cancel"
                }
            })

            if payment.create():
                logger.debug(f"Payment created successfully, order_id: {payment.id}")
                return jsonify({"order_id": payment.id})
            logger.error(f"Failed to create payment: {payment.error}")
            return jsonify({"error": "Failed to create payment", "details": str(payment.error)}), 500

        logger.error(f"Invalid plan selected: {plan}")
        return jsonify({"error": "Invalid plan selected"}), 400

    except Exception as e:
        logger.error(f"Error in create_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/execute_payment', methods=['POST'])
def execute_payment():
    try:
        data = request.get_json()
        logger.debug(f"Received /execute_payment request data: {data}")
        payment_id = data.get('payment_id')
        payer_id = data.get('payer_id')

        if not payment_id or not payer_id:
            logger.error("Missing payment_id or payer_id")
            return jsonify({"error": "Missing payment_id or payer_id"}), 400

        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            logger.debug(f"Payment executed successfully: {payment_id}")
            return jsonify({"status": "success", "payment_id": payment_id})
        logger.error(f"Payment execution failed: {payment.error}")
        return jsonify({"error": "Payment execution failed", "details": str(payment.error)}), 500

    except Exception as e:
        logger.error(f"Error in execute_payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/success')
def success():
    logger.debug("Success endpoint reached")
    return jsonify({"message": "Payment completed successfully"})

@app.route('/cancel')
def cancel():
    logger.debug("Cancel endpoint reached")
    return jsonify({"message": "Payment cancelled"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)