from flask import Flask, request, jsonify, redirect, render_template_string
import paypalrestsdk
from paypalrestsdk import BillingPlan, BillingAgreement, Webhook
import logging

app = Flask(__name__)

# Configure PayPal SDK (Sandbox mode)
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": "Aekwyfll3MQb7o-g9o1Z5BrlEB6eXiT3j4Km5FjkWMVHtEXhKLQxAMRuC9Mf9PuUT1WtuL5GC_zdCFgC",
    "client_secret": "EJJsSBmFUFn3usBfaNvKeFPkJXrUgnicCGqgszNVyhpPvjYaIWF-0UBO6aEFhQOkYqWfNgGW49BF-MNI"  # Replace with your app's Client Secret
})

# Configure logging
logging.basicConfig(level=logging.INFO)

# Plan IDs from PayPal Developer Dashboard (create these in Testing Tools > Sandbox > Billing Plans)
PLAN_IDS = {
    "basic-subscription": "YOUR_BASIC_PLAN_ID",  # e.g., P-123456789...
    "mid-tier-subscription": "YOUR_MID_PLAN_ID",
    "premium-subscription": "YOUR_PREMIUM_PLAN_ID"
}

# Plan details for one-time purchases
ONE_TIME_PLANS = {
    "basic-purchase": {"amount": 799, "description": "Basic One-Time Purchase"},
    "standard-purchase": {"amount": 11999, "description": "Standard One-Time Purchase"},
    "enterprise-purchase": {"amount": 25000, "description": "Enterprise One-Time Purchase"}
}

@app.route('/')
def serve_html():
    with open('index.html', 'r') as file:
        html_content = file.read()
    return render_template_string(html_content)

@app.route('/create_payment', methods=['POST'])
def create_payment():
    data = request.json
    plan = data.get('plan')
    account_type = data.get('account_type')
    form_data = data.get('form_data')

    logging.info(f"Creating payment for plan: {plan}, account type: {account_type}, form data: {form_data}")

    try:
        if plan in PLAN_IDS:  # Subscription
            billing_agreement = BillingAgreement({
                "name": ONE_TIME_PLANS.get(plan, {}).get("description", plan),
                "description": f"Subscription for {plan}",
                "start_date": "2025-09-16T00:00:00Z",
                "plan": {"id": PLAN_IDS[plan]},
                "payer": {"payment_method": "paypal"},
                "shipping_address": {
                    "line1": form_data.get('address', form_data.get('business-address', '')),
                    "city": form_data.get('city', form_data.get('business-city', '')),
                    "country_code": form_data.get('country', form_data.get('business-country', '')),
                    "postal_code": form_data.get('zip', form_data.get('business-zip', ''))
                }
            })

            if billing_agreement.create():
                for link in billing_agreement.links:
                    if link.rel == "approval_url":
                        return jsonify({"approval_url": link.href})
            else:
                logging.error(f"Billing agreement creation failed: {billing_agreement.error}")
                return jsonify({"error": billing_agreement.error}), 500

        elif plan in ONE_TIME_PLANS:  # One-time payment
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": "http://localhost:5000/execute_payment",
                    "cancel_url": "http://localhost:5000/cancel_payment"
                },
                "transactions": [{
                    "amount": {
                        "total": str(ONE_TIME_PLANS[plan]["amount"]),
                        "currency": "CAD"
                    },
                    "description": ONE_TIME_PLANS[plan]["description"]
                }]
            })

            if payment.create():
                for link in payment.links:
                    if link.rel == "approval_url":
                        return jsonify({"approval_url": link.href})
            else:
                logging.error(f"Payment creation failed: {payment.error}")
                return jsonify({"error": payment.error}), 500

        else:
            return jsonify({"error": "Invalid plan selected"}), 400

    except Exception as e:
        logging.error(f"Error creating payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/execute_payment', methods=['GET'])
def execute_payment():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        if payment.execute({"payer_id": payer_id}):
            logging.info(f"Payment {payment_id} executed successfully")
            return jsonify({"status": "success", "message": "Payment completed"})
        else:
            logging.error(f"Payment execution failed: {payment.error}")
            return jsonify({"error": payment.error}), 500
    except Exception as e:
        logging.error(f"Error executing payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cancel_payment')
def cancel_payment():
    return jsonify({"status": "cancelled", "message": "Payment cancelled"})

@app.route('/webhook', methods=['POST'])
def webhook():
    webhook_data = request.json
    logging.info(f"Webhook received: {webhook_data}")

    try:
        # Verify webhook (optional, requires webhook ID)
        webhook_id = "63464273GK1192151"  # Replace with your webhook ID
        if paypalrestsdk.Webhook.verify(request.headers.get('PAYPAL-TRANSMISSION-ID'), request.headers.get('PAYPAL-TRANSMISSION-TIME'), webhook_id, request.get_data()):
            event_type = webhook_data.get('event_type')
            if event_type == 'PAYMENT.SALE.COMPLETED':
                logging.info("Payment sale completed")
                # Update your database with payment details
            elif event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
                logging.info("Subscription activated")
                # Update your database with subscription details
            return jsonify({"status": "success"}), 200
        else:
            logging.error("Webhook verification failed")
            return jsonify({"error": "Webhook verification failed"}), 400
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)