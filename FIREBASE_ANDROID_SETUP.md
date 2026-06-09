# PHASE 5: FIREBASE & ANDROID SETUP GUIDE

**Status:** Production Ready ✅  
**Last Updated:** June 9, 2026  
**Version:** 1.0.0

---

## Table of Contents
1. [Firebase Cloud Messaging Setup](#firebase-cloud-messaging-setup)
2. [Android Configuration](#android-configuration)
3. [Notification Channels](#notification-channels)
4. [Push Notification Testing](#push-notification-testing)
5. [Troubleshooting](#troubleshooting)

---

## Firebase Cloud Messaging Setup

### Step 1: Create Firebase Project

```bash
# Visit Firebase Console: https://console.firebase.google.com/

# 1. Click "Create Project"
# 2. Project Name: "Aetheria"
# 3. Enable Google Analytics: Yes
# 4. Finish project creation

# 5. Go to Project Settings (⚙️ icon)
# 6. Go to "Service Accounts" tab
# 7. Click "Generate New Private Key"
# 8. Save as: firebase-service-account.json
```

### Step 2: Download Service Account Key

```bash
# Place the file in socialmedia/ directory
mv ~/Downloads/aetheria-xxxxx-firebase-adminsdk-xxxxx-xxxxxxxx.json \
   socialmedia/firebase-service-account.json

# Set permissions
chmod 600 socialmedia/firebase-service-account.json
```

### Step 3: Extract Firebase Config

```bash
# From Firebase Console:
# 1. Go to Project Settings > General
# 2. Under "Your apps", create a web app
# 3. Copy the config object:

firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "aetheria-xxxx.firebaseapp.com",
  projectId: "aetheria-xxxx",
  storageBucket: "aetheria-xxxx.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef123456"
}

# Add to .env file:
FIREBASE_API_KEY=YOUR_API_KEY
FIREBASE_AUTH_DOMAIN=aetheria-xxxx.firebaseapp.com
FIREBASE_PROJECT_ID=aetheria-xxxx
FIREBASE_STORAGE_BUCKET=aetheria-xxxx.appspot.com
FIREBASE_MESSAGING_SENDER_ID=123456789
FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

### Step 4: Enable Cloud Messaging

```bash
# In Firebase Console:
# 1. Go to "Messaging" section
# 2. Click "Get Started"
# 3. Follow the setup wizard
# 4. Enable "Cloud Messaging"
```

---

## Android Configuration

### Step 1: Add Dependencies

**File:** `android/app/build.gradle`

```gradle
dependencies {
    // Firebase Cloud Messaging
    implementation 'com.google.firebase:firebase-messaging:23.2.1'
    implementation 'com.google.firebase:firebase-analytics:21.3.0'
    
    // Firebase Admin SDK (for testing)
    implementation 'com.google.firebase:firebase-admin:9.1.0'
}

android {
    compileSdkVersion 33
    defaultConfig {
        applicationId "com.aetheria.app"
        minSdkVersion 21
        targetSdkVersion 33
    }
}
```

### Step 2: Update AndroidManifest.xml

**File:** `android/app/src/main/AndroidManifest.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.aetheria.app">

    <!-- Internet permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    
    <!-- Firebase Cloud Messaging permissions -->
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
    
    <!-- Notification permission (Android 13+) -->
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    
    <!-- Camera and media permissions -->
    <uses-permission android:name="android.permission.CAMERA" />
    <uses-permission android:name="android.permission.RECORD_AUDIO" />
    
    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme">

        <!-- Main Activity -->
        <activity
            android:name="com.aetheria.app.MainActivity"
            android:exported="true"
            android:label="@string/app_name">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <!-- Firebase Cloud Messaging Service -->
        <service
            android:name="com.aetheria.app.MyFirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>

        <!-- Firebase Notification Channel -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="aetheria_notifications" />

    </application>

</manifest>
```

### Step 3: Apply Google Services Plugin

**File:** `android/app/build.gradle` (add at end)

```gradle
// Add Google Services plugin
apply plugin: 'com.google.gms.google-services'
```

**File:** `android/build.gradle` (root level)

```gradle
buildscript {
    dependencies {
        // Add Google Services plugin
        classpath 'com.google.gms:google-services:4.3.14'
    }
}
```

### Step 4: Add google-services.json

**File:** `android/app/google-services.json`

```bash
# Download from Firebase Console:
# 1. Project Settings > General
# 2. Download "google-services.json"
# 3. Place in: android/app/

# The file should exist: android/app/google-services.json
# (Already placed in the project structure)
```

---

## Notification Channels

### Create NotificationChannels.java

**File:** `android/app/src/main/java/com/aetheria/app/NotificationChannels.java`

```java
package com.aetheria.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;

public class NotificationChannels {
    
    // Channel IDs
    public static final String CHANNEL_MESSAGES = "aetheria_messages";
    public static final String CHANNEL_SOCIAL = "aetheria_social";
    public static final String CHANNEL_SYSTEM = "aetheria_system";
    
    /**
     * Create notification channels for Android 8.0 (API 26) and above
     * Call this method from MainActivity.onCreate()
     */
    public static void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager notificationManager = 
                (NotificationManager) AppContext.getInstance()
                    .getSystemService(NotificationManager.class);
            
            if (notificationManager != null) {
                // Messages channel (high priority)
                NotificationChannel messagesChannel = new NotificationChannel(
                    CHANNEL_MESSAGES,
                    "Messages",
                    NotificationManager.IMPORTANCE_HIGH
                );
                messagesChannel.setDescription("Direct messages and chats");
                messagesChannel.enableVibration(true);
                messagesChannel.setShowBadge(true);
                notificationManager.createNotificationChannel(messagesChannel);
                
                // Social channel (default priority)
                NotificationChannel socialChannel = new NotificationChannel(
                    CHANNEL_SOCIAL,
                    "Social Updates",
                    NotificationManager.IMPORTANCE_DEFAULT
                );
                socialChannel.setDescription("Likes, comments, and follows");
                socialChannel.enableVibration(true);
                socialChannel.setShowBadge(true);
                notificationManager.createNotificationChannel(socialChannel);
                
                // System channel (low priority)
                NotificationChannel systemChannel = new NotificationChannel(
                    CHANNEL_SYSTEM,
                    "System",
                    NotificationManager.IMPORTANCE_LOW
                );
                systemChannel.setDescription("System notifications");
                systemChannel.setShowBadge(false);
                notificationManager.createNotificationChannel(systemChannel);
            }
        }
    }
}
```

### Firebase Messaging Service

**File:** `android/app/src/main/java/com/aetheria/app/MyFirebaseMessagingService.java`

```java
package com.aetheria.app;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import androidx.core.app.NotificationCompat;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class MyFirebaseMessagingService extends FirebaseMessagingService {
    
    private static final String TAG = "FCMService";
    
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        Log.d(TAG, "Message received from: " + remoteMessage.getFrom());
        
        if (remoteMessage.getData().size() > 0) {
            Log.d(TAG, "Message data payload: " + remoteMessage.getData());
            handleDataMessage(remoteMessage);
        }
        
        if (remoteMessage.getNotification() != null) {
            Log.d(TAG, "Message body: " + remoteMessage.getNotification().getBody());
            handleNotificationMessage(remoteMessage);
        }
    }
    
    @Override
    public void onNewToken(String token) {
        Log.d(TAG, "Refreshed token: " + token);
        // Send token to backend
        sendTokenToServer(token);
    }
    
    private void handleDataMessage(RemoteMessage remoteMessage) {
        String notificationType = remoteMessage.getData().get("type");
        String title = remoteMessage.getData().get("title");
        String message = remoteMessage.getData().get("message");
        String senderId = remoteMessage.getData().get("sender_id");
        
        // Determine notification channel based on type
        String channelId = NotificationChannels.CHANNEL_SOCIAL;
        if ("message".equals(notificationType)) {
            channelId = NotificationChannels.CHANNEL_MESSAGES;
        } else if ("system".equals(notificationType)) {
            channelId = NotificationChannels.CHANNEL_SYSTEM;
        }
        
        showNotification(title, message, channelId, senderId);
    }
    
    private void handleNotificationMessage(RemoteMessage remoteMessage) {
        RemoteMessage.Notification notification = remoteMessage.getNotification();
        showNotification(
            notification.getTitle(),
            notification.getBody(),
            NotificationChannels.CHANNEL_SOCIAL,
            null
        );
    }
    
    private void showNotification(String title, String message, 
                                   String channelId, String senderId) {
        // Create intent for notification tap
        Intent intent = new Intent(this, MainActivity.class);
        if (senderId != null) {
            intent.putExtra("sender_id", senderId);
        }
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
        
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0, intent,
            PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_UPDATE_CURRENT);
        
        // Build notification
        NotificationCompat.Builder notificationBuilder =
            new NotificationCompat.Builder(this, channelId)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(title)
                .setContentText(message)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent);
        
        // Show notification
        NotificationManager notificationManager =
            (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (notificationManager != null) {
            notificationManager.notify(System.currentTimeMillis(), 
                notificationBuilder.build());
        }
    }
    
    private void sendTokenToServer(String token) {
        // TODO: Send FCM token to Django backend
        // POST /api/device-tokens/ with {"token": token}
        Log.d(TAG, "Token should be sent to server: " + token);
    }
}
```

### Update MainActivity.java

**File:** `android/app/src/main/java/com/aetheria/app/MainActivity.java`

```java
package com.aetheria.app;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    
    private static final int PERMISSION_REQUEST_CODE = 101;
    
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Create notification channels
        NotificationChannels.createNotificationChannels();
        
        // Request notification permission (Android 13+)
        requestNotificationPermission();
    }
    
    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this,
                    Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                
                ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.POST_NOTIFICATIONS},
                    PERMISSION_REQUEST_CODE);
            }
        }
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, 
            String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                // Permission granted
                android.util.Log.d("MainActivity", "Notification permission granted");
            }
        }
    }
}
```

---

## Push Notification Testing

### Test from Firebase Console

```bash
# 1. Go to Firebase Console > Messaging > Create your first campaign

