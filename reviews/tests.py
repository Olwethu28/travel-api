from datetime import date
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import serializers
from rest_framework.test import APIClient
from destinations.models import Destination
from bookings.models import Accommodation, Activity
from .models import Review
from .serializers import ReviewSerializer


User = get_user_model()


class ReviewSerializerTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="Password123!",
        )

        self.destination = Destination.objects.create(
            name="Cape Town",
            country="South Africa",
            description="A beautiful coastal city.",
            category="city",
            climate="mediterranean",
            best_time_to_visit="October to March",
            avg_daily_cost=1500,
            latitude=-33.9249,
            longitude=18.4241,
        )

        self.accommodation = Accommodation.objects.create(
            name="Cape Town Hotel",
            destination=self.destination,
            accommodation_type="hotel",
            description="A comfortable hotel.",
            price_per_night=1200,
            max_guests=2,
            address="Cape Town",
            contact_email="hotel@example.com",
            contact_phone="0211234567",
        )

        self.activity = Activity.objects.create(
            name="Table Mountain Hike",
            destination=self.destination,
            category="adventure",
            description="A mountain hiking experience.",
            duration_hours=4,
            price=500,
            max_participants=10,
        )

        self.review = Review.objects.create(
            user=self.user,
            destination=self.destination,
            rating=5,
            title="Amazing!",
            content="I really enjoyed my visit.",
            visit_date=date(2026, 1, 15),
        )

    def test_review_serializer(self):
        serializer = ReviewSerializer(self.review)

        self.assertEqual(serializer.data["rating"], 5)
        self.assertEqual(serializer.data["title"], "Amazing!")
        self.assertEqual(
            serializer.data["content"],
            "I really enjoyed my visit.",
        )

    def test_review_serializer_includes_target_name(self):
        serializer = ReviewSerializer(self.review)

        self.assertEqual(
            serializer.data["target_name"],
            "Cape Town",
        )

    def test_review_serializer_includes_helpful_count(self):
        serializer = ReviewSerializer(self.review)

        self.assertEqual(
            serializer.data["helpful_count"],
            0,
        )

    def test_valid_review_can_be_created(self):
        data = {
            "destination": self.destination.id,
            "rating": 4,
            "title": "Great place",
            "content": "I had a great experience.",
            "visit_date": "2026-02-10",
            "images": "",
        }

        serializer = ReviewSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_rating_is_rejected(self):
        data = {
            "destination": self.destination.id,
            "rating": 6,
            "title": "Bad rating",
            "content": "This rating should fail.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("rating", serializer.errors)

    def test_review_requires_a_target(self):
        data = {
            "rating": 5,
            "title": "No target",
            "content": "This review has no target.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_review_rejects_multiple_targets(self):
        data = {
            "destination": self.destination.id,
            "accommodation": self.accommodation.id,
            "rating": 5,
            "title": "Multiple targets",
            "content": "This should fail.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("non_field_errors", serializer.errors)

    def test_review_can_target_accommodation(self):
        data = {
            "accommodation": self.accommodation.id,
            "rating": 4,
            "title": "Nice hotel",
            "content": "The hotel was comfortable.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_review_can_target_activity(self):
        data = {
            "activity": self.activity.id,
            "rating": 5,
            "title": "Great activity",
            "content": "The hike was amazing.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rating_lower_boundary_is_valid(self):
        data = {
            "destination": self.destination.id,
            "rating": 1,
            "title": "Low rating",
            "content": "Testing the lower boundary.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rating_upper_boundary_is_valid(self):
        data = {
            "destination": self.destination.id,
            "rating": 5,
            "title": "High rating",
            "content": "Testing the upper boundary.",
            "visit_date": "2026-02-10",
        }

        serializer = ReviewSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)


class ReviewViewTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            username="reviewuser",
            email="review@example.com",
            password="testpass123",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )

        self.destination = Destination.objects.create(
            name="Cape Town",
            country="South Africa",
            description="A beautiful destination.",
            category="city",
            climate="temperate",
            best_time_to_visit="Summer",
            avg_daily_cost=1000,
            latitude=-33.9249,
            longitude=18.4241,
        )

        self.review = Review.objects.create(
            user=self.user,
            destination=self.destination,
            rating=5,
            title="Amazing destination",
            content="I really enjoyed my visit.",
            visit_date=date(2026, 1, 15),
        )

        self.list_url = "/api/reviews/"
        self.detail_url = f"/api/reviews/{self.review.id}/"

    def test_authenticated_user_can_create_review(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.list_url,
            {
                "destination": self.destination.id,
                "rating": 4,
                "title": "Great place",
                "content": "I had a great experience.",
                "visit_date": "2026-02-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Review.objects.count(), 2)

        new_review = Review.objects.latest("id")

        self.assertEqual(new_review.user, self.user)
        self.assertEqual(new_review.destination, self.destination)

    def test_unauthenticated_user_cannot_create_review(self):
        response = self.client.post(
            self.list_url,
            {
                "destination": self.destination.id,
                "rating": 4,
                "title": "Great place",
                "content": "I had a great experience.",
                "visit_date": "2026-02-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)


    def test_anyone_can_list_reviews(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_anyone_can_retrieve_review(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Amazing destination")

    def test_owner_can_update_review(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            self.detail_url,
            {
                "rating": 4,
                "title": "Updated review",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.review.refresh_from_db()

        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.title, "Updated review")

    def test_non_owner_cannot_update_review(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            self.detail_url,
            {
                "rating": 1,
                "title": "Changed by someone else",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        self.review.refresh_from_db()

        self.assertEqual(self.review.rating, 5)
        self.assertEqual(
            self.review.title,
            "Amazing destination",
        )

    def test_owner_can_delete_review(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Review.objects.filter(id=self.review.id).exists()
        )

    def test_non_owner_cannot_delete_review(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(self.detail_url)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Review.objects.filter(id=self.review.id).exists()
        )