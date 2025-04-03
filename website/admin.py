# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Donation, Agent, Recipient,Need
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

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
    list_display = ('id','donation_type_display','donor_info','amount_display','item_info','recipient_info','status_display','created_at','fulfillment_display')
    list_filter = ('status','donation_type','created_at','assigned_recipient','assigned_agent')
    search_fields = ('donor__username','donor__first_name','donor__last_name','item_name','assigned_recipient__user__username','assigned_agent__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at','updated_at','assignment_date','fulfillment_date','fulfillment_percentage')
    fieldsets = (
        ('Basic Information', {
            'fields': ('donation_type','donor','status','message')       
        }),
        ('Monetary Details', {
            'fields': (
                'amount',
                'currency'
            ),
            'classes': ('collapse',)
        }),
        ('In-Kind Details', {
            'fields': (
                'item_name',
                'item_quantity',
                'item_description',
                'item_condition'
            ),
            'classes': ('collapse',)
        }),
        ('Location Information', {
            'fields': (
                'pickup_location',
                'pickup_latitude',
                'pickup_longitude',
                'preferred_pickup_time'
            )
        }),
        ('Assignment', {
            'fields': (
                'assigned_agent',
                'assigned_recipient',
                'assignment_date'
            )
        }),
        ('Fulfillment', {
            'fields': (
                'fulfillment_notes',
                'fulfillment_date',
                'fulfillment_percentage'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    # Custom display methods
    def donation_type_display(self, obj):
        return obj.get_donation_type_display()
    donation_type_display.short_description = 'Type'
    
    def donor_info(self, obj):
        if obj.donor:
            return f"{obj.donor.get_full_name() or obj.donor.username}"
        return "Anonymous"
    donor_info.short_description = 'Donor'
    
    def amount_display(self, obj):
        if obj.donation_type == "monetary" and obj.amount:
            return f"{obj.currency} {obj.amount}"
        return "-"
    amount_display.short_description = 'Amount'
    
    def item_info(self, obj):
        if obj.donation_type == "in_kind":
            return f"{obj.item_quantity}x {obj.item_name}"
        return "-"
    item_info.short_description = 'Item'
    
    def recipient_info(self, obj):
        if obj.assigned_recipient:
            return obj.assigned_recipient.user.get_full_name() or obj.assigned_recipient.user.username
        return "Not assigned"
    recipient_info.short_description = 'Recipient'
    
    def status_display(self, obj):
        color = {
            'pending': 'orange',
            'in_progress': 'blue',
            'completed': 'green',
            'canceled': 'red',
            'partially_fulfilled': 'purple'
        }.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'status'
    
    def fulfillment_display(self, obj):
        if obj.status in ['completed', 'partially_fulfilled']:
            return f"{obj.fulfillment_percentage}%"
        return "-"
    fulfillment_display.short_description = 'Fulfillment'
    
    # Custom actions
    actions = ['mark_as_completed', 'reassign_donations']
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed', fulfillment_date=timezone.now())
        self.message_user(request, f"{updated} donations marked as completed")
    mark_as_completed.short_description = "Mark selected as completed"
    
    def reassign_donations(self, request, queryset):
        count = 0
        for donation in queryset:
            if donation.assign_to_recipient(force=True):
                count += 1
        self.message_user(request, f"Reassigned {count} donations to recipients")
    reassign_donations.short_description = "Reassign to recipients"
    
@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'phone')  # Fields to display in the list view
    search_fields = ('user__username', 'location', 'phone')  # Enable search functionality
    list_filter = ('location',)  # Add filtering by location

@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = (
        'user_info',
        'phone_number', 
        'population',
        'urgency_display',
        'needs_summary',  # Show needs summary in list view
        'location_display',
        'map_link',
        'priority_score'
    )
    
    list_filter = (
        'urgency_level',
        'needs__category',  # Add filter by need category
    )
    
    search_fields = (
        'user__username',
        'user__first_name',
        'user__last_name',
        'phone_number',
        'location',
        'needs__name',  # Search by need names
    )
    
    readonly_fields = (
        'user',
        'location_preview',
        'location_display',
        'needs_preview',  # Add needs preview to readonly fields
        'priority_score'
    )

    fieldsets = (
        (None, {
            'fields': ('user', 'phone_number', 'population', 'urgency_level')
        }),
        ('Location Information', {
            'fields': ('location', 'location_display', 'location_preview'),
            'description': 'Location in "latitude,longitude" format'
        }),
        ('Needs Information', {
            'fields': ('needs_preview', 'priority_score'),
            'classes': ('collapse',)  # Makes this section collapsible
        }),
    )

    # Existing location methods
    def user_info(self, obj):
        return f"{obj.user.get_full_name() or obj.user.username}"
    user_info.short_description = 'Recipient'
    
    def location_display(self, obj):
        return obj.location or "Not specified"
    location_display.short_description = 'Coordinates'
    
    def map_link(self, obj):
        if obj.location:
            try:
                lat, lon = obj.location.split(',')
                return format_html(
                    '<a href="https://maps.google.com/?q={},{}" target="_blank">View on Map</a>',
                    lat.strip(),
                    lon.strip()
                )
            except (ValueError, AttributeError):
                return "Invalid coordinates"
        return "No location"
    map_link.short_description = 'Map'

    def location_preview(self, obj):
        if obj.location:
            try:
                return format_html(
                    '<div style="margin-top:10px">'
                    '<p>Coordinates: <strong>{}</strong></p>'
                    '<iframe width="300" height="200" frameborder="0" style="border:0" '
                    'src="https://maps.google.com/maps?q={}&z=15&output=embed"></iframe>'
                    '</div>',
                    obj.location,
                    obj.location
                )
            except (ValueError, AttributeError):
                return "Invalid location format"
        return "No location set"
    location_preview.short_description = 'Location Preview'

    # New needs-related methods
    def needs_summary(self, obj):
        needs = obj.needs.all()[:3]  # Show first 3 needs
        items = []
        for need in needs:
            status = "✓" if need.is_fulfilled else f"{need.quantity_received}/{need.quantity_needed}"
            items.append(f"{need.name} ({status})")
        
        if obj.needs.count() > 3:
            items.append(f"...+{obj.needs.count() - 3} more")
        return format_html("<br>".join(items))
    needs_summary.short_description = 'Current Needs'

    def needs_preview(self, obj):
        needs = obj.needs.all().order_by('-priority', 'is_fulfilled')
        if not needs.exists():
            return "No needs registered"
        
        rows = []
        for need in needs:
            progress = min(100, int((need.quantity_received / need.quantity_needed) * 100)) if need.quantity_needed > 0 else 0
            rows.append(format_html(
                '<div style="margin-bottom:10px; border-bottom:1px solid #eee; padding-bottom:5px">'
                '<strong>{}</strong> ({} {})<br>'
                '<div style="background:#f0f0f0; width:100%; height:20px; position:relative">'
                '<div style="background:{}; width:{}%; height:100%;"></div>'
                '<div style="position:absolute; top:0; left:0; width:100%; text-align:center; line-height:20px;">'
                '{}% ({} of {})</div></div>'
                'Priority: {} | Category: {}'
                '</div>',
                need.name,
                need.get_unit_display(),
                "✓ Fulfilled" if need.is_fulfilled else "",
                "#4CAF50" if need.is_fulfilled else "#2196F3",
                progress,
                progress,
                need.quantity_received,
                need.quantity_needed,
                need.get_priority_display(),
                need.get_category_display()
            ))
        
        return format_html("".join(rows))
    needs_preview.short_description = 'Detailed Needs'

    def urgency_display(self, obj):
        colors = {
            1: 'green',
            2: 'blue',
            3: 'orange',
            4: 'red'
        }
        return format_html(
            '<span style="color:{}; font-weight:bold">{}</span>',
            colors.get(obj.urgency_level, 'black'),
            obj.get_urgency_level_display()
        )
    urgency_display.short_description = 'Urgency'

@admin.register(Need)
class NeedAdmin(admin.ModelAdmin):
    list_display = ('name', 'recipient', 'category', 'quantity_needed', 'quantity_received', 'unit', 'priority', 'is_fulfilled', 'date_logged')
    list_filter = ('category', 'priority', 'is_fulfilled', 'date_logged')
    search_fields = ('name', 'recipient__user__username', 'category')
    ordering = ('-priority', 'is_fulfilled', '-date_logged')
    readonly_fields = ('date_logged', 'last_updated', 'remaining_need')

    def remaining_need(self, obj):
        return obj.remaining_need
    remaining_need.short_description = "Remaining Need"
    
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

