import firebase_admin
from firebase_admin import messaging
from .models import DeviceToken
import logging

logger = logging.getLogger(__name__)

def send_push_notification(user, title, body, data=None):
    """
    Sends a push notification to all devices registered for the given user.
    """
    if not user:
        return

    tokens = DeviceToken.objects.filter(user=user).values_list('token', flat=True)
    if not tokens:
        return

    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        android=messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                sound='default',
                channel_id='default',
            )
        ),
        data=data or {},
        tokens=list(tokens),
    )

    try:
        response = messaging.send_multicast(message)
        logger.info(f"Successfully sent {response.success_count} messages; {response.failure_count} failed.")
        
        # Optionally remove invalid tokens
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # e.g., 'messaging/invalid-registration-token' or 'messaging/registration-token-not-registered'
                    if resp.exception.code in ['messaging/invalid-registration-token', 'messaging/registration-token-not-registered']:
                        failed_tokens.append(tokens[idx])
            if failed_tokens:
                DeviceToken.objects.filter(token__in=failed_tokens).delete()
                logger.info(f"Removed {len(failed_tokens)} invalid device tokens.")

    except Exception as e:
        logger.error(f"Error sending push notification: {e}")
