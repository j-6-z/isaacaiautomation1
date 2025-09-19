from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import stripe

app = Flask(__name__)

# Define allowed origins
ALLOWED_ORIGINS = [
    "http://localhost:5500",
    "https://www.jayisaacai.com",
    "https://isaacaiautomation1-k20kqgdp3-jay-turners-projects-16621d09.vercel.app"
]

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

# Set Stripe API key (add to Vercel environment variables)
stripe.api_key = os.environ.get('sk_test_51S94dt40fBt8mCexAupOMzcDR1hOvIBnccrLZT57ZI8CB7fMwmcvNCDKA5kPv8B5L9MiNuEieP8O3OZnbFxz8aWc00M2leWPtK')
if not stripe.api_key:
    logger.error("Missing STRIPE_SECRET_KEY environment variable")

@app.route('/api/debug', methods=['GET'])
def debug():
    logger.debug("Debug endpoint accessed")
    return jsonify({"status": "running", "env": os.environ.get('FLASK_ENV', 'unknown')}), 200

@app.route('/api/validate_form', methods=['POST'])
def validate_form():
    try:
        data = request.get_json(silent=True)
        logger.debug("Received validate_form request data: %s", data)
        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "No JSON data provided"}), 400

        account_type = data.get('account_type')
        form_data = data.get('form_data')
        if not account_type or not form_data:
            logger.error("Missing fields - account_type: %s, form_data: %s", account_type, form_data)
            return jsonify({"error": "Missing required fields"}), 400

        if account_type == 'personal':
            if not form_data.get('name') or not form_data.get('email'):
                logger.error("Missing personal fields - name: %s, email: %s", form_data.get('name'), form_data.get('email'))
                return jsonify({"error": "Missing personal fields"}), 400
            if form_data.get('email') != form_data.get('verifyEmail'):
                logger.error("Emails do not match - email: %s, verifyEmail: %s", form_data.get('email'), form_data.get('verifyEmail'))
                return jsonify({"error": "Emails do not match"}), 400
        elif account_type == 'business':
            if not form_data.get('companyName') or not form_data.get('businessEmail'):
                logger.error("Missing business fields - companyName: %s, businessEmail: %s", form_data.get('companyName'), form_data.get('businessEmail'))
                return jsonify({"error": "Missing business fields"}), 400
            if form_data.get('businessEmail') != form_data.get('businessVerifyEmail'):
                logger.error("Business emails do not match - businessEmail: %s, businessVerifyEmail: %s", form_data.get('businessEmail'), form_data.get('businessVerifyEmail'))
                return jsonify({"error": "Business emails do not match"}), 400
        else:
            logger.error("Invalid account type: %s", account_type)
            return jsonify({"error": "Invalid account type"}), 400

        logger.debug("Form data validated successfully")
        return jsonify({"status": "valid"}), 200
    except Exception as e:
        logger.error("Unexpected error in validate_form: %s", str(e))
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500

@app.route('/api/process_payment', methods=['POST'])
def process_payment():
    try:
        data = request.get_json(silent=True)
        logger.debug("Received process_payment request data: %s", data)
        if not data:
            logger.error("No JSON data in request")
            return jsonify({"error": "No JSON data provided"}), 400

        plan = data.get('plan')
        plan_type = data.get('plan_type')
        amount = data.get('amount')
        is_subscription = data.get('is_subscription')
        stripe_token = data.get('stripe_token')
        form_data = data.get('form_data')

        if not all([plan, plan_type, amount, stripe_token, form_data]):
            logger.error("Missing fields - plan: %s, plan_type: %s, amount: %s, stripe_token: %s", plan, plan_type, amount, stripe_token)
            return jsonify({"error": "Missing required fields"}), 400

        if not stripe.api_key:
            logger.error("Stripe API key not configured")
            return jsonify({"error": "Server configuration error: Missing Stripe key"}), 500

        try:
            # Extract email from form data
            email = form_data.get('email') if form_data.get('accountType') == 'personal' else form_data.get('businessEmail')

            if is_subscription:
                # Create customer
                customer = stripe.Customer.create(
                    email=email,
                    source=stripe_token
                )
                # Create subscription (assumes plan ID like 'basic-monthly' is a recurring price in Stripe)
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': plan}],  # Use 'price' instead of 'plan' for modern Stripe API
                    billing_cycle_anchor=stripe.utils.utc_now(),
                    expand=['latest_invoice.payment_intent']
                )
                logger.debug("Subscription created: %s", subscription.id)
                return jsonify({"status": "success", "subscription_id": subscription.id}), 200
            else:
                # Create one-time charge
                charge = stripe.Charge.create(
                    amount=amount,
                    currency='cad',
                    source=stripe_token,
                    description=f"{plan} for {form_data.get('name') or form_data.get('companyName')}"
                )
                logger.debug("Charge created: %s", charge.id)
                return jsonify({"status": "success", "charge_id": charge.id}), 200
        except stripe.error.StripeError as e:
            logger.error("Stripe error: %s", str(e))
            return jsonify({"error": f"Payment failed: {str(e)}"}), 400
        except Exception as e:
            logger.error("Unexpected Stripe exception: %s", str(e))
            return jsonify({"error": f"Payment processing error: {str(e)}"}), 500
    except Exception as e:
        logger.error("Unexpected error in process_payment: %s", str(e))
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500

@app.route('/api/success')
def success():
    logger.debug("Serving /success")
    return jsonify({"message": "Payment completed successfully"})

@app.route('/api')
def hello():
    logger.debug("Serving /api")
    return jsonify({"message": "Hello from Flask on Vercel!"})

# Vercel handles serverless execution; no app.run() needed