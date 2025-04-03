from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from ..models import Agent, Recipient
from ..forms import ProfileUpdateForm

@login_required
def profile(request):
    user = request.user
    context = {
        'agent': Agent.objects.filter(user=user).first(),
        'recipient': Recipient.objects.filter(user=user).first(),
        'user': user,
    }
    return render(request, 'profile.html', context)

@login_required
def edit_profile(request):
    user = request.user
    agent = getattr(user, 'agent', None)

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            if agent:
                agent.phone = request.POST.get("phone", agent.phone)
                agent.location = request.POST.get("location", agent.location)
                agent.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, "edit_profile.html", {"form": form, "agent": agent, "user": user})
