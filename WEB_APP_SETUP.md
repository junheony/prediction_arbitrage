# 🚀 Web Application Setup Guide

## 📋 Overview

This guide will help you set up the full-stack web application with:
- **Backend**: FastAPI (Python) with JWT authentication
- **Frontend**: React (Vite + Tailwind CSS)
- **Database**: SQLite (development) / PostgreSQL (production)
- **Real-time**: WebSocket for live arbitrage opportunities

---

## 🏗️ Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   React SPA     │─────▶│  FastAPI API    │─────▶│  Kalshi/Opinion │
│   (Frontend)    │◀─────│   (Backend)     │◀─────│    WebSockets   │
└─────────────────┘ HTTP  └─────────────────┘      └─────────────────┘
         │                         │
         │ WebSocket               │
         └─────────────────────────┘
                  Live Updates
```

---

## 🚀 Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your API credentials

# Run the backend
python main.py
```

Backend will start at: http://localhost:8000
API Docs: http://localhost:8000/docs

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will start at: http://localhost:3000

### 3. Create Your Account

1. Open http://localhost:3000
2. Click "Sign up"
3. Create an account with email/username/password
4. Login and start using the bot!

---

## 🐳 Docker Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Create .env file with your credentials
cp .env.production .env
nano .env

# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

Access the app at: http://localhost:3000

### Option 2: Separate Docker Containers

```bash
# Backend
docker build -f Dockerfile.backend -t arbitrage-backend .
docker run -p 8000:8000 --env-file .env arbitrage-backend

# Frontend
docker build -f Dockerfile.frontend -t arbitrage-frontend .
docker run -p 3000:80 arbitrage-frontend
```

---

## ☁️ Cloud Deployment

### Railway.app (Easiest)

1. **Sign up** at https://railway.app

2. **Deploy Backend**:
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository
   - Set root directory: `backend`
   - Add environment variables from `.env.production`
   - Railway will auto-detect Python and deploy

3. **Deploy Frontend**:
   - Create new service in same project
   - Set root directory: `frontend`
   - Add build command: `npm run build`
   - Add start command: `npx serve -s dist -p $PORT`

4. **Configure Environment**:
   - Add all environment variables
   - Generate SECRET_KEY: `openssl rand -hex 32`
   - Update FRONTEND_URL to your Railway frontend URL

### Render.com

1. **Backend (Web Service)**:
   - New Web Service
   - Connect GitHub repo
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables

2. **Frontend (Static Site)**:
   - New Static Site
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`

### DigitalOcean / AWS / GCP

Use Docker Compose with their container services:

1. Set up a VM or container service
2. Clone repository
3. Create `.env` with production values
4. Run `docker-compose up -d`
5. Configure nginx/reverse proxy for SSL

---

## 🔧 Configuration

### Backend (.env)

```bash
# Required
SECRET_KEY=your-super-secret-key-min-32-chars
DATABASE_URL=sqlite:///./arbitrage_bot.db

# API Credentials (at least one platform required)
KALSHI_EMAIL=your_email@example.com
KALSHI_PASSWORD=your_password

# Optional
OPINION_API_KEY=optional_key
POLYMARKET_API_KEY=optional_key
POLYMARKET_SECRET=optional_secret
POLYMARKET_PASSPHRASE=optional_passphrase
```

### Frontend

Frontend configuration is handled via Vite proxy in development.

For production, update `vite.config.js` if using different backend URL:

```javascript
// For custom backend URL
export default defineConfig({
  // ...
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify('https://your-backend.com')
  }
})
```

---

## 📊 Database

### SQLite (Default - Development)

SQLite is used by default. Database file: `arbitrage_bot.db`

### PostgreSQL (Production)

For production, use PostgreSQL:

```bash
# Install psycopg2
pip install psycopg2-binary

# Update .env
DATABASE_URL=postgresql://user:password@localhost:5432/arbitrage_bot
```

---

## 🔐 Security

### Generate Secure SECRET_KEY

```bash
# Method 1: OpenSSL
openssl rand -hex 32

# Method 2: Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### HTTPS/SSL

For production, always use HTTPS:

1. **Railway/Render**: Automatic HTTPS
2. **Self-hosted**: Use nginx with Let's Encrypt
3. **Cloudflare**: Free SSL/CDN

### CORS

Update `main.py` to restrict origins in production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
pytest  # Once you add tests
```

### Frontend Tests

```bash
cd frontend
npm test  # Once you add tests
```

### Manual Testing

1. **Register**: Create a new account
2. **Login**: Sign in with credentials
3. **Start Bot**: Configure and start the bot
4. **WebSocket**: Verify real-time updates work
5. **Opportunities**: Check if opportunities appear
6. **Stop Bot**: Stop and verify status updates

---

## 📱 Features

### Implemented ✅

- ✅ User authentication (JWT)
- ✅ Bot start/stop controls
- ✅ Real-time WebSocket updates
- ✅ Arbitrage opportunity tracking
- ✅ Multi-platform support (Polymarket, Kalshi, Opinion)
- ✅ Configurable parameters
- ✅ Responsive UI (mobile-friendly)
- ✅ Dashboard with statistics

### Coming Soon 🚧

- 🚧 Actual trade execution
- 🚧 Advanced matching engine with NLP
- 🚧 Email/Slack notifications
- 🚧 Historical data & charts
- 🚧 Backtesting system
- 🚧 Multi-user management
- 🚧 API rate limiting

---

## 🐛 Troubleshooting

### Backend won't start

```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill process if needed
kill -9 <PID>

# Check logs
python main.py
```

### Frontend won't start

```bash
# Clear node_modules
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### WebSocket not connecting

1. Check if backend is running
2. Verify token is valid (check browser console)
3. Check CORS settings in `main.py`
4. Verify WebSocket URL in Dashboard.jsx

### Database errors

```bash
# Delete and recreate database
rm arbitrage_bot.db
python main.py  # Will auto-create tables
```

### API credentials not working

1. Verify `.env` file exists in `backend/` directory
2. Check credentials are correct (no extra spaces)
3. Restart backend after changing `.env`

---

## 📚 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

```
POST /api/auth/register     - Register new user
POST /api/auth/login        - Login (get JWT token)
GET  /api/auth/me           - Get current user info

POST /api/bot/start         - Start arbitrage bot
POST /api/bot/stop          - Stop arbitrage bot
GET  /api/bot/status        - Get bot status
GET  /api/bot/opportunities - Get recent opportunities

WS   /ws?token=<jwt>        - WebSocket for real-time updates
```

---

## 🎯 Next Steps

1. ✅ Set up local development environment
2. ✅ Test all features locally
3. 📝 Deploy to cloud platform (Railway/Render)
4. 🔐 Configure production environment variables
5. 🌐 Set up custom domain (optional)
6. 📧 Configure notifications (future)
7. 💰 Start arbitrage trading!

---

## 💬 Support

- **GitHub Issues**: https://github.com/junheony/prediction_arbitrage/issues
- **Documentation**: See `THREE_PLATFORMS_GUIDE.md`
- **Quick Start**: See `QUICKSTART.md`

---

## 📄 License

MIT License - see LICENSE file

---

**Built with ❤️ for the prediction market arbitrage community**

Happy Trading! 🚀📈💰
