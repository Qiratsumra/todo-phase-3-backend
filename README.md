# Todo Chatbot - Backend API

A FastAPI-powered backend with AI chatbot capabilities using Gemini API for intelligent task management.

## Features

- 🚀 **Fast REST API** - FastAPI with async support
- 🤖 **AI Chatbot** - Gemini-powered conversational interface
- 📝 **Task Management** - Full CRUD operations with advanced features
- 🔒 **Rate Limiting** - User-level request throttling
- 📊 **API Monitoring** - Usage tracking and quota management
- 🗄️ **PostgreSQL Database** - Robust data persistence with SQLAlchemy
- 🎯 **Skill-Based Routing** - Modular AI agent architecture
- 🛡️ **Error Handling** - Graceful degradation with fallback messages

## Tech Stack

- **Framework:** FastAPI 0.115.6
- **Python:** 3.11
- **Database:** PostgreSQL 16 with SQLAlchemy 2.0.36
- **AI:** Gemini API (via OpenAI SDK compatibility)
- **Server:** Uvicorn 0.34.0
- **Rate Limiting:** slowapi 0.1.9
- **Validation:** Pydantic

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 16 or higher
- Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Quick Start

### 1. Clone and Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements-prod.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your configuration
```

**Required environment variables:**

```env
# Database Configuration
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=app
DB_USER=postgres

# OR use full connection string:
SQLALCHEMY_DATABASE_URL=postgresql://user:pass@host:port/database

# AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Server Configuration
PORT=8000
LOG_LEVEL=info
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

### 3. Start PostgreSQL

**Option A: Using Docker**
```bash
docker run --name postgres-dev \
  -e POSTGRES_PASSWORD=your_secure_password \
  -e POSTGRES_DB=app \
  -p 5432:5432 \
  -d postgres:16-alpine
```

**Option B: Using Docker Compose** (from project root)
```bash
cd ..
docker-compose up -d postgres
```

### 4. Run the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at: **http://localhost:8000**

### 5. Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"ok","service":"todo-backend"}

# Check API documentation
open http://localhost:8000/docs
```

## Project Structure

```
backend/
├── agents/                  # AI Agent System
│   ├── main_agent.py       # Intent routing
│   ├── agent_config.py     # Gemini API setup
│   └── skills/             # Specialized agent skills
│       ├── task_management.py
│       ├── task_search.py
│       ├── task_analytics.py
│       └── task_recommendation.py
├── routes/                 # API Routes
│   └── chat.py            # Chat endpoints
├── mcp_tools/             # Model Context Protocol tools
│   ├── add_task.py
│   ├── list_tasks.py
│   ├── complete_task.py
│   └── tool_definitions.py
├── utils/                 # Utilities
│   ├── api_monitor.py    # API usage tracking
│   └── error_handler.py  # Error handling
├── config/                # Configuration
│   └── settings.py       # App settings
├── main.py               # FastAPI application entry
├── models.py             # SQLAlchemy models
├── schemas.py            # Pydantic schemas
├── service.py            # Task CRUD service
├── database.py           # Database connection
├── limiter.py            # Rate limiting config
└── logging_config.py     # Logging setup
```

## API Endpoints

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (for Kubernetes probes) |
| GET | `/` | Root health check with rate limiting |
| GET | `/api/status` | System status and API health |
| GET | `/api/admin/stats` | Detailed usage statistics |

### Tasks API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks` | Create a new task |
| GET | `/api/tasks` | List all tasks |
| GET | `/api/tasks/{task_id}` | Get specific task |
| PATCH | `/api/tasks/{task_id}` | Update task (partial) |
| PUT | `/api/tasks/{task_id}` | Update task (full replace) |
| DELETE | `/api/tasks/{task_id}` | Delete task |

### Chat API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/conversations/{user_id}` | Create conversation |
| GET | `/api/conversations/{user_id}` | List user conversations |
| GET | `/api/conversations/{conversation_id}/messages` | Get conversation messages |
| POST | `/api/chat/{user_id}` | Send chat message |
| DELETE | `/api/conversations/{conversation_id}` | Delete conversation |

### API Documentation

