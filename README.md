# Assignment 2 — Django Backend Service

A persistent REST API backend built with Django and Django REST Framework, featuring full CRUD operations, token-based authentication, and pagination.

---

## Tech Stack

- Python 3
- Django 6.1
- Django REST Framework 3.18
- SQLite (default database)

---

## Project Structure

```
Assignment2_Django/
├── backend/              # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── api/                  # Main application
│   ├── models.py         # Document, QueryLog, UserSession
│   ├── serializers.py    # Input/output validation
│   ├── views.py          # Endpoint logic
│   ├── urls.py           # Route definitions
│   ├── pagination.py     # StandardPagination (default 10/page)
│   ├── admin.py          # Admin panel registrations
│   └── tests.py          # 51 unit + integration tests
├── manage.py
└── requirements.txt
```

---

## Setup

**1. Create and activate virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

**2. Install dependencies**
```bash
pip install django djangorestframework
```

**3. Apply migrations**
```bash
python manage.py migrate
```

**4. Run the server**
```bash
python manage.py runserver
```

Server runs at `http://127.0.0.1:8000`

---

## Models

| Model | Fields |
|-------|--------|
| `Document` | id, title, content, uploaded_at, owner |
| `QueryLog` | id, query_text, result_summary, created_at, user |
| `UserSession` | id, user, token, created_at, expires_at |

---

## API Endpoints

### Authentication

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/register` | No | Create a new user account |
| POST | `/login` | No | Login and retrieve token |

**Register request body:**
```json
{
    "username": "alice",
    "password": "pass1234",
    "email": "alice@example.com"
}
```

**Register / Login response:**
```json
{
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "username": "alice"
}
```

---

### Documents

All document endpoints require the token in the Authorization header:
```
Authorization: Token <your_token>
```

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/documents` | Create a document (JSON or file upload) |
| GET | `/documents` | List your documents (paginated) |
| GET | `/documents/{id}` | Get a single document |
| DELETE | `/documents/{id}` | Delete a document |

**POST /documents — JSON body:**
```json
{
    "title": "My Document",
    "content": "Document content here"
}
```

**POST /documents — File upload (multipart/form-data):**
```
file: <file>
title: Optional title (defaults to filename)
```

File constraints:
- Maximum size: **5 MB** (returns `413` if exceeded)
- Allowed types: `text/plain`, `application/pdf`, `application/json`

**GET /documents — Paginated response:**
```json
{
    "count": 45,
    "next": "http://127.0.0.1:8000/documents?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "title": "My Document",
            "content": "Document content here",
            "uploaded_at": "2026-11-24T08:00:00Z",
            "owner": "alice"
        }
    ]
}
```

Pagination query params: `?page=2&page_size=25` (max page_size: 100)

**Status codes:**

| Code | Meaning |
|------|---------|
| 201 | Document created |
| 204 | Document deleted |
| 403 | Forbidden — not the owner (DELETE) |
| 404 | Not found or not owned by requester (GET) |
| 413 | File too large |

---

### Queries

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/query` | Log a query |
| GET | `/queries` | List your query history (paginated) |

**POST /query request body:**
```json
{
    "query_text": "What is machine learning?"
}
```

**POST /query response (201):**
```json
{
    "id": 1,
    "query_text": "What is machine learning?",
    "result_summary": "",
    "created_at": "2026-11-24T08:00:00Z",
    "user": "alice"
}
```

---

## Running Tests

```bash
# Activate venv first
source venv/bin/activate

# Run all tests
python manage.py test api

# Run with verbose output
python manage.py test api --verbosity=2

# Run with coverage report
coverage run --source=api manage.py test api
coverage report

# Run a specific test class
python manage.py test api.tests.DocumentDetailTest
```

**Test coverage: 99%** across 51 tests covering models, serializers, and all endpoints.

---

## Admin Panel

Create a superuser to access the Django admin at `/admin`:

```bash
python manage.py createsuperuser
```
