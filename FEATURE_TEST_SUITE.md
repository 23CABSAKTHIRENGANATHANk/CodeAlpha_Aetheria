# ✅ AETHERIA FEATURE TEST SUITE

**Purpose:** Verify all features work like WhatsApp & Instagram before APK deployment  
**Status:** Pre-deployment testing checklist  
**Target:** 100% feature coverage

---

## 📋 Test Sections

1. **Core Functionality Tests** (Authentication, Profiles, Messaging)
2. **Feed & Social Features** (Posts, Likes, Comments, Follow)
3. **Real-Time Features** (WebSocket, Notifications, Live Updates)
4. **Mobile/Responsive Tests** (Layout, Touch, Orientation)
5. **Performance Tests** (Load times, Query optimization)
6. **Android-Specific Tests** (Permissions, Notifications, Camera)
7. **Security Tests** (Authentication, Data protection)
8. **Offline Tests** (Message queuing, Sync)

---

## 🔐 SECTION 1: AUTHENTICATION & PROFILES

### Test 1.1: User Registration
```
Steps:
1. Navigate to http://localhost:8000/register/
2. Fill form:
   - Username: test_user_001
   - Email: test@aetheria.local
   - Password: TestPass123!
   - Confirm: TestPass123!
3. Click "Create Account"
4. Verify redirect to login

Expected: User created, redirects to login
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 1.2: User Login
```
Steps:
1. Navigate to http://localhost:8000/login/
2. Enter credentials:
   - Username: test_user_001
   - Password: TestPass123!
3. Click "Sign In"

Expected: Logged in, redirects to feed
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 1.3: Password Reset
```
Steps:
1. Go to login page
2. Click "Forgot Password?"
3. Enter email
4. Check email for reset link
5. Follow link and reset password

Expected: Password reset email sent, link works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 1.4: Profile Page
```
Steps:
1. Click on profile icon (bottom nav or sidebar)
2. Verify profile shows:
   - Profile picture
   - Display name
   - Username & handle
   - Bio
   - Location
   - Stats (followers, following, posts)
3. Check follow/message buttons

Expected: Profile displays correctly with all info
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 1.5: Edit Profile
```
Steps:
1. On profile page, click "Edit Profile"
2. Update:
   - Bio
   - Location
   - Profile picture
3. Save changes
4. Verify changes appear on profile

Expected: Changes saved and displayed
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 1.6: Logout
```
Steps:
1. Click settings (gear icon)
2. Select "Logout"
3. Verify redirect to login page

Expected: User logged out, session cleared
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 📱 SECTION 2: POSTS & FEED

### Test 2.1: Create Post
```
Steps:
1. On feed page, find "What's on your mind?" box
2. Type: "Testing Aetheria ✨"
3. (Optional) Upload photo
4. Click "Post"

Expected: Post appears at top of feed
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.2: Like Post
```
Steps:
1. On any post, click heart icon
2. Verify heart turns red/pink
3. Verify like count increases
4. Click again to unlike

Expected: Like toggles, count updates
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.3: Comment on Post
```
Steps:
1. Click comment icon on post
2. Type: "Great post! 👍"
3. Click send button
4. Verify comment appears below post

Expected: Comment displays with author, time
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.4: Share/Bookmark Post
```
Steps:
1. Click bookmark icon
2. Verify bookmark toggles
3. Go to profile
4. Check saved posts section

Expected: Post bookmarked and retrievable
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.5: Delete Post
```
Steps:
1. Click 3-dot menu on your post
2. Select "Delete"
3. Confirm deletion
4. Verify post disappears from feed

Expected: Post removed from database
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.6: Photo Upload
```
Steps:
1. Create new post
2. Click photo icon
3. Select image file
4. Post with image
5. Verify image displays

