const https = require('https');

// Replace this with your actual Render URL
const URL = 'https://code-alpha-aetheria.onrender.com/'; 
const INTERVAL = 10 * 60 * 1000; // 10 minutes in milliseconds

console.log(`Starting keep-awake script for ${URL}...`);

setInterval(() => {
    https.get(URL, (res) => {
        console.log(`[${new Date().toISOString()}] Pinged ${URL}. Status Code: ${res.statusCode}`);
    }).on('error', (err) => {
        console.error(`[${new Date().toISOString()}] Error pinging server:`, err.message);
    });
}, INTERVAL);
