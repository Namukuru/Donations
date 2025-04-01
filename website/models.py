from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q, F, Sum
from geopy.distance import geodesic

# Create your models here.
ROLE_CHOICES = [
    ('donor', 'Donor'),
    ('recipient', 'Recipient'),
    ('agent', 'Agent'),
    ]
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='donor')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

    def save(self, *args, **kwargs):
        """
        If the user is assigned as an agent, create an Agent entry.
        If the role changes to non-agent, delete the Agent entry.
        """
        # Check if the role is being updated
        if self.pk:  # If the profile already exists
            old_role = UserProfile.objects.get(pk=self.pk).role
            if old_role != self.role:  # Role has changed
                if old_role == 'agent':
                    Agent.objects.filter(user=self.user).delete()  # Remove old agent record
                if self.role == 'agent':
                    Agent.objects.get_or_create(user=self.user)  # Create new agent record
        else:  # New profile
            if self.role == 'agent':
                Agent.objects.get_or_create(user=self.user)  # Create agent record

        super().save(*args, **kwargs)  # Save the profile
        
class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=255, blank=True, null=True) 
    phone = models.CharField(max_length=15)

    def __str__(self):
        return f"Agent: {self.user.username}"

class Recipient(models.Model):
    URGENCY_LEVELS = (
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="recipient")
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    population = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=255, blank=True, null=True)
    urgency_level = models.PositiveSmallIntegerField(choices=URGENCY_LEVELS, default=2)
    last_received = models.DateTimeField(null=True,blank=True)
    priority_score = models.FloatField(default=0.0, editable=False)
    
    class Meta:
        ordering = ['-priority_score']
        verbose_name = "Donation Recipient"
        verbose_name_plural = "Donation Recipients"
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Population: {self.population})"
    
    def update_priority_score(self):
        """Calculate and update the priority score automatically"""
        # Days since last received (or 365 if never)
        days_since = (timezone.now() - self.last_received).days if self.last_received else 365
        
        # Base score components
        time_factor = min(days_since, 365) / 3.65  # Convert to 0-100 scale
        urgency_factor = self.urgency_level * 25    # 25, 50, 75, or 100
        population_factor = min(self.population, 10) * 5  # 5-50 based on family size
        
        # Calculate weighted score
        self.priority_score = (
            (time_factor * 0.4) +    # 40% weight to time since last
            (urgency_factor * 0.4) +  # 40% weight to urgency
            (population_factor * 0.2) # 20% weight to population
        )
        self.save()
    
    @property
    def location_coords(self):
        """Return location as tuple of (lat, lon) or None"""
        if self.location:
            try:
                return tuple(map(float, self.location.split(',')))
            except (ValueError, AttributeError):
                return None
        return None
    
    @property
    def needs_summary(self):
        """Generate a summary of needs for display"""
        needs = []
        if hasattr(self, 'needs'):
            needs.extend(self.needs.all().values_list('name', flat=True))
        return ", ".join(needs) if needs else "Not specified"


