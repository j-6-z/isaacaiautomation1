// index.js - Optional shared utils
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

module.exports = { stripe };  // Export for use in other files