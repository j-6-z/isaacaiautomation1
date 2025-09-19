```python
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

# Set Stripe API key from environment variable
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
if not stripe.api_key:
    logger.error("Missing STRIPE_SECRET_KEY environment variable")
    raise ValueError("STRIPE_SECRET_KEY environment variable is not set")

# Map plan names to Stripe Price IDs (replace with actual Price IDs from Stripe Dashboard)
PLAN_PRICE_IDS = {
    'basic-monthly': 'price_basic_monthly',  # Replace with actual Price ID (e.g., price_123...)
    'standard-monthly': 'price_standard_monthly',
    'enterprise-monthly': 'price_enterprise_monthly'
}

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

        # Validate plan and amount
        valid_plans = {
            'basic-monthly': 4900,
            'standard-monthly': 14900,
            'enterprise-monthly': 49900,
            'basic-purchase': 79900,
            'standard-purchase': 999900,
            'enterprise-purchase': 2500000
        }
        if plan not in valid_plans or valid_plans[plan] != amount:
            logger.error("Invalid plan or amount - plan: %s, amount: %s", plan, amount)
            return jsonify({"error": "Invalid plan or amount"}), 400

        try:
            # Extract email from form data
            email = form_data.get('email') if form_data.get('accountType') == 'personal' else form_data.get('businessEmail')

            if is_subscription:
                if plan not in PLAN_PRICE_IDS:
                    logger.error("No Price ID for plan: %s", plan)
                    return jsonify({"error": f"No Price ID configured for plan {plan}"}), 400

                # Create customer
                customer = stripe.Customer.create(
                    email=email,
                    source=stripe_token
                )
                # Create subscription
                subscription = stripe.Subscription.create(
                    customer=customer.id,
                    items=[{'price': PLAN_PRICE_IDS[plan]}],
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
        except stripe.error.AuthenticationError as e:
            logger.error("Stripe authentication error: %s", str(e))
            return jsonify({"error": "Server configuration error: Invalid Stripe API key"}), 401
        except stripe.error.InvalidRequestError as e:
            logger.error("Stripe invalid request: %s", str(e))
            return jsonify({"error": f"Payment failed: {str(e)}"}), 400
        except stripe.error.CardError as e:
            logger.error("Stripe card error: %s", str(e))
            return jsonify({"error": f"Payment declined: {str(e)}"}), 402
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