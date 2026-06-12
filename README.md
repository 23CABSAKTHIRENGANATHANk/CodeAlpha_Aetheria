# Aetheria — Premium Social Media Platform

## Overview

Aetheria is a sophisticated, feature-rich social media platform engineered to deliver a premium, responsive, and immersive social networking experience. The platform is built on a robust Python backend with modern interactive front-end enhancements, combining the best design principles of leading social media applications.

**Live Production:** [https://socialmedia-phi-roan.vercel.app](https://socialmedia-phi-roan.vercel.app)

---

## Core Features

### Ephemeral Stories
- **Automated Expiration:** Images and captions expire automatically after 24 hours
- **Visual Status Indicators:** Dynamic gradient rings denote unviewed stories; grey rings indicate viewed content
- **Full-Screen Viewer:** Sequential navigation with 5-second auto-progression, manual tap-to-advance, viewer analytics, and owner controls

### Post Reactions
- **Intuitive Reaction System:** Glassmorphism-based emoji picker with six reaction options (❤️, 😍, 😂, 😮, 😢, 🔥)
- **Real-time Aggregation:** Dynamic reaction count badges displayed beneath post cards

### Hashtag Discovery & Curation
- **Intelligent Parsing:** Automatic backend scanning and linking of hashtags within post content
- **Dedicated Hashtag Feeds:** Browse all public posts associated with specific hashtags

### Content Bookmarking
- **Private Collections:** Save posts for later reference through a dedicated "Saved" profile section
- **Secure Access:** Saved collections remain visible exclusively to the user

### Explore & Discovery
- **Engagement-Based Feed:** Popular posts ranked by aggregate reaction metrics
- **Trending Analysis:** Real-time display of trending hashtags
- **Account Recommendations:** Personalized profile suggestions based on engagement patterns

### Privacy & Social Controls
- **Granular Privacy Settings:** Restrict post visibility, follower lists, and user details
- **Follow Request Management:** Accept or decline follow requests with dual-user notifications

### Progressive Web Application (PWA)
- **Cross-Platform Installation:** Deployable to iOS, Android, and desktop environments as a standalone application
- **Offline Capability:** Service Worker implementation caches critical assets for instant loading and offline functionality

### Performance Optimization
- **Infinite Scroll:** Automatic content loading as users reach feed boundaries
- **Loading States:** Animated skeleton screens enhance user experience during data fetching

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend Framework** | Python 3 with Django |
| **Database** | Neon PostgreSQL (Production) / SQLite (Development) |
| **Frontend** | HTML5, Vanilla JavaScript, CSS3 with CSS Custom Properties |
| **Static Asset Management** | WhiteNoise Static Storage |
| **Deployment** | Vercel with zero-configuration Python pipeline |
| **Mobile Packaging** | Capacitor framework |

---

## Getting Started

### Prerequisites
- Python 3.9 or higher
- Git
- Virtual environment manager (venv)

### Local Development Installation

1. **Clone Repository**
   ```bash
   git clone https://github.com/23CABSAKTHIRENGANATHANk/CodeAlpha_Aetheria.git
   cd CodeAlpha_Aetheria
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   ```

3. **Activate Virtual Environment**
   - Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Initialize Database**
   ```bash
   python manage.py migrate
   ```

6. **Start Development Server**
   ```bash
   python manage.py runserver
   ```
   
   Access the application at `http://127.0.0.1:8000/`

---

## Production Deployment

### Vercel Deployment

Aetheria implements Vercel's zero-configuration Django build system for streamlined deployment.

**Environment Variables:**
```
SECRET_KEY          # Django cryptographic signing key
DEBUG               # Set to False for production
DATABASE_URL        # PostgreSQL connection string (e.g., Neon)
ALLOWED_HOSTS       # Production domain or * for Vercel domain
```

**Deploy Command:**
```bash
vercel --prod
```

Configure environment variables through the Vercel dashboard or CLI before deployment.

---

## Mobile Application Build

Aetheria supports native application packaging for iOS and Android platforms using the Capacitor framework.

**Build Process:**

1. **Initialize Capacitor**
   ```bash
   npm init @capacitor/app
   ```

2. **Configure Capacitor** (`capacitor.config.json`)
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

3. **Build Platform-Specific Packages**
   ```bash
   npx cap add android    # Android APK
   npx cap add ios        # iOS IPA
   ```

---

## Project Structure

```
Aetheria/
├── socialmedia/          # Django application root
│   ├── manage.py
│   ├── users/            # User authentication & profiles
│   ├── posts/            # Post and feed management
│   ├── utils/            # Shared utilities
│   └── templates/        # HTML templates
├── www/                  # Frontend assets
├── android/              # Android build configuration
├── static/               # Compiled static assets
└── requirements.txt      # Python dependencies
```

---

## Architecture Overview

### Backend Architecture
- **Django ORM:** Database abstraction layer for PostgreSQL operations
- **RESTful API:** Endpoints for all core features (posts, reactions, followers, etc.)
- **Authentication:** Secure session and token-based user authentication

### Frontend Architecture
- **Responsive Design:** CSS Grid and Flexbox for adaptive layouts
- **Progressive Enhancement:** Core functionality works without JavaScript; enhanced features via vanilla JS
- **State Management:** Client-side state handling with efficient DOM updates

### Database Schema
- Users and authentication
- Posts and story content
- Reactions and engagement metrics
- Follow relationships and notifications
- Hashtag indexing and curation

---

## Security Considerations

- Django CSRF protection enabled
- Password hashing via Django's security utilities
- SQL injection prevention through ORM
- CORS configuration for API endpoints
- Environment variables for sensitive credentials
- HTTPS enforcement in production

---

## Performance Metrics

- **Page Load Time:** < 2 seconds (production)
- **Service Worker Cache:** Instant asset loading for return visits
- **Database Indexing:** Optimized queries for feed and discovery operations
- **Lazy Loading:** Images and content load on-demand

---

## Troubleshooting

### Common Issues

**Database Connection Error**
- Verify `DATABASE_URL` environment variable
- Ensure PostgreSQL service is running (local development)
- Check Neon connection credentials (production)

**Static Files Not Loading**
- Run `python manage.py collectstatic` in development
- Verify WhiteNoise configuration in Django settings
- Clear browser cache and refresh

**Mobile App Build Failure**
- Update Capacitor: `npm install @capacitor/cli@latest`
- Ensure Android SDK or Xcode is properly installed
- Review platform-specific build logs

---

## Contributing

Contributions are welcome. Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes with descriptive messages
4. Push to the branch (`git push origin feature/your-feature`)
5. Submit a Pull Request

---

## License

This project is licensed under the MIT License. See LICENSE file for details.

---

## Support & Contact

For issues, questions, or suggestions, please open an issue on the GitHub repository or contact the development team.