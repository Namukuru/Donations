from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Agent, Recipient

#  Signal to create UserProfile automatically when a User is created


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # Get the role and location from the User instance (set in the view)
        role = getattr(instance, 'role', 'donor')
        location = getattr(instance, 'location', '')
        UserProfile.objects.create(user=instance, role=role)

        # If the user is an agent, create an Agent record (if it doesn't already exist)
        if role == 'agent':
            agent,_ = Agent.objects.get_or_create(user=instance, defaults={'location': location})
            agent.location = location  # Ensure location is set
            agent.save()  # Save changes

# Signal to update Agent table if role is changed to 'agent'
@receiver(post_save, sender=UserProfile)
def create_agent(sender, instance, **kwargs):
    if instance.role == 'agent':
        Agent.objects.get_or_create(user=instance.user)
    else:
        # If the role is changed from 'agent' to something else, delete the Agent record
        Agent.objects.filter(user=instance.user).delete()

@receiver(post_save, sender=User)
def create_recipient_profile(sender, instance, created, **kwargs):
    if created and instance.role == "recipient":
        Recipient.objects.create(
            user=instance,
            location=instance.location,
            population=getattr(instance, 'population', None),  # Ensure population is set
            phone_number=getattr(instance, 'phone_number', None)  # Ensure phone_number is set
        )