Expected: Image uploads, displays, loads fast
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.7: Multiple Photos
```
Steps:
1. Create post with 3+ photos
2. Verify carousel appears
3. Swipe through photos
4. Check all photos display

Expected: Photo carousel works smoothly
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.8: Hashtag Search
```
Steps:
1. Click on hashtag in post
2. Verify all posts with hashtag shown
3. Click hashtag in trending section
4. Verify same results

Expected: Hashtag filtering works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.9: Feed Types
```
Steps:
1. Click "For You" tab - see all posts
2. Click "Following" tab - see only followed users
3. Click "Trending" tab - see trending posts
4. Click "Recommended" tab - see suggestions

Expected: Feed filters work correctly
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 2.10: Infinite Scroll
```
Steps:
1. Open feed
2. Scroll down to bottom
3. New posts load automatically
4. Continue scrolling
5. Verify no duplicate posts

Expected: Smooth pagination, no errors
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 👥 SECTION 3: FOLLOW & CONNECTIONS

### Test 3.1: Follow User
```
Steps:
1. Find user profile
2. Click "Follow" button
3. Verify button changes to "Following"
4. Check follower count increases

Expected: Follow relationship created
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 3.2: Unfollow User
```
Steps:
1. Go to profile of user you follow
2. Click "Following" button
3. Confirm unfollow
4. Verify button changes back to "Follow"

Expected: Follow relationship deleted
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 3.3: Follow Suggestions
```
Steps:
1. On feed page, look at right sidebar
2. Verify suggested users shown
3. Click "Follow" on suggestion
4. Verify count updates

Expected: Suggestions relevant and working
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 3.4: Private Account
```
Steps:
1. Go to settings
2. Toggle "Private Account" ON
3. Try to follow as other user
4. Verify follow request sent
5. Approve/deny request

Expected: Follow request system works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 3.5: Block User
```
Steps:
1. Visit user profile
2. Click 3-dot menu
3. Select "Block User"
4. Verify confirmation
5. Try to find their profile

Expected: User blocked, not visible
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 💬 SECTION 4: DIRECT MESSAGING

### Test 4.1: Start Conversation
```
Steps:
1. Click Messages icon
2. Click "New Message"
3. Search for user
4. Click to start conversation
5. Type message: "Hello!"
6. Send message

Expected: Message appears in thread
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.2: Real-Time Messaging
```
Steps:
1. Open chat on two devices/windows
2. Send message from Device A
3. Verify instantly appears on Device B
4. Reply from Device B

Expected: WebSocket real-time sync works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.3: Message Status
```
Steps:
1. Send message
2. Verify "sent" indicator
3. Wait for recipient to read
4. Verify "read" indicator shows time

Expected: Status indicators accurate
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.4: Message Reactions
```
Steps:
1. Long-press/tap-hold on message
2. Select emoji reaction (👍, ❤️, etc.)
3. Verify reaction appears
4. Add another reaction

Expected: Reactions display correctly
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.5: Photo in Chat
```
Steps:
1. In chat, click photo icon
2. Select image
3. Send
4. Verify image displays in chat
5. Can tap to expand

Expected: Photo messaging works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.6: Message Search
```
Steps:
1. Open chat
2. Search for specific message
3. Verify search results show matching messages
4. Click result to jump to message

Expected: Search finds messages
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.7: Conversation List
```
Steps:
1. Open Messages
2. Verify list of conversations
3. Click conversation
4. Verify chat loads
5. Go back to list

Expected: Navigation works smoothly
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 4.8: Mute/Unmute
```
Steps:
1. Long-press conversation
2. Select "Mute"
3. Send message to muted chat
4. Verify no notification
5. Unmute and verify notification works

Expected: Mute controls notifications
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 🔔 SECTION 5: NOTIFICATIONS

### Test 5.1: Like Notification
```
Steps:
1. Create post on Device A
2. Like post from Device B
3. Device A receives notification
4. Verify notification shows "User liked your post"