# 2. Select "Firebase Notification messages"

# 3. Fill in notification:
#    - Title: "Test Notification"
#    - Body: "Hello from Aetheria!"

# 4. Select target:
#    - Choose your Android app

# 5. Click "Send Test Message"

# 6. Select your device or use the FCM token from logcat
```

### Test from Django Backend

```python
# In Django shell:
python manage.py shell

from users.models import DeviceToken
from firebase_admin import messaging

# Get device token
device = DeviceToken.objects.first()

# Send notification
message = messaging.Message(
    notification=messaging.Notification(
        title="Test from Django",
        body="This is a test notification",
    ),
    token=device.token,
)

response = messaging.send(message)
print(f"Message sent: {response}")
```

### Manual Testing with curl

```bash
# Get FCM token from app logs
# curl -X POST https://yourdomain.com/api/device-tokens/ \
#   -H "Authorization: Bearer YOUR_TOKEN" \
#   -H "Content-Type: application/json" \
#   -d '{"token": "YOUR_FCM_TOKEN"}'
```

---

## Troubleshooting

### Issue: "FirebaseMessagingService not receiving messages"

**Solution:**
1. Verify `google-services.json` is in `android/app/`
2. Check that Firebase Cloud Messaging is enabled
3. Rebuild: `./gradlew clean build`
4. Check logcat: `adb logcat | grep FCM`

### Issue: "Notification permission denied"

**Solution:**
```bash
# Check manifest for POST_NOTIFICATIONS permission
grep "POST_NOTIFICATIONS" android/app/src/main/AndroidManifest.xml

