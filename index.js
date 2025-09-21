const express = require('express');
const app = express();

// Middleware to parse JSON bodies (optional, include if you need to handle POST/PUT requests)
app.use(express.json());

// Define API route
app.get('/api', (req, res) => {
  res.json({ message: 'API is working' });
});

// Handle all other routes (optional, for better user experience)
app.get('*', (req, res) => {
  res.status(404).json({ message: 'Not Found' });
});

// Export for Vercel serverless
module.exports = app;