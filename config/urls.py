from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/accounts/", include("accounts.urls")),
    path("api/", include("destinations.urls")),
    path("api/", include("itineraries.urls")),
    path("api/", include("bookings.urls")),
    path("api/", include("budgets.urls")),
    path("api/", include("reviews.urls")),
]