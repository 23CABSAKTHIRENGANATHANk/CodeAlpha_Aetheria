// Android Notification Channels Configuration
// Place in android/app/src/main/java/com/aetheria/app/NotificationChannels.java

package com.aetheria.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.os.Build;

public class NotificationChannels {
    
    /**
     * Create notification channels for Android 8.0+
     * Call this from MainActivity.onCreate() or FirebaseMessagingService
     */
    public static void createNotificationChannels(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager notificationManager = 
                context.getSystemService(NotificationManager.class);
            
            if (notificationManager != null) {
                // 1. HIGH PRIORITY MESSAGE CHANNEL
                createMessageChannel(notificationManager, context);
                
                // 2. HIGH PRIORITY NOTIFICATION CHANNEL
                createNotificationChannel(notificationManager, context);
                
                // 3. CALL CHANNEL
                createCallChannel(notificationManager, context);
                
                // 4. DEFAULT CHANNEL
                createDefaultChannel(notificationManager, context);
            }
        }
    }
    
    /**
     * Create high priority message channel with sound and vibration
     */
    private static void createMessageChannel(NotificationManager manager, Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            String channelId = "aetheria_messages";
            String channelName = "Messages";
            String channelDescription = "Direct messages and chat notifications";
            int importance = NotificationManager.IMPORTANCE_HIGH;
            
            NotificationChannel channel = new NotificationChannel(channelId, channelName, importance);
            channel.setDescription(channelDescription);
            
            // Enable sound
            AudioAttributes audioAttrs = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .build();
            
            channel.setSound(
                RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION),
                audioAttrs
            );
            
            // Enable vibration
            channel.enableVibration(true);
            channel.setVibrationPattern(new long[]{0, 250, 250, 250});
            
            // Enable lights
            channel.enableLights(true);
            channel.setLightColor(0xFF5722);
            
            // Show badge
            channel.setShowBadge(true);
            
            manager.createNotificationChannel(channel);
        }
    }
    
    /**
     * Create high priority notification channel
     */
    private static void createNotificationChannel(NotificationManager manager, Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            String channelId = "aetheria_high_importance";
            String channelName = "Notifications";
            String channelDescription = "Like, comment, follow, and other notification alerts";
            int importance = NotificationManager.IMPORTANCE_HIGH;
            
            NotificationChannel channel = new NotificationChannel(channelId, channelName, importance);
            channel.setDescription(channelDescription);
            
            // Enable sound
            AudioAttributes audioAttrs = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION)
                .build();
            
            channel.setSound(
                RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION),
                audioAttrs
            );
            
            // Enable vibration
            channel.enableVibration(true);
            channel.setVibrationPattern(new long[]{0, 200});
            
            // Enable lights
            channel.enableLights(true);
            channel.setLightColor(0x7C3AED);
            
            // Show badge
            channel.setShowBadge(true);
            
            manager.createNotificationChannel(channel);
        }
    }
    
    /**
     * Create call channel with distinct sound
     */
    private static void createCallChannel(NotificationManager manager, Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            String channelId = "aetheria_calls";
            String channelName = "Calls";
            String channelDescription = "Incoming call notifications";
            int importance = NotificationManager.IMPORTANCE_MAX;
            
            NotificationChannel channel = new NotificationChannel(channelId, channelName, importance);
            channel.setDescription(channelDescription);
            
            // Enable sound (different sound for calls)
            AudioAttributes audioAttrs = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION_COMMUNICATION_REQUEST)
                .build();
            
            channel.setSound(
                RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE),
                audioAttrs
            );
            
            // Enable vibration with pattern
            channel.enableVibration(true);
            channel.setVibrationPattern(new long[]{0, 100, 200, 100});
            
            // Enable lights
            channel.enableLights(true);
            channel.setLightColor(0xFF0000);
            
            manager.createNotificationChannel(channel);
        }
    }
    
    /**
     * Create default notification channel
     */
    private static void createDefaultChannel(NotificationManager manager, Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            String channelId = "aetheria_default";
            String channelName = "Default";
            String channelDescription = "General app notifications";
            int importance = NotificationManager.IMPORTANCE_DEFAULT;
            
            NotificationChannel channel = new NotificationChannel(channelId, channelName, importance);
            channel.setDescription(channelDescription);
            channel.enableVibration(false);
            
            manager.createNotificationChannel(channel);
        }
    }
}
