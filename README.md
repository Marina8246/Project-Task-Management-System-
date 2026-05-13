# Task Management System

A RESTful API built with FastAPI for managing tasks, projects, and users with JWT authentication and role-based access control.

## Features
- JWT Authentication
- Role-Based Authorization (Admin, Project Manager, Employee)
- Redis Caching (Cache-Aside Pattern)
- Structured Logging
- Monitoring Endpoints

## Project Structure

project_fixed/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── dependencies.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── projects.py
│   │   ├── tasks.py
│   │   └── monitoring.py
│   └── services/
│       ├── task_service.py
│       └── monitoring.py
├── tests/
│   └── test_app.py
├── .env
└── README.md
LTR
## Setup Instructions

### 1. Install dependencies
```bash
pip install fastapi uvicorn sqlalchemy passlib python-jose python-multipart bcrypt pydantic[email] python-dotenv redis
```

### 2. Configure environment variables
Create a `.env` file:
SECRET_KEY=my_super_secret_key_123
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_HOST=localhost
REDIS_PORT=6379
LTR
### 3. Run the application
```bash
cd project_fixed
uvicorn app.main:app --reload
```

### 4. Run tests
```bash
pytest tests/
```

## API Endpoints

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| POST | /auth/login | Login | Public |
| POST | /auth/register-with-role | Register user | Admin |
| GET | /users/ | Get all users | Admin |
| GET | /users/me | Get current user | All |
| GET | /projects/ | Get all projects | All |
| POST | /projects/ | Create project | Manager+ |
| GET | /tasks/ | Get all tasks | Manager+ |
| POST | /tasks/ | Create task | Manager+ |
| PUT | /tasks/{id} | Update task | Employee+ |
| DELETE | /tasks/{id} | Delete task | Admin |
| GET | /monitoring/health | Health check | Public |
| GET | /monitoring/stats | Cache stats | Admin |

## Default Admin
- **Username:** admin
- **Password:** admin123
