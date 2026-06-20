# 🌌 Aetheria — Premium Social Media Platform

<div align="center">

![Aetheria](https://img.shields.io/badge/Aetheria-Social%20Platform-8b5cf6?style=for-the-badge&logo=instagram&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2+-092E20?style=flat-square&logo=django&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=flat-square&logo=postgresql&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Enabled-5A0FC8?style=flat-square&logo=pwa&logoColor=white)
![Vercel](https://img.shields.io/badge/Deployed-Vercel-000000?style=flat-square&logo=vercel&logoColor=white)
![WebSockets](https://img.shields.io/badge/WebSockets-Real--time-green?style=flat-square&logo=socket.io)

**A sophisticated, feature-rich social media platform delivering a premium, immersive social networking experience.**

[🌐 Live Demo](https://socialmedia-phi-roan.vercel.app) · [Report Bug](https://github.com/23CABSAKTHIRENGANATHANk/CodeAlpha_Aetheria/issues) · [GitHub](https://github.com/23CABSAKTHIRENGANATHANk/CodeAlpha_Aetheria)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API & WebSockets](#api--websockets)
- [PWA Support](#pwa-support)
- [Author](#author)

---

## 🌟 Overview

**Aetheria** is a full-featured social media platform engineered to deliver a premium social networking experience. Built on a robust Python/Django backend with real-time capabilities, it combines the best design principles of Instagram, Twitter, and modern social apps.

The platform features ephemeral stories, post reactions, hashtag discovery, infinite scroll, real-time messaging, push notifications, and PWA installation — all wrapped in a sleek, responsive UI.

**Live Production:** [https://socialmedia-phi-roan.vercel.app](https://socialmedia-phi-roan.vercel.app)

Built as part of the **CodeAlpha Internship Program**.

---

## ✨ Features

### 📸 Ephemeral Stories
- **Auto-Expiration:** Stories automatically expire after 24 hours
- **Visual Indicators:** Gradient rings for unviewed, grey rings for viewed stories
- **Full-Screen Viewer:** Sequential navigation with 5-second auto-progression, manual tap-to-advance, viewer analytics, and owner controls

### 🎭 Post Reactions
- **6 Reaction Types:** 😍 ❤️ 😂 😮 😢 😠 with a glassmorphism emoji picker
- **Real-time Aggregation:** Dynamic reaction count badges on each post card

### #️⃣ Hashtag Discovery
- **Auto Parsing:** Backend automatically scans and links hashtags in post content
- **Dedicated Feeds:** Browse all public posts associated with any hashtag
- **Trending Hashtags:** Real-time display of trending topics

### 🔖 Content Bookmarking
- **Private Collections:** Save posts to a personal "Saved" section
- **Secure Access:** Visible only to the authenticated user

### 🔍 Explore & Discovery
- **Engagement-Based Feed:** Posts ranked by aggregate reaction metrics
- **Account Recommendations:** Personalized suggestions based on engagement patterns

### 🔒 Privacy & Social Controls
- **Granular Privacy Settings:** Control post visibility, follower lists, and profile details
- **Follow Request System:** Accept/decline with dual-user notifications

### 💬 Real-time Messaging
- Live chat powered by Django Channels + WebSockets
- Push notifications via Firebase
- Chat starters and conversation management

### 📱 Progressive Web App (PWA)
- Installable on iOS, Android & desktop
- Service Worker caches critical assets for offline functionality
- Native-app-like experience

### ⚡ Performance
- **Infinite Scroll:** Auto-loads content as users scroll
- **Skeleton Screens:** Animated loading states for better UX
- **Redis Caching:** Fast data access for frequently accessed content

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Backend Framework** | Python 3 + Django 4.2 |
| **Database (Prod)** | Neon PostgreSQL |
| **Database (Dev)** | SQLite |
| **Frontend** | HTML5, Vanilla JavaScript, CSS3 |
| **Real-time** | Django Channels + WebSockets + Daphne |
| **Push Notifications** | Firebase Admin SDK |
| **File Storage** | Cloudinary |
| **Caching** | Redis + django-redis |
| **Static Files** | WhiteNoise |
| **Deployment** | Vercel |
| **Mobile** | Capacitor (Android/iOS APK) |
| **ASGI Server** | Uvicorn |

---

## 📁 Project Structure

```
CodeAlpha_Aetheria/
├── socialmedia/               # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── posts/                     # Posts, reactions, hashtags, stories
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── users/                     # User profiles, follows, privacy
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── utils/                     # Shared utilities
├── templates/                 # Django HTML templates
│   └── ...
├── static/                    # CSS, JavaScript, PWA assets
│   ├── css/
│   ├── js/
│   └── manifest.json          # PWA manifest
├── android/                   # Capacitor Android project
├── requirements.txt
├── manage.py
├── render.yaml                # Render deployment config
├── vercel.json                # Vercel deployment config
├── build-apk.bat              # Windows APK builder
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Git
- pip

### 1. Clone the Repository

```bash
git clone https://github.com/23CABSAKTHIRENGANATHANk/CodeAlpha_Aetheria.git
cd CodeAlpha_Aetheria
```

### 2. Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials (see Environment Variables below)
```

### 5. Apply Migrations

```bash
python manage.py migrate
```

### 6. Collect Static Files

```bash
python manage.py collectstatic
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000/**

Admin Panel: **http://127.0.0.1:8000/admin/**

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory:

```env
# Django
SECRET_KEY=your-django-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.vercel.app,localhost

# Database (Production - Neon PostgreSQL)
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Cloudinary (File Storage)
CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name

# Redis (Caching + WebSockets)
REDIS_URL=redis://localhost:6379

# Firebase (Push Notifications)
FIREBASE_SERVER_KEY=your-firebase-server-key

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 🔌 API & WebSockets

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/posts/` | List & create posts |
| `POST` | `/posts/:id/react/` | React to a post |
| `GET` | `/posts/:id/story/` | View a story |
| `GET` | `/explore/` | Explore trending content |
| `GET` | `/hashtag/:tag/` | Posts by hashtag |
| `POST` | `/users/follow/:id/` | Follow/unfollow a user |
| `GET` | `/users/:id/profile/` | View user profile |
| `WS` | `/ws/chat/:room_id/` | Real-time messaging |

---

## 📱 PWA Support

Aetheria is a fully installable **Progressive Web App**:

1. Open [https://socialmedia-phi-roan.vercel.app](https://socialmedia-phi-roan.vercel.app) in your browser
2. Click **"Install App"** in the browser address bar (Chrome/Edge)
3. On mobile: tap **"Add to Home Screen"** in the browser menu

Features enabled:
- ✅ Offline support via Service Worker
- ✅ Push notifications (Firebase)
- ✅ Full-screen standalone mode
- ✅ App icon & splash screen

---

## 🎓 About This Project

This project was built as **Task 2** of the **CodeAlpha Web Development Internship**, demonstrating advanced Django development with real-time WebSockets, PWA capabilities, Firebase push notifications, Cloudinary media storage, and production deployment on Vercel.

---

## 👤 Author

**Sakthirenganathan K**
- GitHub: [@23CABSAKTHIRENGANATHANk](https://github.com/23CABSAKTHIRENGANATHANk)
- Live: [https://socialmedia-phi-roan.vercel.app](https://socialmedia-phi-roan.vercel.app)
- Internship: CodeAlpha Web Development

---

## 📄 License

MIT License — feel free to use and modify.