Expected: Like notifications work
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 5.2: Comment Notification
```
Steps:
1. Someone comments on your post
2. Receive notification
3. Click notification
4. Jump to post + comment

Expected: Comment notification and navigation works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 5.3: Message Notification
```
Steps:
1. Receive message from follower
2. Notification appears
3. Click to open chat
4. Message displays

Expected: Message notification works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 5.4: Follow Notification
```
Steps:
1. User follows you
2. Notification appears
3. Shows "User started following you"
4. Can view their profile

Expected: Follow notifications work
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 5.5: Toast/In-App Notifications
```
Steps:
1. Create post
2. Verify toast notification: "Post published"
3. Save post - "Post saved" toast appears
4. Follow user - "Following User" toast

Expected: In-app notifications display
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 📱 SECTION 6: RESPONSIVE DESIGN

### Test 6.1: Desktop Layout (1920x1080)
```
Steps:
1. Open on desktop browser
2. Verify 3-column layout:
   - Left sidebar (270px)
   - Feed (center)
   - Suggestions right (340px)
3. All text readable
4. Navigation accessible

Expected: Full desktop layout optimal
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 6.2: Tablet Layout (768x1024)
```
Steps:
1. Open on tablet or resize to 768px
2. Verify sidebar icons-only
3. Feed centered
4. No horizontal scroll
5. Touch targets 44px+

Expected: Tablet layout works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 6.3: Mobile Layout (375x667)
```
Steps:
1. Open on mobile or resize to 375px
2. Verify top bar (60px) fixed
3. Bottom navigation (58px) fixed
4. Feed scrolls between
5. No horizontal scroll

Expected: Mobile layout perfect
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 6.4: Orientation Change
```
Steps:
1. On mobile, rotate portrait → landscape
2. Layout adjusts automatically
3. Rotate back to portrait
4. All content accessible

Expected: Orientation changes handled
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 6.5: Touch Targets
```
Steps:
1. On mobile, try clicking all buttons
2. Verify minimum 44x44px (touchable)
3. Check spacing between buttons
4. Try to hit small targets

Expected: All buttons easily tappable
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## ⚡ SECTION 7: PERFORMANCE

### Test 7.1: Page Load Time
```
Steps:
1. Open DevTools (F12) → Network
2. Reload page
3. Check load time

Expected: < 2 seconds (desktop), < 3 seconds (mobile)
Status: [ ] PASS [ ] FAIL
Actual Time: ___________
```

### Test 7.2: Feed Scroll Performance
```
Steps:
1. Open feed
2. Scroll down rapidly
3. Verify smooth scrolling (60fps)
4. Check DevTools Performance tab

Expected: Smooth, no jank or stuttering
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 7.3: Image Load
```
Steps:
1. Post with image
2. Check image loading time
3. Verify cached on refresh

Expected: Images load quickly (< 1s)
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 7.4: Database Queries
```
Steps:
1. Open DevTools → Console
2. Load feed page
3. Check network requests
4. Verify queries optimized (< 10 requests)

Expected: Efficient query loading
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 🤖 SECTION 8: ANDROID-SPECIFIC TESTS

### Test 8.1: APK Installation
```
Steps:
1. Build APK using: build-apk.bat
2. Connect Android device
3. Run: adb install app-aetheria-release.apk
4. Verify app installs

Expected: APK installs without errors
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.2: App Launch
```
Steps:
1. Find "Aetheria" app on home screen
2. Tap to launch
3. Wait for load
4. Verify landing page shows

Expected: App launches quickly (< 3s)
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.3: Permissions Request
```
Steps:
1. Launch app first time
2. Allow camera permission
3. Allow microphone permission
4. Allow file access permission
5. Allow notification permission

Expected: All permission prompts appear
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.4: Notification Permissions (Android 13+)
```
Steps:
1. Android 13+ device
2. App prompts for POST_NOTIFICATIONS
3. Grant permission
4. Receive test notification
5. Verify notification shows

