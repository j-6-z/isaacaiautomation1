const express = require('express');
const app = express();

app.get('/api', async (req, res) => {
  try {
    res.json({ message: 'API is working' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = app;