class Donation(models.Model):
    DONATION_TYPES = [
        ("monetary", "Monetary"),
        ("in_kind", "In-Kind"),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('partially_fulfilled', 'Partially Fulfilled')
    ]

    donation_type = models.CharField(max_length=20, choices=DONATION_TYPES)
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations_made')
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)

    # Monetary Donation Fields
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD', blank=True)

    # In-Kind Donation Fields
    item_name = models.CharField(max_length=255, blank=True, null=True, default="Money")
    item_quantity = models.PositiveIntegerField(blank=True, null=True, default=1)
    item_description = models.TextField(blank=True, null=True)
    item_condition = models.CharField(max_length=50, blank=True, null=True, 
                                    choices=[('new', 'New'), ('used', 'Used'), ('refurbished', 'Refurbished')])

    # Pickup/Delivery Details
    pickup_location = models.CharField(max_length=255, blank=True, null=True)
    pickup_latitude = models.FloatField(blank=True, null=True)
    pickup_longitude = models.FloatField(blank=True, null=True)
    preferred_pickup_time = models.DateTimeField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_agent = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_donations'
    )
    
    # Recipient Assignment
    assigned_recipient = models.ForeignKey(
        'Recipient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_donations',
        verbose_name="Assigned Recipient"
    )
    assignment_date = models.DateTimeField(null=True, blank=True)
    fulfillment_notes = models.TextField(blank=True, null=True)
    fulfillment_date = models.DateTimeField(null=True, blank=True)
    fulfillment_percentage = models.PositiveIntegerField(default=0, 
    help_text="Percentage of donation actually fulfilled")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['donation_type']),
            models.Index(fields=['assigned_recipient']),
        ]

    def __str__(self):
        return f"{self.get_donation_type_display()} ({self.item_quantity or 0}x {self.item_name}) - {self.donor.username if self.donor else 'Anonymous'}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        # Geocode pickup location if provided
        if is_new and self.pickup_location and not (self.pickup_latitude and self.pickup_longitude):
            self.geocode_pickup_location()

        # Assign agent for in-kind donations
        if is_new and self.donation_type == "in_kind" and self.pickup_location and not self.assigned_agent:
            self.assign_optimal_agent()

        # Assign recipient if not already assigned
        if is_new and not self.assigned_recipient:
            self.assign_to_recipient()

    def geocode_pickup_location(self):
        """Convert pickup location to coordinates"""
        # Implementation would use geopy or similar service
        # This is a placeholder for actual geocoding logic
        pass

    def assign_optimal_agent(self):
        """Find the best available agent for this donation"""
        from .models import Agent
        
        # Basic implementation - can be enhanced with location-based assignment
        available_agent = Agent.objects.filter(
            is_available=True,
            user__is_active=True
        ).order_by(
            '-current_load'  # Assign to least busy agent
        ).first()
        
        if available_agent:
            self.assigned_agent = available_agent.user
            self.status = 'in_progress'
            self.save(update_fields=['assigned_agent', 'status'])

    def assign_to_recipient(self, force=False):
        """Enhanced matching algorithm with location consideration"""
        if self.assigned_recipient and not force:
            return False

        recipient = None
        
        if self.donation_type == "monetary":
            recipient = self._assign_monetary_donation()
        else:
            recipient = self._assign_in_kind_donation()

        if recipient:
            self._finalize_assignment(recipient)
            return True
        return False

    def _assign_in_kind_donation(self):
        """Match in-kind donations with recipients' needs"""
        from .models import Need
        
        # First try exact name matches
        matching_needs = Need.objects.filter(
            Q(name__iexact=self.item_name) & 
            Q(is_fulfilled=False) &
            Q(quantity_received__lt=F('quantity_needed'))
        ).select_related('recipient').order_by(
            '-recipient__priority_score',
            '-priority'
        )
        
        # If no exact matches, try category matches
        if not matching_needs.exists():
            matching_needs = Need.objects.filter(
                Q(category__iexact=self.item_name) & 
                Q(is_fulfilled=False) &
                Q(quantity_received__lt=F('quantity_needed'))
            ).select_related('recipient').order_by(
                '-recipient__priority_score',
                '-priority'
            )
        
        # Consider location if available
        if self.pickup_latitude and self.pickup_longitude:
            matching_needs = [
                need for need in matching_needs 
                if self._is_within_distance(need.recipient)
            ]
        
        # Find the best match
        for need in matching_needs:
            if need.remaining_need > 0:
                return need.recipient
        return None

    def _is_within_distance(self, recipient, max_km=50):
        """Check if recipient is within acceptable distance"""
        if not (recipient.location_latitude and recipient.location_longitude):
            return False
            
        donor_coords = (self.pickup_latitude, self.pickup_longitude)
        recipient_coords = (recipient.location_latitude, recipient.location_longitude)
        
        return geodesic(donor_coords, recipient_coords).km <= max_km

    def _finalize_assignment(self, recipient):
        """Complete the assignment process"""
        self.assigned_recipient = recipient
        self.assignment_date = timezone.now()
        self.status = 'in_progress'
        self.save()
        
        # Update recipient records
        recipient.last_received = timezone.now()
        recipient.save()
        recipient.update_priority_score()
        
        # Update specific need if in-kind
        if self.donation_type == "in_kind":
            self._update_recipient_needs(recipient)

    def _update_recipient_needs(self, recipient):
        """Update the recipient's needs based on this donation"""
        from .models import Need
        
        try:
            need = recipient.needs.get(
                Q(name__iexact=self.item_name) | 
                Q(category__iexact=self.item_name),
                is_fulfilled=False
            )
            new_received = need.quantity_received + (self.item_quantity or 1)
            need.quantity_received = min(need.quantity_needed, new_received)
            need.save()
            
            # Calculate fulfillment percentage
            self.fulfillment_percentage = int((need.quantity_received / need.quantity_needed) * 100)
            if need.quantity_received < need.quantity_needed:
                self.status = 'partially_fulfilled'
            
            need.update_fulfillment_status()
            self.save()
        except (Need.DoesNotExist, Need.MultipleObjectsReturned):
            pass

    def complete_donation(self, notes=None, fulfillment_percentage=100):
        """Mark donation as completed with optional notes"""
        self.status = 'completed'
        self.fulfillment_notes = notes
        self.fulfillment_date = timezone.now()
        self.fulfillment_percentage = fulfillment_percentage
        self.save()
        
        if self.assigned_recipient:
            self.assigned_recipient.update_priority_score()

    def cancel_donation(self, reason=None):
        """Cancel the donation"""
        self.status = 'canceled'
        self.fulfillment_notes = reason
        self.save()

    @property
    def is_assigned(self):
        """Check if fully assigned"""
        return bool(self.assigned_agent and self.assigned_recipient)

    @property
    def matching_criteria(self):
        """Detailed matching criteria"""
        return {
            'item_name': self.item_name,
            'item_type': self.donation_type,
            'location': {
                'text': self.pickup_location,
                'coordinates': (self.pickup_latitude, self.pickup_longitude)
            },
            'quantity': self.item_quantity,
            'time_constraints': self.preferred_pickup_time,
            'condition': self.item_condition
        }

    @property
    def fulfillment_status(self):
        """Human-readable fulfillment status"""
        if self.status == 'partially_fulfilled':
            return f"Partially Fulfilled ({self.fulfillment_percentage}%)"
        return self.get_status_display()       

