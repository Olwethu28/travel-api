# Travel Itinerary Planning & Booking API

A Django REST Framework API for discovering destinations, creating travel itineraries, collaborating on trips, managing bookings, tracking budgets and expenses, and publishing reviews.

Developed as part of the **Umuzi Advanced Web Development Programme**.

## Features

* Custom user accounts and JWT authentication
* Destination discovery with filtering, searching, ordering and pagination
* Travel itinerary creation and management
* Daily trip planning and activity scheduling
* Collaborative itinerary management with role-based permissions
* Accommodation and activity bookings
* Budget and expense tracking
* Destination, accommodation and activity reviews
* Trip reports and analytics
* File and image uploads
* Query optimization using Django ORM techniques
* Automated testing and coverage
* OpenAPI, Swagger UI and ReDoc documentation

## Technologies

* Python
* Django 4.2
* Django REST Framework
* Simple JWT
* django-filter
* drf-spectacular
* python-decouple
* Pillow
* SQLite / PostgreSQL
* pytest and pytest-django
* Coverage.py

## Project Structure

```text
travel-api/
├── accounts/       # Users, authentication and preferences
├── destinations/   # Destination catalogue and search
├── itineraries/    # Trips, daily plans and collaboration
├── bookings/       # Accommodation, activities and bookings
├── reviews/        # Travel reviews
├── budgets/        # Budgets and expenses
├── config/         # Django settings, URLs and configuration
├── docs/            # ERD documentation
├── tests/           # Automated tests
├── manage.py
├── requirements.txt
├── pytest.ini
└── README.md
```

The database contains models for users, destinations, itineraries, collaborations, daily plans, accommodations, activities, bookings, reviews, budgets and expenses. Relationships include `OneToOneField`, `ForeignKey`, `ManyToManyField`, and a custom through model.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Olwethu28/travel-api.git
cd travel-api
```

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file using `.env.example` as a template.

Required settings include:

```text
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=
TIME_ZONE=UTC
```

Do not commit the `.env` file or real secrets to Git.

### 5. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the server

```bash
python manage.py runserver
```

The API is available at:

```text
http://127.0.0.1:8000/api/v1/
```

## Authentication

The API uses JWT authentication.

Register:

```http
POST /api/v1/accounts/register/
```

Login:

```http
POST /api/v1/accounts/login/
```

Token endpoints:

```http
POST /api/v1/token/
POST /api/v1/token/refresh/
POST /api/v1/token/verify/
```

Authenticated requests use:

```http
Authorization: Bearer <access-token>
```

Object-level permissions protect resources such as itineraries, bookings and reviews. Collaboration roles include viewer, editor and administrator access.

## Main API Endpoints

| Resource       | Base Endpoint             |
| -------------- | ------------------------- |
| Accounts       | `/api/v1/accounts/`       |
| Destinations   | `/api/v1/destinations/`   |
| Itineraries    | `/api/v1/itineraries/`    |
| Accommodations | `/api/v1/accommodations/` |
| Activities     | `/api/v1/activities/`     |
| Bookings       | `/api/v1/bookings/`       |
| Reviews        | `/api/v1/reviews/`        |
| Budgets        | `/api/v1/budgets/`        |
| Expenses       | `/api/v1/expenses/`       |
| Analytics      | `/api/v1/analytics/`      |

Example destination search:

```http
GET /api/v1/destinations/?search=Cape&ordering=avg_daily_cost
```

Example itinerary creation:

```json
{
  "title": "Cape Town Adventure",
  "destination": 1,
  "start_date": "2027-01-10",
  "end_date": "2027-01-15",
  "budget": 10000
}
```

## API Documentation

OpenAPI schema:

```text
/api/schema/
```

Swagger UI:

```text
/api/docs/
```

ReDoc:

```text
/api/redoc/
```

## Testing

Run the test suite with:

```bash
pytest
```

Run tests using Django:

```bash
python manage.py test
```

Run coverage:

```bash
coverage run -m pytest
coverage report
```

Validate the Django project and OpenAPI schema:

```bash
python manage.py check
python manage.py spectacular --validate --file schema.yml
```

## Query Optimization

The API uses `select_related`, `prefetch_related`, custom `Prefetch` querysets, `only`, `defer`, `annotate`, `aggregate`, `F` expressions and `Q` objects to reduce unnecessary database queries and perform calculations efficiently.

## ERD

The entity relationship diagram is available in:

```text
docs/ERD.png
docs/ERD.dot
```

## Author

**Olwethu Manqola**

Umuzi Advanced Web Development Programme
