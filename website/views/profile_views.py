from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Agent, Recipient
from ..forms import ProfileUpdateForm
from ..utils import get_address_from_coordinates

@login_required
def profile(request):
    user = request.user
    agent = Agent.objects.filter(user=user).first()
    recipient = Recipient.objects.filter(user=user).first()

    # Convert location to address for agent and recipient (if they have a location)
    agent_address = None
    recipient_address = None

    if agent and agent.location:
        agent_address = get_address_from_coordinates(agent.location)
    
    if recipient and recipient.location:
        recipient_address = get_address_from_coordinates(recipient.location)
    
    context = {
        'agent': agent,
        'recipient': recipient,
        'user': user,
        'agent_address': agent_address,
        'recipient_address': recipient_address,
    }
    
    return render(request, 'profile.html', context)


@login_required
def edit_profile(request):
    user = request.user
    agent = getattr(user, 'agent', None)
    recipient = getattr(user, 'recipient', None)

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            if agent:
                agent.phone = request.POST.get("phone", agent.phone)
                agent.location = request.POST.get("location", agent.location)
                agent.save()
            elif recipient:
                recipient.phone_number = request.POST.get("phone_number", recipient.phone_number)
                recipient.population = request.POST.get("population", recipient.population)
                recipient.urgency_level = request.POST.get("urgency_level", recipient.urgency_level)
                recipient.location = request.POST.get("location", recipient.location)
                recipient.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, "edit_profile.html", {
        "form": form,
        "agent": agent,
        "recipient": recipient,
        "user": user
    })