class Need(models.Model):
    CATEGORY_CHOICES = [
        ('food', 'Food'),
        ('clothing', 'Clothing'),
        ('shelter', 'Shelter'),
        ('medical', 'Medical'),
        ('education', 'Education'),
        ('utilities', 'Utilities'),
        ('transportation', 'Transportation'),
        ('other', 'Other'),
    ]
    
    UNIT_CHOICES = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('l', 'Liters'),
        ('items', 'Items'),
        ('boxes', 'Boxes'),
        ('hours', 'Hours'),
    ]
    
    recipient = models.ForeignKey(
        Recipient, 
        on_delete=models.CASCADE, 
        related_name='needs'
    )
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES,
        help_text="Broad category of need"
    )
    name = models.CharField(
        max_length=255,
        help_text="Specific name of needed item/service"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed description of the need"
    )
    quantity_needed = models.PositiveIntegerField(
        default=1,
        help_text="Total quantity required"
    )
    quantity_received = models.PositiveIntegerField(
        default=0,
        help_text="Quantity already received"
    )
    unit = models.CharField(
        max_length=10,
        choices=UNIT_CHOICES,
        default='items',
        help_text="Unit of measurement"
    )
    priority = models.PositiveSmallIntegerField(
        default=3,
        choices=[(1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Critical')],
        help_text="How urgently this is needed"
    )
    date_logged = models.DateTimeField(
        auto_now_add=True
    )
    last_updated = models.DateTimeField(
        auto_now=True
    )
    is_fulfilled = models.BooleanField(
        default=False,
        help_text="Mark if this need has been completely fulfilled"
    )

    class Meta:
        ordering = ['-priority', 'date_logged']
        verbose_name_plural = "Needs"

    def __str__(self):
        return f"{self.name} ({self.remaining_need}/{self.quantity_needed} {self.unit}) - {self.get_priority_display()}"

    @property
    def remaining_need(self):
        return max(0, self.quantity_needed - self.quantity_received)

    def update_fulfillment_status(self):
        """Check if need is fully fulfilled and update status"""
        if self.remaining_need <= 0 and not self.is_fulfilled:
            self.is_fulfilled = True
            self.save()
        elif self.remaining_need > 0 and self.is_fulfilled:
            self.is_fulfilled = False
            self.save()