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
    "basic-subscription": "P-6VF10848V2487410NNDE3Y5A",  # Replace with your Basic Plan ID
    "mid-tier-subscription": "P-24M92406D46068305NDE3ZOI",  # Replace with your Mid Plan ID
    "premium-subscription": "P-7S597632MR070600RNDE327Q"  # Replace with your Premium Plan ID
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
                    "return_url": "https://isaacaiautomation1-git-main-jay-turners-projects-16621d09.vercel.app/execute_payment",
                    "cancel_url": "https://isaacaiautomation1-git-main-jay-turners-projects-16621d09.vercel.app/cancel_payment"
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
            plan_description = payment.transactions[0].description if payment.transactions else "Unknown Plan"
            amount = payment.transactions[0].amount.total if payment.transactions else "0.00"
            return redirect(f"/receipt?payment_id={payment_id}&plan={plan_description}&amount={amount}")
        else:
            logging.error(f"Payment execution failed: {payment.error}")
            return jsonify({"error": str(payment.error)}), 500
    except Exception as e:
        logging.error(f"Error executing payment: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/receipt')
def receipt():
    payment_id = request.args.get('payment_id', 'N/A')
    plan = request.args.get('plan', 'Unknown Plan')
    amount = request.args.get('amount', '0.00')
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Receipt - JAYISAAC AI Automation</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;600&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                font-family: 'Roboto', sans-serif;
            }
            body {
                background: #f8f9fa;
                color: #2B2D42;
                line-height: 1.8;
                scroll-behavior: smooth;
                overflow-x: hidden;
                position: relative;
                padding: 30px;
            }
            header {
                background: #ffffff;
                position: fixed;
                width: 100%;
                top: 0;
                z-index: 1000;
                padding: 1.5rem 2rem;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                animation: slideIn 0.7s ease-out;
            }
            @keyframes slideIn {
                from { transform: translateY(-50%); }
                to { transform: translateY(0); }
            }
            nav {
                display: flex;
                justify-content: space-between;
                align-items: center;
                max-width: 1400px;
                margin: 0 auto;
            }
            .logo {
                display: flex;
                align-items: center;
                gap: 1rem;
            }
            .logo img {
                height: 60px;
                filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
                transition: transform 0.3s ease;
            }
            .logo img:hover {
                transform: scale(1.1);
            }
            .logo span {
                font-size: 1.8rem;
                font-weight: 500;
                color: #2B2D42;
                text-transform: none;
                letter-spacing: 1px;
                text-shadow: none;
            }
            nav ul {
                display: flex;
                gap: 2rem;
                list-style: none;
            }
            nav a {
                color: #2B2D42;
                text-decoration: none;
                font-size: 1.2rem;
                font-weight: 500;
                padding: 0.5rem 1.5rem;
                border-radius: 25px;
                transition: all 0.3s ease;
                background: linear-gradient(90deg, transparent, rgba(43, 45, 66, 0.1));
                background-size: 200%;
                background-position: left;
            }
            nav a:hover {
                background-position: right;
                color: #4B5EFA;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
            .receipt-container {
                background: #ffffff;
                padding: 3rem;
                border-radius: 25px;
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.05);
                width: 100%;
                max-width: 1200px;
                text-align: center;
                margin: 10rem auto;
            }
            h1 {
                font-size: 2.8rem;
                font-weight: 500;
                color: #2B2D42;
                margin-bottom: 2rem;
                text-transform: none;
                letter-spacing: 1px;
                text-shadow: none;
            }
            p {
                font-size: 1.2rem;
                color: #555555;
                margin-bottom: 1.5rem;
            }
            .receipt-details {
                font-size: 1.2rem;
                color: #2B2D42;
                margin-bottom: 1rem;
            }
            .home-button {
                display: inline-block;
                background: #4B5EFA;
                color: #ffffff;
                padding: 1rem 2rem;
                border-radius: 25px;
                text-decoration: none;
                font-size: 1.2rem;
                font-weight: 500;
                transition: all 0.3s ease;
                margin-top: 2rem;
            }
            .home-button:hover {
                background: #3b4cca;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            }
            @media (max-width: 768px) {
                .receipt-container {
                    padding: 2rem;
                    margin: 8rem auto;
                    max-width: 95%;
                }
                h1 {
                    font-size: 2.2rem;
                }
                p, .receipt-details {
                    font-size: 1rem;
                }
                .home-button {
                    font-size: 1rem;
                    padding: 0.8rem 1.5rem;
                }
                nav ul {
                    gap: 1.5rem;
                }
                nav a {
                    font-size: 1rem;
                    padding: 0.5rem 1rem;
                }
                .logo span {
                    font-size: 1.5rem;
                }
            }
        </style>
    </head>
    <body>
        <header>
            <nav>
                <div class="logo">
                    <img src="images/chtabot lololol.jpg" alt="AI Chatbot Logo">
                    <span>JAYISAAC AI Automation</span>
                </div>
                <ul>
                    <li><a href="/index.html">Home</a></li>
                </ul>
            </nav>
        </header>
        <div class="receipt-container">
            <h1>Thank You for Your Purchase!</h1>
            <p>An email will be sent shortly with your purchase details.</p>
            <div class="receipt-details">Payment ID: {{ payment_id }}</div>
            <div class="receipt-details">Plan: {{ plan }}</div>
            <div class="receipt-details">Amount: CAD ${{ amount }}</div>
            <a href="/index.html" class="home-button">Return to Home</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content, payment_id=payment_id, plan=plan, amount=amount)

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

if __name__ == '__main__':
    app.run(debug=True)