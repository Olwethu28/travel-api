# Travel API Planning Document

## ERD
The complete ERD is provided at `docs/ERD.png` (with editable source in `docs/ERD.dot`). The main entities are User, UserPreference, Destination, Itinerary, Collaboration, DailyPlan, Accommodation, Activity, Booking, Budget, Expense, Review, ItineraryDocument and ActivityLog. Itinerary is the central trip entity. Collaboration is the through model connecting users to itineraries. DailyPlan connects itineraries to activities through a second many-to-many relationship.

## API Endpoint Plan

- `POST /api/v1/accounts/register/` — registration
- `POST /api/v1/accounts/login/` — JWT login
- `POST /api/v1/accounts/token/refresh/` — refresh token
- `GET/PATCH /api/v1/accounts/profile/` — profile
- `POST /api/v1/accounts/password/change/` — password change
- `POST /api/v1/accounts/password/reset/` — reset request
- `POST /api/v1/accounts/password/reset/confirm/` — reset confirmation
- `GET/PATCH /api/v1/accounts/preferences/` — recommendations
- `GET /api/v1/destinations/` — filtered/searchable destinations
- `CRUD /api/v1/itineraries/` — trip management
- `GET/POST /api/v1/itineraries/<id>/daily-plans/` — day planning
- `POST /api/v1/itineraries/<id>/documents/` — PDF uploads
- `CRUD /api/v1/accommodations/` — accommodation inventory
- `CRUD /api/v1/activities/` — activity inventory
- `CRUD /api/v1/bookings/` — bookings
- `CRUD /api/v1/reviews/` — reviews
- `CRUD /api/v1/budgets/` — budgets
- `CRUD /api/v1/expenses/` — expenses
- `GET /api/v1/analytics/` — trip analytics

## Authentication Flow

Registration/login returns an access and refresh JWT. The access token is sent in the Bearer Authorization header. Protected endpoints use `IsAuthenticated`. Refresh exchanges the refresh token for a new access token. Password changes require the current password. Password reset uses a uid/token confirmation flow.

## Permission Matrix

| Role | View own/shared trip | Edit trip | Collaborate | Delete trip | Manage inventory |
|---|---|---|---|---|---|
| Owner | Yes | Yes | Yes | Yes | Admin only |
| Editor | Yes | Yes | No | No | No |
| Viewer | Yes | No | No | No | No |
| Public | Public trips only | No | No | No | No |
| Admin | Yes | According to endpoint | Yes | Yes | Yes |

## URL Structure

All API endpoints use `/api/v1/`. DefaultRouter supplies CRUD routes for destinations, itineraries, accommodations, activities, bookings, budgets, expenses and analytics. Nested routes are used for itinerary daily plans and itinerary documents.

## Testing Strategy

The suite uses pytest-django with an isolated test database. Fixtures create reusable users, destinations, itineraries and booking targets. Tests cover model methods/validation, serializer validation, JWT registration/login, object and role permissions, CRUD endpoints, filtering/search, nested resources, custom actions, uploads, analytics and documentation. Coverage is enforced at 75% by `pytest.ini`.