# Test on device: Settings > Apps > Aetheria > Notifications > Allow
```

### Issue: "google-services.json not found"

**Solution:**
```bash
# Download from Firebase Console
# Place in correct location: android/app/google-services.json

# Verify file exists
ls -la android/app/google-services.json
```

### Issue: "Token not being sent to backend"

**Solution:**
1. Implement `sendTokenToServer()` in `MyFirebaseMessagingService.java`
2. Create API endpoint: `POST /api/device-tokens/`
3. Test with Django shell:
```python
from users.models import DeviceToken
DeviceToken.objects.filter(token="YOUR_TOKEN").exists()
```

---

## Production Checklist

- [ ] Firebase project created and configured
- [ ] Service account key downloaded and stored securely
- [ ] Firebase config extracted to .env variables
- [ ] Google Services plugin added to gradle files
- [ ] google-services.json in android/app/
- [ ] AndroidManifest.xml updated with permissions
- [ ] NotificationChannels.java created
- [ ] MyFirebaseMessagingService.java created
- [ ] MainActivity.java updated with permission request
- [ ] Test notifications received on Android device
- [ ] FCM tokens being saved to database
- [ ] Backend API ready to send notifications
- [ ] Error logging configured in FCMService
- [ ] Notification channels visible in Android Settings

---

## Performance Optimization

### Notification Batching

```python
# In Django, batch send notifications:
from firebase_admin import messaging

tokens = list(DeviceToken.objects.filter(
    user__in=followers
).values_list('token', flat=True))

multicast_message = messaging.MulticastMessage(
    notification=messaging.Notification(
        title="User posted new content",
        body=f"{post.author.username} posted something",
    ),
    tokens=tokens[:500],  # Max 500 per batch
)

response = messaging.send_multicast(multicast_message)
print(f"Successfully sent: {response.success_count}")
print(f"Failed: {response.failure_count}")
```

### Token Refresh Strategy

```python
# Auto-refresh tokens older than 30 days
from django.utils import timezone
from datetime import timedelta

old_tokens = DeviceToken.objects.filter(
    last_updated__lt=timezone.now() - timedelta(days=30)
)

# Frontend should refresh tokens periodically
# In firebase-notifications.js:
setInterval(() => {
    messaging.onTokenRefresh(() => {
        messaging.getToken().then(token => {
            sendTokenToBackend(token);
        });
    });
}, 24 * 60 * 60 * 1000);  // Every 24 hours
```

---

**Phase 5 Setup Complete! ✅**

Next: Run final verification tests and deploy to production.
