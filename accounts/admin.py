from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ActivityLog, User, UserPreference

admin.site.register(User, UserAdmin)
admin.site.register(UserPreference)
admin.site.register(ActivityLog)
