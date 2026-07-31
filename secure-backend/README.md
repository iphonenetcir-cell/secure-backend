# Secure Backend

A secure Flask backend with admin panel and hidden API.

## Features
- 🔐 Secure admin panel with login
- 📡 Hidden API proxy
- 🛡️ Rate limiting
- 🌐 CORS configured for W3Schools
- 💾 SQLite database

## Deployment
Deployed on Render.com

## API Endpoints
- `GET /api/data` - Public data endpoint
- `GET /admin` - Admin panel
- `GET /health` - Health check
- `GET /internal/messages` - Internal API (hidden)

## Environment Variables
- `SECRET_KEY` - Flask secret key
- `ADMIN_USERNAME` - Admin username
- `ADMIN_PASSWORD` - Admin password
- `ADMIN_API_KEY` - API key for admin operations
- `ALLOWED_ORIGINS` - CORS allowed origins