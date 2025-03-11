# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Donation, Agent

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'User Profiles'

class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('id','username', 'email', 'get_role', 'is_staff', 'get_created_at')
    list_select_related = ('userprofile',)

    def get_role(self, instance):
        return instance.userprofile.role
    get_role.short_description = 'Role'
    
    def get_created_at(self, instance):
        return instance.userprofile.created_at if instance.userprofile else "N/A"
    get_created_at.short_description = "Created At"
    
@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ('id', 'donor', 'amount','message','pickup_location', 'created_at','item_name','item_description','item_quantity','assigned_agent')  # Columns displayed in the list view
    list_filter = ('created_at',)  # Adds a filter on the right side
    search_fields = ('donor_name',)  # Enables search by donor name
    ordering = ('-created_at',)  # Orders by most recent donations first
    readonly_fields = ('created_at',)  # Prevents editing the timestamp
    
# Unregister the default User admin and register the custom one
admin.site.unregister(User)
admin.site.register(Agent)
admin.site.register(User, CustomUserAdmin)
