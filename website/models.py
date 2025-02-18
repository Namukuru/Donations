from django.db import models
from django.contrib.auth.models import User

# Create your models here.
ROLE_CHOICES = [
    ('donor', 'Donor'),
    ('recipient', 'Recipient'),
    ('admin', 'Admin'),
]
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True, null=True)
    role = models.CharField(max_length=10, choices = ROLE_CHOICES, default='donor')
    created_at = models.DateTimeField(auto_now_add=True)
     
    def __str__(self):
        return (f"{self.user.username}'s Profile")

class Donation(models.Model):
    donor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Optional: Allow anonymous donations
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True, null=True)  # Optional: Allow donors to leave a message

    def __str__(self):
        return (f"Donation of ${self.amount} by {self.donor.username if self.donor else 'Anonymous'}")