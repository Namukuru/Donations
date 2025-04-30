from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, F, Sum, Case, When,Count
from django.contrib.auth import get_user_model
from django.urls import reverse
from math import radians, sin, cos, sqrt, atan2
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

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
    is_available = models.BooleanField(default=True)
    id_number = models.PositiveIntegerField(
        default=100000,  
        validators=[
            MinValueValidator(100000),        
            MaxValueValidator(999999999999)   
        ]
    )
    
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
        return f"{self.user.get_full_name() or self.user.username}"
    
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

    # Core Fields
    donation_type = models.CharField(max_length=20, choices=DONATION_TYPES)
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='donations_made')
    date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message = models.TextField(blank=True, null=True)
    
    # Monetary Fields
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD', blank=True)

    # In-Kind Fields
    item_name = models.CharField(max_length=255, blank=True, null=True, default="Money")
    item_quantity = models.PositiveIntegerField(blank=True, null=True, default=1)
    item_description = models.TextField(blank=True, null=True)
    item_condition = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        choices=[('new', 'New'), ('used', 'Used'), ('refurbished', 'Refurbished')]
    )

    # Location Fields
    pickup_location = models.CharField(max_length=255, blank=True, null=True)
    pickup_latitude = models.FloatField(blank=True, null=True)
    pickup_longitude = models.FloatField(blank=True, null=True)
    preferred_pickup_time = models.DateTimeField(blank=True, null=True)

    # Assignment Fields
    assigned_agent = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_donations'
    )
    assigned_recipient = models.ForeignKey(
        'Recipient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_donations'
    )
    assignment_date = models.DateTimeField(null=True, blank=True)

    # Fulfillment Fields
    fulfillment_notes = models.TextField(blank=True, null=True)
    fulfillment_date = models.DateTimeField(null=True, blank=True)
    fulfillment_percentage = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['donation_type']),
            models.Index(fields=['assigned_recipient']),
        ]

    def __str__(self):
        return f"{self.get_donation_type_display()} ({self.item_quantity}x {self.item_name})"

    def get_absolute_url(self):
        return reverse('donation_detail', args=[str(self.id)])

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            self._process_new_donation()

    def _process_new_donation(self):
        """Handle new donation processing"""
        if self.donation_type == "in_kind":
            if not self.assigned_agent:
                self._assign_agent()
        
        if not self.assigned_recipient:
            self.assign_to_recipient()

    def _assign_agent(self):
        """Assign the most appropriate agent"""
        from .models import Agent
        
        agents = Agent.objects.filter(
            is_available=True,
            user__is_active=True
        ).annotate(
            current_load=Count('user__assigned_donations', 
                            filter=Q(user__assigned_donations__status='in_progress'))
        ).order_by('current_load')

        if agents.exists():
            self.assigned_agent = agents.first().user
            self.status = 'in_progress'
            self.save(update_fields=['assigned_agent', 'status'])

    def assign_to_recipient(self, force=False):
        """Main allocation method"""
        if self.assigned_recipient and not force:
            return False

        if self.donation_type == "monetary":
            return self._assign_monetary()
        return self._assign_in_kind()

    def _assign_monetary(self):
        """Allocate monetary donations"""
        from .models import Recipient

        recipient = Recipient.objects.annotate(
            financial_need=Sum(
                Case(
                    When(needs__category__in=['food', 'shelter', 'medical'],
                        then=F('needs__quantity_needed')-F('needs__quantity_received')),
                    default=0,
                    output_field=models.FloatField()
                )
            )
        ).filter(
            financial_need__gt=0
        ).order_by(
            '-priority_score',
            '-financial_need'
        ).first()

        if recipient:
            self._finalize_assignment(recipient)
            return True
        return False

    def _assign_in_kind(self):
        """Allocate in-kind donations"""
        from .models import Need

        # Try exact name match first
        needs = self._find_matching_needs(exact_match=True)
        if not needs.exists():
            # Fall back to category match
            needs = self._find_matching_needs(exact_match=False)

        # Apply location filter if available
        if self.pickup_latitude and self.pickup_longitude:
            needs = [n for n in needs if self._is_within_distance(n.recipient)]

        # Assign to highest priority need
        for need in needs:
            if need.remaining_need > 0:
                self._finalize_assignment(need.recipient)
                self._update_need_fulfillment(need)
                return True
        return False

    def _find_matching_needs(self, exact_match=True):
        """Find needs matching the donation item"""
        from .models import Need

        filter_field = 'name__iexact' if exact_match else 'category__iexact'
        return Need.objects.filter(
            **{filter_field: self.item_name},
            is_fulfilled=False,
            quantity_received__lt=F('quantity_needed')
        ).select_related('recipient').order_by(
            '-recipient__priority_score',
            '-priority'
        )

    def _is_within_distance(self, recipient, max_km=50):
        """Check if recipient is within acceptable distance using Haversine formula"""
        if not (recipient.location_latitude and recipient.location_longitude):
            return False
            
        if not (self.pickup_latitude and self.pickup_longitude):
            return False
            
        try:
            # Convert coordinates from degrees to radians
            lat1 = radians(float(self.pickup_latitude))
            lon1 = radians(float(self.pickup_longitude))
            lat2 = radians(float(recipient.location_latitude))
            lon2 = radians(float(recipient.location_longitude))

            # Haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            
            # Earth radius in kilometers
            EARTH_RADIUS = 6371
            distance = EARTH_RADIUS * c
            
            return distance <= max_km
        except (TypeError, ValueError):
            return False

    def _finalize_assignment(self, recipient):
        """Complete assignment process"""
        self.assigned_recipient = recipient
        self.assignment_date = timezone.now()
        self.status = 'in_progress'
        self.save()
        
        # Update recipient
        recipient.last_received = timezone.now()
        recipient.save()
        recipient.update_priority_score()

    def _update_need_fulfillment(self, need):
        """Update need status after assignment"""
        need.quantity_received = min(
            need.quantity_needed,
            need.quantity_received + (self.item_quantity or 1)
        )
        need.save()
        
        # Update donation fulfillment
        self.fulfillment_percentage = int((need.quantity_received / need.quantity_needed) * 100)
        if need.quantity_received < need.quantity_needed:
            self.status = 'partially_fulfilled'
        else:
            need.is_fulfilled = True
            need.save()
        self.save()

    def complete(self, notes=None):
        """Mark donation as completed"""
        self.status = 'completed'
        self.fulfillment_notes = notes
        self.fulfillment_date = timezone.now()
        self.save()
        
        if self.assigned_recipient:
            self.assigned_recipient.update_priority_score()

    def cancel(self, reason=None):
        """Cancel the donation"""
        self.status = 'canceled'
        self.fulfillment_notes = reason
        self.save()

    @property
    def is_assigned(self):
        return bool(self.assigned_agent and self.assigned_recipient)

    @property
    def matching_criteria(self):
        return {
            'type': self.donation_type,
            'item': self.item_name,
            'quantity': self.item_quantity,
            'location': {
                'address': self.pickup_location,
                'coordinates': (self.pickup_latitude, self.pickup_longitude)
            },
            'time': self.preferred_pickup_time
        }
        

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
        

class DonationCompletionPhoto(models.Model):
    donation = models.ForeignKey(Donation, on_delete=models.CASCADE, related_name='completion_photos')
    
    def upload_to_path(instance, filename):
        date_str = timezone.now().strftime('%Y-%m-%d')
        return f'donation_completion_photos/{instance.donation.id}_{date_str}_{filename}'
    
    photo = models.ImageField(upload_to=upload_to_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    caption = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Photo for {self.donation} - {self.uploaded_at}"