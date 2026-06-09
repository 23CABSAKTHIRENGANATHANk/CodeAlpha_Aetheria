package com.aetheria.app;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

/**
 * Firebase Cloud Messaging Service for Aetheria
 * Handles incoming push notifications from Django backend
 */
public class MyFirebaseMessagingService extends FirebaseMessagingService {
    
    private static final String TAG = "AetheriaFCM";
    
    /**
     * Called when a message is received from Firebase
     */
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        Log.d(TAG, "Message received from: " + remoteMessage.getFrom());
        
        // Handle data payload
        if (remoteMessage.getData().size() > 0) {
            Log.d(TAG, "Message data payload: " + remoteMessage.getData());
            handleDataMessage(remoteMessage);
        }
        
        // Handle notification payload
        if (remoteMessage.getNotification() != null) {
            Log.d(TAG, "Message body: " + remoteMessage.getNotification().getBody());
            handleNotificationMessage(remoteMessage);
        }
    }
    
    /**
     * Called when device token is refreshed
     * Send the new token to the backend server
     */
    @Override
    public void onNewToken(String token) {
        Log.d(TAG, "Refreshed token: " + token);
        
        // Send token to backend
        sendTokenToServer(token);
    }
    
    /**
     * Handle data message from Firebase
     * Data messages are sent as key-value pairs
     */
    private void handleDataMessage(RemoteMessage remoteMessage) {
        String notificationType = remoteMessage.getData().get("type");
        String title = remoteMessage.getData().get("title");
        String message = remoteMessage.getData().get("message");
        String senderId = remoteMessage.getData().get("sender_id");
        String postId = remoteMessage.getData().get("post_id");
        
        Log.d(TAG, "Type: " + notificationType + ", Sender: " + senderId);
        
        // Determine notification channel based on type
        String channelId = NotificationChannels.CHANNEL_SOCIAL;
        if ("message".equals(notificationType)) {
            channelId = NotificationChannels.CHANNEL_MESSAGES;
        } else if ("system".equals(notificationType)) {
            channelId = NotificationChannels.CHANNEL_SYSTEM;
        }
        
        // Show the notification
        showNotification(title, message, channelId, senderId, postId);
    }
    
    /**
     * Handle notification message from Firebase
     * Notification messages have title and body
     */
    private void handleNotificationMessage(RemoteMessage remoteMessage) {
        RemoteMessage.Notification notification = remoteMessage.getNotification();
        String title = notification.getTitle();
        String body = notification.getBody();
        
        showNotification(title, body, NotificationChannels.CHANNEL_SOCIAL, null, null);
    }
    
    /**
     * Display notification to user
     */
    private void showNotification(String title, String message, String channelId, 
                                   String senderId, String postId) {
        if (title == null || message == null) {
            Log.w(TAG, "Title or message is null, skipping notification");
            return;
        }
        
        // Create intent to open app when notification is tapped
        Intent intent = new Intent(this, MainActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
        
        if (senderId != null) {
            intent.putExtra("sender_id", senderId);
        }
        if (postId != null) {
            intent.putExtra("post_id", postId);
        }
        
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 
            (int) System.currentTimeMillis(), 
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        
        // Build notification
        NotificationCompat.Builder notificationBuilder =
            new NotificationCompat.Builder(this, channelId)
                .setSmallIcon(android.R.drawable.ic_dialog_info)  // Replace with app icon
                .setContentTitle(title)
                .setContentText(message)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setContentIntent(pendingIntent);
        
        // Display the notification
        NotificationManager notificationManager =
            (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        
        if (notificationManager != null) {
            // Use unique ID based on current time
            int notificationId = (int) System.currentTimeMillis();
            notificationManager.notify(notificationId, notificationBuilder.build());
            Log.d(TAG, "Notification displayed with ID: " + notificationId);
        }
    }
    
    /**
     * Send FCM token to backend server
     * This method should POST the token to your Django API
     */
    private void sendTokenToServer(String token) {
        Log.d(TAG, "Sending token to server: " + token.substring(0, 20) + "...");
        
        try {
            // TODO: Implement actual network call to send token
            // Example using URLConnection or Retrofit:
            
            // String url = "https://yourdomain.com/api/device-tokens/";
            // String json = "{\"token\": \"" + token + "\"}";
            
            // You can use:
            // - URLConnection (built-in)
            // - Retrofit (recommended for Android)
            // - OkHttp (also recommended)
            // - Volley (deprecated but still works)
            
            // For now, just log it
            Log.d(TAG, "Token ready to send to backend");
            
        } catch (Exception e) {
            Log.e(TAG, "Error sending token to server: " + e.getMessage());
        }
    }
    
    /**
     * Channel IDs must match those defined in NotificationChannels
     */
    public static class CHANNEL_IDS {
        public static final String CHANNEL_MESSAGES = "aetheria_messages";
        public static final String CHANNEL_SOCIAL = "aetheria_high_importance";
        public static final String CHANNEL_CALLS = "aetheria_calls";
        public static final String CHANNEL_SYSTEM = "aetheria_default";
    }
}
