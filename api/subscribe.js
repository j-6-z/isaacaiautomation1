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
    'basic-monthly': { priceId: 'price_1S94dt40fBt8mCex_basic_monthly' },
    'standard-monthly': { priceId: 'price_1S94dt40fBt8mCex_standard_monthly' },
    'enterprise-monthly': { priceId: 'price_1S94dt40fBt8mCex_enterprise_monthly' }
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

    let customer = await stripe.customers.create(customerData);

    const subscription = await stripe.subscriptions.create({
      customer: customer.id,
      items: [{ price: plans[plan].priceId }],
      payment_behavior: 'default_incomplete',
      expand: ['latest_invoice.payment_intent']
    });

    const clientSecret = subscription.latest_invoice.payment_intent.client_secret;

    res.status(200).json({ clientSecret });
  } catch (error) {
    console.error('Error creating subscription:', error);
    res.status(500).json({ error: error.message });
  }
};