- **Interactive Docs:** http://localhost:8000/docs (Swagger UI)
- **ReDoc:** http://localhost:8000/redoc (Alternative documentation)
- **OpenAPI JSON:** http://localhost:8000/openapi.json

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PASSWORD` | **Required** | PostgreSQL password |
| `DB_HOST` | localhost | Database host |
| `DB_PORT` | 5432 | Database port |
| `DB_NAME` | app | Database name |
| `DB_USER` | postgres | Database user |
| `SQLALCHEMY_DATABASE_URL` | - | Full connection string (overrides above) |
| `GEMINI_API_KEY` | **Required** | Gemini API key |
| `PORT` | 8000 | Server port |
| `LOG_LEVEL` | info | Logging level (debug, info, warning, error) |
| `BACKEND_CORS_ORIGINS` | ["http://localhost:3000"] | Allowed CORS origins (JSON array) |
| `BACKEND_RATE_LIMIT` | 5/minute | Rate limit configuration |
| `ENABLE_FALLBACK` | true | Enable fallback messages |
| `FALLBACK_MODE` | smart | Fallback mode (smart/simple) |
| `RATE_LIMIT_REQUESTS` | 5 | Max requests per window |
| `RATE_LIMIT_WINDOW` | 120 | Rate limit window (seconds) |
| `MAX_TOKENS_PER_REQUEST` | 500 | Max tokens per AI request |

### Rate Limiting

Configure rate limits in `.env`:

```env
BACKEND_RATE_LIMIT=5/minute
RATE_LIMIT_REQUESTS=5
RATE_LIMIT_WINDOW=120
```

### CORS Configuration

Configure allowed origins in `.env`:

```env
# Single origin
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Multiple origins
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://your-frontend.com"]
```

## Database Schema

### Conversations
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Messages
```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id),
    user_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    skill_used VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Tasks
```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    description TEXT,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    priority VARCHAR,
    tags TEXT[],
    due_date TIMESTAMP,
    recurrence_pattern VARCHAR,
    next_recurrence_date TIMESTAMP,
    recurrence_start_date TIMESTAMP,
    recurrence_end_date TIMESTAMP,
    reminder_time TIMESTAMP
);
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Docker

### Build Image

```bash
docker build -t todo-backend:latest .
```

### Run Container

```bash
docker run -d \
  --name todo-backend \
  -p 8000:8000 \
  -e DB_PASSWORD=your_password \
  -e GEMINI_API_KEY=your_key \
  todo-backend:latest
```

### Docker Compose

From project root:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

## Kubernetes Deployment

### Using Helm

```bash
# From project root
cd helm-charts

# Install backend
helm install todo-backend ./todo-backend \
  --set secrets.databaseUrl="postgresql://..." \
  --set secrets.geminiApiKey="your-key" \
  --namespace todo-app \
  --create-namespace

# Check status
kubectl get pods -n todo-app

# View logs
kubectl logs -n todo-app -l app.kubernetes.io/name=todo-backend -f
```

### Health Checks

The backend includes health endpoints for Kubernetes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
psql -h localhost -U postgres -d app

# Check logs
docker logs postgres-dev
```

### API Key Issues

```bash
# Verify key is set
echo $GEMINI_API_KEY

# Test key directly
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  https://generativelanguage.googleapis.com/v1beta/models
```

### Rate Limit Errors

If you see `429 Too Many Requests`:
- Increase `RATE_LIMIT_REQUESTS` in `.env`
- Increase `RATE_LIMIT_WINDOW` for longer periods
- Check API quota at Google AI Studio

### Import Errors

```bash
# Ensure all dependencies installed
pip install -r requirements-prod.txt

# Reinstall from scratch
pip install --force-reinstall -r requirements-prod.txt
```

## Security

⚠️ **IMPORTANT:** Read [SECURITY.md](../SECURITY.md) before deploying to production.

- Never commit `.env` files
- Rotate API keys regularly
- Use strong database passwords
- Configure CORS properly (no wildcards)
- Enable HTTPS in production
- Implement authentication middleware

## Performance

### Optimization Tips

1. **Database:**
   - Enable connection pooling
   - Add indexes on frequently queried columns
   - Use database read replicas for scaling

2. **API:**
   - Enable response caching
   - Use async operations where possible
   - Optimize database queries

3. **Deployment:**
   - Use Horizontal Pod Autoscaler in Kubernetes
   - Configure resource limits appropriately
   - Enable gzip compression

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is part of the AI Hackathon Phase 4.

## Support

For issues and questions:
- Check the [SECURITY.md](../SECURITY.md) for security concerns
- Review [PROJECT_COMPLETION_REPORT.md](../PROJECT_COMPLETION_REPORT.md) for deployment details
- Open an issue on GitHub

---

**Last Updated:** 2025-12-26
**Version:** 1.0.0
**Status:** ✅ Production Ready (with security fixes applied)
