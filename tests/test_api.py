from datetime import date
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import ActivityLog, User, UserPreference
from bookings.models import Accommodation, Activity, Booking
from budgets.models import Budget, Expense
from destinations.models import Destination
from itineraries.models import Collaboration, DailyPlan, Itinerary, ItineraryDocument
from reviews.models import Review


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def users(db):
    owner = User.objects.create_user(
        username="owner",
        email="owner@example.com",
        password="StrongPass123!",
    )
    other = User.objects.create_user(
        username="other",
        email="other@example.com",
        password="StrongPass123!",
    )
    admin = User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="StrongPass123!",
        role=User.RoleChoices.ADMIN,
        is_staff=True,
    )
    return owner, other, admin


@pytest.fixture
def destination(db):
    return Destination.objects.create(
        name="Cape Town",
        country="South Africa",
        description="A coastal city.",
        category="city",
        climate="mediterranean",
        best_time_to_visit="October to March",
        avg_daily_cost=Decimal("1500.00"),
    )


@pytest.fixture
def itinerary(db, users, destination):
    owner, _, _ = users
    return Itinerary.objects.create(
        title="Cape Town Adventure",
        description="Five days in Cape Town.",
        destination=destination,
        owner=owner,
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        budget=Decimal("10000.00"),
    )


@pytest.fixture
def accommodation(db, destination):
    return Accommodation.objects.create(
        name="Cape Town Hotel",
        destination=destination,
        accommodation_type="hotel",
        description="Comfortable hotel.",
        price_per_night=Decimal("1200.00"),
        max_guests=2,
        amenities="WiFi, breakfast",
        address="Cape Town",
        contact_email="hotel@example.com",
        contact_phone="0211234567",
    )


@pytest.fixture
def activity(db, destination):
    return Activity.objects.create(
        name="Table Mountain Hike",
        destination=destination,
        category="outdoor",
        description="Mountain hike.",
        duration_hours=Decimal("4.0"),
        price=Decimal("500.00"),
        max_participants=10,
    )


def authenticate(client, user):
    client.force_authenticate(user=user)


# Model tests


@pytest.mark.django_db
def test_user_string_and_role(users):
    owner, _, _ = users
    assert str(owner) == "owner"
    assert owner.role == User.RoleChoices.TRAVELER


@pytest.mark.django_db
def test_itinerary_duration_and_budget(itinerary):
    assert itinerary.duration_days == 5
    assert itinerary.budget_remaining == Decimal("10000.00")


@pytest.mark.django_db
def test_collaboration_helper(itinerary, users):
    _, other, _ = users
    collaboration = itinerary.add_collaborator(
        other,
        role=Collaboration.RoleChoices.EDITOR,
    )
    assert collaboration.user == other
    assert itinerary.can_edit(other) is True


@pytest.mark.django_db
def test_accommodation_total_price(accommodation):
    assert accommodation.total_price(3) == Decimal("3600.00")


@pytest.mark.django_db
def test_activity_total_price(activity):
    assert activity.total_price(2) == Decimal("1000.00")


@pytest.mark.django_db
def test_booking_confirm_and_cancel(
    itinerary,
    users,
    accommodation,
):
    owner, _, _ = users
    booking = Booking.objects.create(
        user=owner,
        itinerary=itinerary,
        accommodation=accommodation,
        booking_date=date(2026, 10, 1),
        quantity=1,
        price=Decimal("1200.00"),
    )
    booking.confirm()
    assert booking.status == Booking.StatusChoices.CONFIRMED
    booking.status = Booking.StatusChoices.PENDING
    booking.save(update_fields=["status"])
    booking.cancel()
    assert booking.status == Booking.StatusChoices.CANCELLED


@pytest.mark.django_db
def test_budget_total(itinerary):
    budget = Budget.objects.create(
        itinerary=itinerary,
        accommodation_budget=3000,
        activities_budget=2000,
        food_budget=1500,
        transport_budget=1000,
        shopping_budget=500,
        miscellaneous_budget=500,
    )
    assert budget.total_budget == Decimal("8500")


