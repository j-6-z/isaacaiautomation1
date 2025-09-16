from flask import Flask, request, render_template, jsonify
import json
from datetime import datetime
import hmac
import hashlib

app = Flask(__name__)

def generate_receipt(customer_name, customer_email, transaction_id, plan_name, plan_price):
    """
    Generate a receipt dictionary for a JAYISAAC AI Automation subscription purchase.
    
    Args:
        customer_name (str): Name of the customer
        customer_email (str): Email of the customer
        transaction_id (str): PayPal transaction ID
        plan_name (str): Name of the subscription plan
        plan_price (float): Price of the plan
    
    Returns:
        dict: Receipt data
    """
    receipt = {
        "company": {
            "name": "JAYISAAC AI Automation",
            "email": "support@jayisaac.ai",
            "logo": "images/chtabot lololol.jpg"
        },
        "customer": {
            "name": customer_name,
            "email": customer_email
        },
        "transaction": {
            "id": transaction_id,
            "date": datetime.now().strftime("%B %d, %Y"),
            "items": [
                {
                    "item": "Chatbot Subscription",
                    "description": plan_name,
                    "price": f"${plan_price:.2f}"
                }
            ],
            "total": f"${plan_price:.2f}"
        }
    }
    
    return receipt

def verify_paypal_webhook(payload, transmission_id, timestamp, webhook_id, cert_url, algorithm, signature):
    """
    Verify the PayPal webhook signature for security.
    This is a basic implementation; in production, use the full verification.
    
    Args:
        payload (str): Raw payload from the request
        transmission_id (str): PayPal-TRANSMISSION-ID header
        timestamp (str): PayPal-TIMESTAMP header
        webhook_id (str): Your webhook ID from PayPal Dashboard
        cert_url (str): PayPal-CERT-URL header (not used in basic HMAC)
        algorithm (str): PayPal-ALGORITHM header (should be 'sha256')
        signature (str): PayPal-SIGNATURE header
    
    Returns:
        bool: True if verified, False otherwise
    """
    # For basic verification using webhook ID as secret (PayPal recommends using cert for full verification)
    # In production, download the cert from cert_url and use it for asymmetric verification
    if algorithm != 'sha256':
        return False
    
    # Construct the transmission string
    transmission = f"{transmission_id}\n{timestamp}\n{webhook_id}\n{payload}"
    
    # Use webhook_id as the secret for HMAC-SHA256 (this is a simplified method; see PayPal docs for full)
    expected_signature = hmac.new(
        webhook_id.encode('utf-8'),
        transmission.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Check if the signature matches (PayPal sends multiple signatures separated by commas; take the first)
    received_signatures = signature.split(',')[0] if ',' in signature else signature
    return hmac.compare_digest(expected_signature, received_signatures)

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    PayPal webhook endpoint to handle events like payment completions.
    """
    # Get headers and raw payload
    transmission_id = request.headers.get('PayPal-Transmission-Id')
    timestamp = request.headers.get('PayPal-Timestamp')
    webhook_id = 'YOUR_WEBHOOK_ID_HERE'  # Replace with your actual webhook ID from PayPal Dashboard
    algorithm = request.headers.get('PayPal-Algorithm')
    signature = request.headers.get('PayPal-Signature')
    cert_url = request.headers.get('PayPal-Cert-Url')
    
    # Get raw payload for verification
    raw_payload = request.get_data(as_text=True)
    
    # Verify the webhook (basic HMAC; for full verification, implement cert-based)
    if not verify_paypal_webhook(raw_payload, transmission_id, timestamp, webhook_id, cert_url, algorithm, signature):
        return jsonify({'error': 'Webhook signature verification failed'}), 401
    
    # Parse the payload
    try:
        event_data = json.loads(raw_payload)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON payload'}), 400
    
    # Check if it's a relevant event (e.g., payment completed for subscription)
    event_type = event_data.get('event_type')
    if event_type == 'PAYMENT.SALE.COMPLETED':  # Or BILLING.SUBSCRIPTION.ACTIVATED, etc.
        # Extract data from the event (adapt based on PayPal event structure)
        transaction_id = event_data.get('resource', {}).get('id', 'Unknown ID')
        amount = event_data.get('resource', {}).get('amount', {}).get('total', 0.0)
        plan_name = event_data.get('resource', {}).get('description', 'Monthly Pro Plan')  # Adjust as needed
        # For customer info, you might need to look up from your DB or extract from event
        # Here, using placeholders; in real app, query your database using transaction_id
        customer_name = 'John Doe'  # Replace with actual lookup
        customer_email = event_data.get('resource', {}).get('payer', {}).get('payer_info', {}).get('email', 'example@example.com')
        
        # Generate receipt
        receipt_data = generate_receipt(customer_name, customer_email, transaction_id, plan_name, float(amount))
        
        # Save receipt to JSON (or send email, store in DB, etc.)
        with open(f'receipt_{transaction_id}.json', 'w') as f:
            json.dump(receipt_data, f, indent=4)
        
        print(f"Receipt generated for transaction {transaction_id}")
        # Optionally, render or send the receipt (e.g., email it)
        
    return jsonify({'status': 'OK'}), 200

@app.route('/receipt/<transaction_id>')
def show_receipt(transaction_id):
    """
    Route to display the receipt HTML with dynamic data.
    Loads from the generated JSON file.
    """
    try:
        with open(f'receipt_{transaction_id}.json', 'r') as f:
            receipt_data = json.load(f)
    except FileNotFoundError:
        return "Receipt not found", 404
    
    # Render the HTML template with data
    return render_template('receipt.html', receipt=receipt_data)

@app.route('/')
def home():
    """
    Home route - can redirect to receipt or show a form
    """
    return "JAYISAAC AI Automation - Receipt System Ready. Use /receipt/<id> to view."

if __name__ == '__main__':
    # Run the Flask app
    # Place receipt.html in a 'templates' folder
    app.run(debug=True, port=5000)