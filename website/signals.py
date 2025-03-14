from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Agent

#  Signal to create UserProfile automatically when a User is created


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Get the role from the User instance (set in the view)
        role = getattr(instance, 'role', 'donor')
        UserProfile.objects.create(user=instance, role=role)

        # If the user is an agent, create an Agent record (if it doesn't already exist)
        if role == 'agent':
            Agent.objects.get_or_create(user=instance)


# Signal to update Agent table if role is changed to 'agent'
@receiver(post_save, sender=UserProfile)
def create_agent(sender, instance, **kwargs):
    if instance.role == 'agent':
        Agent.objects.get_or_create(user=instance.user)
    else:
        # If the role is changed from 'agent' to something else, delete the Agent record
        Agent.objects.filter(user=instance.user).delete()
