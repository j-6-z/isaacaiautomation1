from flask import Flask, request, jsonify, redirect, render_template_string
import paypalrestsdk
import logging
import os

app = Flask(__name__)

# Configure PayPal SDK (Sandbox mode)
paypalrestsdk.configure({
    "mode": "sandbox",
    "client_id": "Aekwyfll3MQb7o-g9o1Z5BrlEB6eXiT3j4Km5FjkWMVHtEXhKLQxAMRuC9Mf9PuUT1WtuL5GC_zdCFgC",
    "client_secret": "EJJsSBmFUFn3usBfaNvKeFPkJXrUgnicCGqgszNVyhpPvjYaIWF-0UBO6aEFhQOkYqWfNgGW49BF-MNI"
})

# Configure logging
logging.basicConfig(level=logging.INFO)

# Plan IDs from PayPal Developer Dashboard
PLAN_IDS = {
    "basic-subscription": "P-XXXXXXXXXXXXXXX",  # Replace with your Basic Plan ID
    "mid-tier-subscription": "P-XXXXXXXXXXXXXXX",  # Replace with your Mid Plan ID
    "premium-subscription": "P-XXXXXXXXXXXXXXX"  # Replace with your Premium Plan ID
}

# Plan details for one-time purchases
ONE_TIME_PLANS = {
    "basic-purchase": {"amount": 7.99, "description": "Basic One-Time Purchase"},
    "standard-purchase": {"amount": 119.99, "description": "Standard One-Time Purchase"},
    "enterprise-purchase": {"amount": 250.00, "description": "Enterprise One-Time Purchase"}
}

@app.route('/')
def serve_html():
    try:
        with open('index.html', 'r') as file:
            html_content = file.read()
        return render_template_string(html_content)
    except Exception as e:
        logging.error(f"Error serving index.html: {str(e)}")
        return jsonify({"error": "Failed to load index.html"}), 500

@app.route('/create_payment', methods=['POST'])
def create_payment():
    data = request.json
    plan = data.get('plan')
    account_type = data.get('account_type')
    form_data = data.get('form_data')
    logging.info(f"Creating payment for plan: {plan}, account type: {account_type}, form_data: {form_data}")

    try:
        if plan in PLAN_IDS:  # Subscription
            billing_agreement = paypalrestsdk.BillingAgreement({
                "name": ONE_TIME_PLANS.get(plan, {}).get("description", plan),
                "description": f"Subscription for {plan}",
                "start_date": "2025-09-17T00:00:00Z",
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
                return jsonify({"error": str(billing_agreement.error)}), 500

        elif plan in ONE_TIME_PLANS:  # One-time payment
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": "isaacaiautomation1-git-main-jay-turners-projects-16621d09.vercel.app",  # Replace with your Vercel URL
                    "cancel_url": "https://your-vercel-url.vercel.app/cancel_payment"
                },
                "transactions": [{
                    "amount": {
                        "total": f"{ONE_TIME_PLANS[plan]['amount']:.2f}",
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
                return jsonify({"error": str(payment.error)}), 500

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
            return jsonify({"error": str(payment.error)}), 500
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
        webhook_id = "63464273GK1192151"  # Replace with your PayPal webhook ID
        if paypalrestsdk.Webhook.verify(
            request.headers.get('PAYPAL-TRANSMISSION-ID'),
            request.headers.get('PAYPAL-TRANSMISSION-TIME'),
            webhook_id,
            request.get_data()
        ):
            event_type = webhook_data.get('event_type')
            if event_type == 'PAYMENT.SALE.COMPLETED':
                logging.info("Payment sale completed")
                # Add database or logging logic here (file I/O disabled on Vercel)
            elif event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
                logging.info("Subscription activated")
                # Add database or logging logic here
            return jsonify({"status": "success"}), 200
        else:
            logging.error("Webhook verification failed")
            return jsonify({"error": "Webhook verification failed"}), 400
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500