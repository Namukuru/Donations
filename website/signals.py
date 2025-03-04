from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Agent

#  Signal to create UserProfile automatically when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        user_profile = UserProfile.objects.create(user=instance)

        # If the user is an agent, create an Agent record
        if user_profile.role == 'agent':
            Agent.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()
    
# Signal to update Agent table if role is changed to 'agent'
@receiver(post_save, sender=UserProfile)
def create_agent(sender, instance, **kwargs):
    if instance.role == 'agent' and not Agent.objects.filter(user=instance.user).exists():
        Agent.objects.create(user=instance)