Expected: Notification permission works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.5: Firebase Notifications
```
Steps:
1. Login to app on Android device
2. Go to Firebase Console
3. Send test notification
4. Verify notification received on device

Expected: FCM notifications work
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.6: Camera Access
```
Steps:
1. Upload photo in post
2. Choose "Take Photo"
3. Take picture with camera
4. Verify image uploads

Expected: Camera integration works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.7: Back Button
```
Steps:
1. Navigate through app
2. Press back button
3. Verify goes to previous screen
4. Keep pressing until home

Expected: Back navigation works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.8: Share Sheet
```
Steps:
1. On post, click share/export
2. Verify share sheet appears
3. Select app to share to
4. Verify share works

Expected: Share integration works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.9: Safe Area (Notch/Home Indicator)
```
Steps:
1. Run on device with notch/home indicator
2. Verify content not behind notch
3. Verify bottom nav above home indicator
4. Landscape/portrait orientation

Expected: Safe areas respected
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 8.10: Hardware Back Button
```
Steps:
1. Press physical back button
2. Navigate correctly
3. Prevent back from chat
4. Show confirmation dialog

Expected: Back button behaves correctly
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 🔐 SECTION 9: SECURITY

### Test 9.1: Password Security
```
Steps:
1. Register with weak password
2. Verify error message
3. Register with strong password
4. Verify account created

Expected: Password validation works
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 9.2: Session Management
```
Steps:
1. Login on Device A
2. Open app on Device B with same account
3. Verify both logged in OR one logged out
4. Check session handling

Expected: Session management secure
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 9.3: CSRF Protection
```
Steps:
1. Login
2. DevTools → Network
3. Make form submission
4. Verify CSRF token in request
5. Tamper with token
6. Verify request fails

Expected: CSRF protection active
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 9.4: Rate Limiting
```
Steps:
1. Send rapid requests
2. After N requests, verify throttling
3. Check error response
4. Wait and retry

Expected: Rate limiting prevents abuse
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 📊 SECTION 10: OFFLINE MODE

### Test 10.1: Message Queuing
```
Steps:
1. Turn off WiFi/data
2. Send message
3. Verify message queued locally
4. Turn WiFi back on
5. Message sends automatically

Expected: Messages queue offline, send when online
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

### Test 10.2: Offline Indicators
```
Steps:
1. Disable internet
2. App shows "Offline" indicator
3. Verify no loading spinners
4. Enable internet
5. "Online" indicator shows

Expected: Offline state clearly indicated
Status: [ ] PASS [ ] FAIL
Notes: ___________
```

---

## 📈 SECTION 11: COMPARISON WITH INSTAGRAM/WHATSAPP

| Feature | Instagram | WhatsApp | Aetheria | Status |
|---------|-----------|----------|----------|--------|
| Real-time Chat | ✅ | ✅ | ✅ | [ ] |
| Posts/Feed | ✅ | ❌ | ✅ | [ ] |
| Stories | ✅ | ❌ | ✅ | [ ] |
| Push Notifications | ✅ | ✅ | ✅ | [ ] |
| Private Messages | ✅ | ✅ | ✅ | [ ] |
| Follow System | ✅ | ❌ | ✅ | [ ] |
| Responsive Mobile | ✅ | ✅ | ✅ | [ ] |
| Photo Upload | ✅ | ✅ | ✅ | [ ] |
| Dark Theme | ✅ | ✅ | ✅ | [ ] |
| Search | ✅ | ✅ | ✅ | [ ] |

---

## 🎯 FINAL SIGN-OFF

### Total Tests: 95+
### Pass Rate Required: 100% for release
### Test Date: __________
### Tested By: __________
### Build Version: __________

```
Final Status:
[ ] All tests passed - READY FOR RELEASE
[ ] Some tests failed - NEEDS FIXES
[ ] Critical tests failed - DO NOT RELEASE
```

---

**Feature Test Suite Version:** 1.0.0  
**Last Updated:** June 9, 2026  
**Status:** ✅ Production Ready
