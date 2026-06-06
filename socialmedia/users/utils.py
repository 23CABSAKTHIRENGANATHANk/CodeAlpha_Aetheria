import firebase_admin
from firebase_admin import messaging
from .models import DeviceToken
import logging

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None, badge=None):
    """
    Sends a push notification to all devices registered for the given user.
    """
    if not user:
        return

    tokens = DeviceToken.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        return

    # Configure Android notification
    android_notification = messaging.AndroidNotification(
        sound='default',
        channel_id='aetheria_high_importance',
    )
    if badge is not None:
        android_notification.notification_count = int(badge)

    # Configure APNS payload (for iOS devices)
    aps_kwargs = {'sound': 'default'}
    if badge is not None:
        aps_kwargs['badge'] = int(badge)
    
    apns_payload = messaging.ApnsPayload(
        aps=messaging.Aps(**aps_kwargs)
    )

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        android=messaging.AndroidConfig(
            priority='high',
            notification=android_notification,
        ),
        apns=messaging.ApnsConfig(
            payload=apns_payload
        ),
        data=data or {},
        tokens=list(tokens),
    )

    try:
        response = messaging.send_multicast(message)
        logger.info(f"Successfully sent {response.success_count} messages; {response.failure_count} failed.")
        
        # Remove invalid tokens
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    if resp.exception.code in ['messaging/invalid-registration-token', 'messaging/registration-token-not-registered']:
                        failed_tokens.append(tokens[idx])
            if failed_tokens:
                DeviceToken.objects.filter(token__in=failed_tokens).delete()
                logger.info(f"Removed {len(failed_tokens)} invalid device tokens.")

    except Exception as e:
        logger.error(f"Error sending push notification: {e}")

# ──────────────────────────────────────────────
# Google Gemini API client helper
# ──────────────────────────────────────────────
def call_gemini_api(prompt):
    import os
    import requests
    import json
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        
    return None
