from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ActivityLogListView,
    LoginView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    UserPreferenceView,
    UserProfileView,
)

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path(
        "password/change/",
        PasswordChangeView.as_view(),
        name="password-change",
    ),
    path(
        "password/reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "preferences/",
        UserPreferenceView.as_view(),
        name="preferences",
    ),
    path(
        "audit-logs/",
        ActivityLogListView.as_view(),
        name="audit-logs",
    ),
]
