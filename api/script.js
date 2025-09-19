// Stripe setup
const stripe = Stripe('pk_test_YOUR_PUBLISHABLE_KEY');  // Your public key here

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