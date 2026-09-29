from django.contrib import admin
from .models import Collaboration, DailyPlan, Itinerary, ItineraryDocument

admin.site.register(Itinerary)
admin.site.register(Collaboration)
admin.site.register(DailyPlan)
admin.site.register(ItineraryDocument)
