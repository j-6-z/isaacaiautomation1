// Stripe setup
const stripe = Stripe('pk_live_51S94dl3jvJSv2v9HnjZKuzoec68rIbBFULBh0ihi1kg5yRPq92JCv4xFT5MFJNwLCfKuBWqcI19xakCggReg9Y2F00vG2bvqk9');  // Your public key here

// Example: On button click (add <button id="pay-button">Pay $20</button> to HTML)
document.getElementById('pay-button').addEventListener('click', async () => {
  const response = await fetch('/api/stripe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ amount: 2000 })  // $20 in cents
  });
  const { clientSecret } = await response.json();

  const { error } = await stripe.confirmCardPayment(clientSecret, {
    payment_method: {
      card: { token: 'tok_visa' },  // Test token; in prod, use Elements
    }
  });

  if (error) {
    alert('Payment failed: ' + error.message);
  } else {
    alert('Payment succeeded!');
  }
});