const sharp = require('sharp');
const fs = require('fs');

async function generateSplash() {
    try {
        console.log('Generating splash screen...');
        await sharp('resources/icon.png')
            .resize({
                width: 2732,
                height: 2732,
                fit: 'contain',
                background: { r: 18, g: 18, b: 18, alpha: 1 } // Dark background matching the app
            })
            .toFile('resources/splash.png');
        console.log('Splash screen generated successfully.');
    } catch (error) {
        console.error('Error generating splash screen:', error);
    }
}

generateSplash();
