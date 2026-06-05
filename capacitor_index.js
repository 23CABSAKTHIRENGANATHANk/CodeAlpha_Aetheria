import { PushNotifications } from '@capacitor/push-notifications';

// Make it available globally so we can call it from main.js or HTML templates
window.PushNotifications = PushNotifications;

// Automatically initialize Push Notifications when the app starts
export async function initPushNotifications() {
    // We only want to run this on native devices (Android/iOS), not in the browser
    if (!window.Capacitor || !window.Capacitor.isNativePlatform()) {
        console.log('Push notifications not initialized (not on a native platform).');
        return;
    }

    try {
        let permStatus = await PushNotifications.checkPermissions();

        if (permStatus.receive === 'prompt') {
            permStatus = await PushNotifications.requestPermissions();
        }

        if (permStatus.receive !== 'granted') {
            console.error('User denied push notification permission.');
            return;
        }

        // Register with Apple / Google to receive push via APNS/FCM
        await PushNotifications.register();

        // Create high importance channel for Android 8.0+ to ensure heads-up popups and sound
        await PushNotifications.createChannel({
            id: 'default',
            name: 'Default Notifications',
            description: 'Important app notifications like messages and likes',
            importance: 5, // 5 = High importance (makes it pop up on screen)
            visibility: 1, // 1 = Public
            vibration: true,
            lights: true
        });

    } catch (e) {
        console.error('Error setting up push notifications:', e);
    }
}

window.initPushNotifications = initPushNotifications;

// Listeners
if (window.Capacitor && window.Capacitor.isNativePlatform()) {
    PushNotifications.addListener('registration', (token) => {
        console.log('Push registration success, token: ' + token.value);
        // We will send this token to our Django backend
        sendFCMTokenToServer(token.value);
    });

    PushNotifications.addListener('registrationError', (error) => {
        console.error('Error on registration: ' + JSON.stringify(error));
    });

    PushNotifications.addListener('pushNotificationReceived', (notification) => {
        console.log('Push received: ' + JSON.stringify(notification));
        // We can show an in-app toast here if we want
    });

    PushNotifications.addListener('pushNotificationActionPerformed', (notification) => {
        console.log('Push action performed: ' + JSON.stringify(notification));
        // Handle tapping on the notification here
    });
}

function sendFCMTokenToServer(token) {
    // We need to fetch the CSRF token from the DOM (assuming Django)
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    
    fetch('/api/register_device_token/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ token: token })
    }).then(res => {
        if (res.ok) console.log('Successfully saved FCM token to backend.');
        else console.error('Failed to save FCM token.');
    }).catch(err => console.error('Network error saving FCM token:', err));
}
