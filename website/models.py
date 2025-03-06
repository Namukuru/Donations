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
    status = models.CharField(max_length=50, default='pending')

    def __str__(self):
        return (f"{self.amount}  {self.donor.username if self.donor else 'Anonymous'}")
    
    def save(self, *args, **kwargs):
        # Check if it's an in-kind donation and has a pickup location
        is_new = self.pk is None  # Check if this is a new donation
        super().save(*args, **kwargs)  # Save the donation first

        if is_new and self.donation_type == "in_kind" and self.pickup_location:
            Job.objects.create(
                donor_name=self.donor.username if self.donor else "Anonymous",
                pickup_address=self.pickup_location,
                donation_items=f"{self.item_quantity or 1}x {self.item_name}",
                status="pending"
            )

class Job(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    ]

    donor_name = models.CharField(max_length=100)
    pickup_address = models.TextField()
    donation_items = models.TextField()
    assigned_agent = models.ForeignKey(User, on_delete=models.CASCADE,null= True,blank=True, related_name="jobs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.donor_name} - {self.donation_items} - {self.pickup_address} ({self.get_status_display()})"