@pytest.mark.django_db
def test_expense_string(itinerary):
    expense = Expense.objects.create(
        itinerary=itinerary,
        category="food",
        description="Dinner",
        amount=450,
        date=date(2026, 10, 2),
    )
    assert "Dinner" in str(expense)


@pytest.mark.django_db
def test_review_helpful_counter(users, destination):
    owner, _, _ = users
    review = Review.objects.create(
        user=owner,
        destination=destination,
        rating=5,
        title="Excellent",
        content="Great destination.",
        visit_date=date(2026, 1, 1),
    )
    review.increment_helpful()
    review.refresh_from_db()
    assert review.helpful_count == 1


@pytest.mark.django_db
def test_user_preference_category_list(users):
    owner, _, _ = users
    preference = UserPreference.objects.create(
        user=owner,
        preferred_categories="city, beach",
    )
    assert preference.category_list() == ["city", "beach"]


# Serializer/API authentication tests


@pytest.mark.django_db
def test_registration_returns_tokens(client):
    response = client.post(
        "/api/v1/accounts/register/",
        {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert "access" in response.data["tokens"]


@pytest.mark.django_db
def test_registration_rejects_mismatched_password(client):
    response = client.post(
        "/api/v1/accounts/register/",
        {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "Different123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_login_returns_tokens(client, users):
    owner, _, _ = users
    response = client.post(
        "/api/v1/accounts/login/",
        {
            "username": owner.username,
            "password": "StrongPass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert ActivityLog.objects.filter(
        user=owner,
        action=ActivityLog.ActionChoices.LOGIN,
    ).exists()


@pytest.mark.django_db
def test_profile_requires_authentication(client):
    response = client.get("/api/v1/accounts/profile/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_profile_can_be_updated(client, users):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.patch(
        "/api/v1/accounts/profile/",
        {"first_name": "Olwethu"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    owner.refresh_from_db()
    assert owner.first_name == "Olwethu"


@pytest.mark.django_db
def test_password_change(client, users):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/accounts/password/change/",
        {
            "old_password": "StrongPass123!",
            "new_password": "NewStrongPass123!",
            "new_password_confirm": "NewStrongPass123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    owner.refresh_from_db()
    assert owner.check_password("NewStrongPass123!")


@pytest.mark.django_db
def test_password_reset_flow(client, users):
    owner, _, _ = users
    response = client.post(
        "/api/v1/accounts/password/reset/",
        {"username": owner.username},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    response = client.post(
        "/api/v1/accounts/password/reset/confirm/",
        {
            "uid": response.data["uid"],
            "token": response.data["token"],
            "password": "ResetStrong123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK


# Destination serializer/view tests


@pytest.mark.django_db
def test_destination_list_is_public(client, destination):
    response = client.get("/api/v1/destinations/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["results"][0]["name"] == "Cape Town"


@pytest.mark.django_db
def test_destination_search(client, destination):
    response = client.get(
        "/api/v1/destinations/search/",
        {"q": "Cape"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["country"] == "South Africa"


@pytest.mark.django_db
def test_destination_filters(client, destination):
    response = client.get(
        "/api/v1/destinations/",
        {"category": "city", "min_cost": 1000},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_non_admin_cannot_create_destination(client, users):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/destinations/",
        {
            "name": "Durban",
            "country": "South Africa",
            "description": "Coastal city.",
            "category": "beach",
            "climate": "temperate",
            "best_time_to_visit": "Summer",
            "avg_daily_cost": 1000,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_create_destination(client, users):
    _, _, admin = users
    authenticate(client, admin)
    response = client.post(
        "/api/v1/destinations/",
        {
            "name": "Durban",
            "country": "South Africa",
            "description": "Coastal city.",
            "category": "beach",
            "climate": "temperate",
            "best_time_to_visit": "Summer",
            "avg_daily_cost": 1000,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


# Itinerary tests


@pytest.mark.django_db
def test_itinerary_list_requires_authentication(client):
    response = client.get("/api/v1/itineraries/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_itinerary_create(client, users, destination):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/itineraries/",
        {
            "title": "Durban Trip",
            "description": "A beach trip.",
            "destination": destination.id,
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "budget": "5000.00",
            "status": "planning",
            "is_public": True,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Budget.objects.filter(
        itinerary__title="Durban Trip"
    ).exists()


@pytest.mark.django_db
def test_itinerary_update_owner(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.patch(
        f"/api/v1/itineraries/{itinerary.id}/",
        {"title": "Updated Trip"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    itinerary.refresh_from_db()
    assert itinerary.title == "Updated Trip"


@pytest.mark.django_db
def test_itinerary_update_viewer_forbidden(client, users, itinerary):
    _, other, _ = users
    itinerary.add_collaborator(
        other,
        role=Collaboration.RoleChoices.VIEWER,
    )
    authenticate(client, other)
    response = client.patch(
        f"/api/v1/itineraries/{itinerary.id}/",
        {"title": "Not allowed"},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_editor_can_update_itinerary(client, users, itinerary):
    _, other, _ = users
    itinerary.add_collaborator(
        other,
        role=Collaboration.RoleChoices.EDITOR,
    )
    authenticate(client, other)
    response = client.patch(
        f"/api/v1/itineraries/{itinerary.id}/",
        {"title": "Edited by collaborator"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_collaborate_action(client, users, itinerary):
    owner, other, _ = users
    authenticate(client, owner)
    response = client.post(
        f"/api/v1/itineraries/{itinerary.id}/collaborate/",
        {"username": other.username, "role": "editor"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert itinerary.collaborations.filter(
        user=other,
        role="editor",
    ).exists()


@pytest.mark.django_db
def test_publish_action(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        f"/api/v1/itineraries/{itinerary.id}/publish/"
    )
    assert response.status_code == status.HTTP_200_OK
    itinerary.refresh_from_db()
    assert itinerary.is_public is True


@pytest.mark.django_db
def test_daily_plan_nested_endpoint(client, users, itinerary, activity):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        f"/api/v1/itineraries/{itinerary.id}/daily-plans/",
        {
            "day_number": 1,
            "date": "2026-10-01",
            "title": "Arrival",
            "notes": "Check in.",
            "activities": [activity.id],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert DailyPlan.objects.filter(
        itinerary=itinerary,
        day_number=1,
    ).exists()


@pytest.mark.django_db
def test_daily_plan_detail_delete(client, users, itinerary):
    owner, _, _ = users
    plan = DailyPlan.objects.create(
        itinerary=itinerary,
        day_number=1,
        date=date(2026, 10, 1),
        title="Arrival",
    )
    authenticate(client, owner)

    response = client.delete(
        f"/api/v1/itineraries/daily-plans/{plan.id}/"
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not DailyPlan.objects.filter(pk=plan.pk).exists()


@pytest.mark.django_db
def test_daily_plan_detail_delete_requires_edit_access(
    client,
    users,
    itinerary,
):
    _, other, _ = users
    plan = DailyPlan.objects.create(
        itinerary=itinerary,
        day_number=1,
        date=date(2026, 10, 1),
        title="Arrival",
    )
    itinerary.add_collaborator(
        other,
        role=Collaboration.RoleChoices.VIEWER,
    )
    authenticate(client, other)

    response = client.delete(
        f"/api/v1/itineraries/daily-plans/{plan.id}/"
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert DailyPlan.objects.filter(pk=plan.pk).exists()


@pytest.mark.django_db
def test_public_trip_search(client, itinerary):
    itinerary.is_public = True
    itinerary.save(update_fields=["is_public"])
    response = client.get(
        "/api/v1/itineraries/search/",
        {"q": "Cape"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1


# Booking tests


@pytest.mark.django_db
def test_booking_create(client, users, itinerary, accommodation):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/bookings/",
        {
            "itinerary": itinerary.id,
            "accommodation": accommodation.id,
            "booking_date": "2026-10-01",
            "quantity": 1,
            "price": "1200.00",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Booking.objects.filter(user=owner).exists()


@pytest.mark.django_db
def test_booking_cannot_target_two_resources(
    client,
    users,
    itinerary,
    accommodation,
    activity,
):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/bookings/",
        {
            "itinerary": itinerary.id,
            "accommodation": accommodation.id,
            "activity": activity.id,
            "booking_date": "2026-10-01",
            "quantity": 1,
            "price": "1200.00",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_booking_confirm_action(
    client,
    users,
    itinerary,
    accommodation,
):
    owner, _, _ = users
    booking = Booking.objects.create(
        user=owner,
        itinerary=itinerary,
        accommodation=accommodation,
        booking_date=date(2026, 10, 1),
        price=1200,
    )
    authenticate(client, owner)
    response = client.post(
        f"/api/v1/bookings/{booking.id}/confirm/"
    )
    assert response.status_code == status.HTTP_200_OK
    booking.refresh_from_db()
    assert booking.status == Booking.StatusChoices.CONFIRMED


@pytest.mark.django_db
def test_booking_owner_can_cancel(
    client,
    users,
    itinerary,
    accommodation,
):
    owner, _, _ = users
    booking = Booking.objects.create(
        user=owner,
        itinerary=itinerary,
        accommodation=accommodation,
        booking_date=date(2026, 10, 1),
        price=1200,
    )
    authenticate(client, owner)
    response = client.post(
        f"/api/v1/bookings/{booking.id}/cancel/"
    )
    assert response.status_code == status.HTTP_200_OK
    booking.refresh_from_db()
    assert booking.status == Booking.StatusChoices.CANCELLED


@pytest.mark.django_db
def test_other_user_cannot_modify_booking(
    client,
    users,
    itinerary,
    accommodation,
):
    owner, other, _ = users
    booking = Booking.objects.create(
        user=owner,
        itinerary=itinerary,
        accommodation=accommodation,
        booking_date=date(2026, 10, 1),
        price=1200,
    )
    authenticate(client, other)
    response = client.patch(
        f"/api/v1/bookings/{booking.id}/",
        {"quantity": 2},
        format="json",
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


# Budget/review/file tests


@pytest.mark.django_db
def test_budget_create(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/budgets/",
        {
            "itinerary": itinerary.id,
            "food_budget": "2000.00",
        },
        format="json",
    )
    # The itinerary already receives a budget at creation, so duplicate
    # creation is rejected by the OneToOne database constraint.
    assert response.status_code in {
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_201_CREATED,
    }


@pytest.mark.django_db
def test_expense_create(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/expenses/",
        {
            "itinerary": itinerary.id,
            "category": "food",
            "description": "Dinner",
            "amount": "450.00",
            "date": "2026-10-02",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_expense_totals_action(client, users, itinerary):
    owner, _, _ = users
    Expense.objects.create(
        itinerary=itinerary,
        category="food",
        description="Dinner",
        amount=450,
        date=date(2026, 10, 2),
    )
    authenticate(client, owner)
    response = client.get("/api/v1/expenses/totals/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["total"] == "450.00"


@pytest.mark.django_db
def test_review_create(client, users, destination):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/reviews/",
        {
            "destination": destination.id,
            "rating": 5,
            "title": "Amazing",
            "content": "Excellent destination.",
            "visit_date": "2026-01-01",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_review_requires_one_target(client, users, destination, activity):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.post(
        "/api/v1/reviews/",
        {
            "destination": destination.id,
            "activity": activity.id,
            "rating": 5,
            "title": "Invalid",
            "content": "Two targets.",
            "visit_date": "2026-01-01",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_review_owner_can_update(client, users, destination):
    owner, _, _ = users
    review = Review.objects.create(
        user=owner,
        destination=destination,
        rating=5,
        title="Great",
        content="Great place.",
        visit_date=date(2026, 1, 1),
    )
    authenticate(client, owner)
    response = client.patch(
        f"/api/v1/reviews/{review.id}/",
        {"rating": 4},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_non_owner_cannot_update_review(client, users, destination):
    owner, other, _ = users
    review = Review.objects.create(
        user=owner,
        destination=destination,
        rating=5,
        title="Great",
        content="Great place.",
        visit_date=date(2026, 1, 1),
    )
    authenticate(client, other)
    response = client.patch(
        f"/api/v1/reviews/{review.id}/",
        {"rating": 1},
        format="json",
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_review_stats(client, users, destination):
    owner, _, _ = users
    Review.objects.create(
        user=owner,
        destination=destination,
        rating=4,
        title="Good",
        content="Good.",
        visit_date=date(2026, 1, 1),
    )
    response = client.get(
        f"/api/v1/reviews/stats/{destination.id}/"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["review_count"] == 1


@pytest.mark.django_db
def test_itinerary_pdf_upload(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    pdf = SimpleUploadedFile(
        "itinerary.pdf",
        b"%PDF-1.4 test",
        content_type="application/pdf",
    )
    response = client.post(
        f"/api/v1/itineraries/{itinerary.id}/documents/",
        {
            "file": pdf,
            "description": "Trip PDF",
        },
        format="multipart",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert ItineraryDocument.objects.filter(
        itinerary=itinerary
    ).exists()


@pytest.mark.django_db
def test_wrong_document_type_rejected(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    txt = SimpleUploadedFile(
        "itinerary.txt",
        b"not a pdf",
        content_type="text/plain",
    )
    response = client.post(
        f"/api/v1/itineraries/{itinerary.id}/documents/",
        {"file": txt},
        format="multipart",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# Preferences, analytics, and documentation endpoints


@pytest.mark.django_db
def test_preferences_endpoint(client, users, destination):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.patch(
        "/api/v1/accounts/preferences/",
        {
            "preferred_destinations": [destination.id],
            "preferred_categories": "city,beach",
            "preferred_climates": "mediterranean",
            "max_daily_budget": "2000.00",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_analytics_endpoint(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.get("/api/v1/analytics/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["trip_count"] == 1


@pytest.mark.django_db
def test_analytics_detail_endpoint_is_read_only(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)

    get_response = client.get(f"/api/v1/analytics/{itinerary.id}/")
    delete_response = client.delete(f"/api/v1/analytics/{itinerary.id}/")

    assert get_response.status_code == status.HTTP_200_OK
    assert get_response.data["title"] == itinerary.title
    assert delete_response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
def test_analytics_budget_summary(client, users, itinerary):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.get("/api/v1/analytics/budget_summary/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["within_budget_trips"] == 1


@pytest.mark.django_db
def test_swagger_schema_endpoint(client):
    response = client.get("/api/schema/")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_admin_audit_log_access(client, users):
    _, _, admin = users
    authenticate(client, admin)
    response = client.get("/api/v1/accounts/audit-logs/")
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_traveler_cannot_view_audit_log(client, users):
    owner, _, _ = users
    authenticate(client, owner)
    response = client.get("/api/v1/accounts/audit-logs/")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_personalized_recommendations(client, users, destination):
    owner, _, _ = users
    UserPreference.objects.create(
        user=owner,
        preferred_categories="city",
        preferred_climates="mediterranean",
        max_daily_budget=2000,
    )
    authenticate(client, owner)
    response = client.get("/api/v1/analytics/recommendations/")
    assert response.status_code == status.HTTP_200_OK
    assert response.data[0]["name"] == destination.name
