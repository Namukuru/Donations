from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
ROLE_CHOICES = [
    ('donor', 'Donor'),
    ('recipient', 'Recipient'),
    ('agent', 'Agent'),
    ]
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=10, choices = ROLE_CHOICES, default='donor')
    created_at = models.DateTimeField(auto_now_add=True)
     
    def __str__(self):
        return (f"{self.user.username}'s Profile")

class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Link to User model
    city = models.CharField(max_length=100)  # City where agent operates
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username

class Donation(models.Model):
    DONATION_TYPES = [
        ("monetary", "Monetary"),
        ("in_kind", "In-Kind"),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    ]

    donation_type = models.CharField(max_length=20, choices=DONATION_TYPES)
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)

    # Monetary Donation Fields
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # In-Kind Donation Fields
    item_name = models.CharField(max_length=255, blank=True, null=True, default="Money")
    item_quantity = models.PositiveIntegerField(blank=True, null=True)
    item_description = models.TextField(blank=True, null=True)

    # Pickup Details
    pickup_location = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_donations')

    def __str__(self):
        return f"{self.donation_type} ({self.item_quantity or 'N/A'} x {self.item_name}) - {self.donor.username if self.donor else 'Anonymous'}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if this is a new donation
        super().save(*args, **kwargs)  # Save the donation first

        # Automatically assign an agent if available
        if is_new and self.donation_type == "in_kind" and self.pickup_location and not self.assigned_agent:
            from .models import Agent  # Import here to avoid circular imports
            available_agent = Agent.objects.first()  # You can modify this logic for better agent selection
            if available_agent:
                self.assigned_agent = available_agent.user
                self.status = 'in_progress'  # Update status when assigned
                super().save(update_fields=['assigned_agent', 'status'])

