const Stripe = require('stripe');
const dotenv = require('dotenv');

dotenv.config();
const stripe = Stripe(process.env.STRIPE_SECRET_KEY);

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const { plan, account_type, form_data } = req.body;

  const plans = {
    'basic-purchase': { amount: 79900, description: 'Basic One-Time Purchase' },
    'standard-purchase': { amount: 1199900, description: 'Standard One-Time Purchase' },
    'enterprise-purchase': { amount: 2500000, description: 'Enterprise One-Time Purchase' }
  };

  if (!plans[plan]) {
    res.status(400).json({ error: 'Invalid plan selected' });
    return;
  }

  try {
    const customerData = {
      email: account_type === 'personal' ? form_data.email : form_data.businessEmail,
      name: account_type === 'personal' ? form_data.name : form_data.companyName,
      metadata: {
        website_url: account_type === 'personal' ? form_data.websiteUrl || '' : form_data.businessWebsiteUrl || ''
      }
    };

    const customer = await stripe.customers.create(customerData);

    const paymentIntent = await stripe.paymentIntents.create({
      amount: plans[plan].amount,
      currency: 'cad',
      customer: customer.id,
      description: plans[plan].description,
      payment_method_types: ['card']
    });

    res.status(200).json({ clientSecret: paymentIntent.client_secret });
  } catch (error) {
    console.error('Error creating payment intent:', error);
    res.status(500).json({ error: error.message });
  }
};