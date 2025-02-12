from django.contrib import admin
from .models import UserProfile

# Register your models here.
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')  # Show role in the list view
    search_fields = ('user__username', 'role')  # Allow search by role
    list_filter = ('role',)  # Filter by role

admin.site.register(UserProfile, UserProfileAdmin)
