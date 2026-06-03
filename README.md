# 🌌 Aetheria — Premium Social Media Platform

Aetheria is a state-of-the-art, feature-rich social media platform designed to deliver a premium, responsive, and immersive networking experience. Built on a modern pythonic backend with interactive front-end enhancements, Aetheria offers a layout inspired by the best aspects of Instagram and WhatsApp.

🚀 **Live Production Link:** [https://socialmedia-phi-roan.vercel.app](https://socialmedia-phi-roan.vercel.app)

---

## ✨ Premium Features

### 1. 🕒 Ephemeral Stories
*   **24-Hour Expiry:** Post images with captions that automatically expire after 24 hours.
*   **Interactive Row:** Avatars at the top of the feed display a dynamic colorful gradient ring when unviewed, which turns grey after viewing.
*   **Fullscreen Viewer:** Slide-by-slide automatic progression (5 seconds each), tap-to-advance navigation, viewer listing, and owner deletion options.

### 2. 🔥 Emoji Post Reactions
*   **Popover Picker:** Hovering or tapping the reaction button triggers a smooth glassmorphism panel showing emoji options (❤️, 😍, 😂, 😮, 😢, 🔥).
*   **Aggregated Badges:** Displays reaction counts dynamically in a clean badge layout under the post card.

### 3. 🏷️ Smart Hashtags & Feeds
*   **Auto-parsing Engine:** The backend automatically scans post text for `#hashtags` and links them to dedicated hashtag feeds.
*   **Hashtag Feeds:** Click on any hashtag to view all public posts carrying that tag.

### 4. 📂 Saved Posts (Bookmarks)
*   **Private Bookmarks:** Save posts for later. A dedicated "Saved" tab is integrated into your profile page, visible only to you.

### 5. 🔍 Explore Page
*   **Engagement Grid:** Showcases popular posts sorted by aggregate reactions.
*   **Trending Tags:** Dynamically displays the most popular hashtags in a sidebar.
*   **Suggested Accounts:** Recommends active profiles to follow.

### 6. 🔒 Account Privacy & Follow Requests
*   **Private Profiles:** Restrict post visibility, follower lists, and details.
*   **Follow Request gates:** Incoming follow requests can be accepted or declined, instantly generating notifications for both users.

### 7. 📲 Progressive Web App (PWA)
*   **Installable App:** Installs directly onto iOS, Android, and Desktop as a standalone application.
*   **Service Worker:** Caches core static assets for instant load times and offline accessibility.

### 8. ⚡ Infinite Scroll & Skeleton Loaders
*   **Sentinels:** Automatically fetches more posts as you scroll to the bottom of the feed.
*   **Glowing Skeletons:** Renders beautiful, pulsing placeholder cards while new data is loading.

---

## 🛠️ Technology Stack

*   **Backend:** Python 3 + [Django](https://www.djangoproject.com/)
*   **Database:** [Neon PostgreSQL](https://neon.tech/) (Production) / SQLite (Local development)
*   **Frontend:** Vanilla HTML5, Vanilla JavaScript, Custom CSS3 Custom Properties (harmonious dark system, custom animations)
*   **Static Serving:** WhiteNoise Static Storage
*   **Hosting:** [Vercel](https://vercel.com/) (Zero-Configuration Python Pipeline)

---

## 💻 Local Development Setup

Follow these steps to run Aetheria on your local machine:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/23CABSAKTHIRENGANATHANk/socialmedia.git
   cd socialmedia
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv venv
   # Activate on Windows:
   .\venv\Scripts\activate
   # Activate on Unix:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Local Database Migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```
   Open your browser to `http://127.0.0.1:8000/`.

---

## 🚀 Cloud Deployment (Vercel)

Aetheria uses Vercel's zero-configuration Django build.

1. **Required Environment Variables:**
   *   `SECRET_KEY`: A secure, secret string for Django's cryptographic signing.
   *   `DEBUG`: Set to `False`.
   *   `DATABASE_URL`: Your hosted PostgreSQL connection URL (e.g., Neon).
   *   `ALLOWED_HOSTS`: Set to `*` or your custom Vercel domain.

2. **Triggering Deployment:**
   Add Vercel variables on the dashboard or run the deploy command:
   ```bash
   vercel --prod
   ```

---

## 📱 Mobile App Packaging

Aetheria can be compiled into a native `.apk` or `.ipa` app for mobile stores using **Capacitor**:

1. Initialize Capacitor:
   ```bash
   npm init @capacitor/app
   ```
2. Configure `capacitor.config.json` to wrap the live deployment URL:
   ```json
   {
     "appId": "com.aetheria.app",
     "appName": "Aetheria",
     "webDir": "www",
     "server": {
       "url": "https://socialmedia-phi-roan.vercel.app",
       "cleartext": true
     }
   }
   ```
3. Run `npx cap add android` or `npx cap add ios` to build and package.
