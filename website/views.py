from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from .forms import SignUpForm, DonationForm
from .models import UserProfile, Donation, Job, Agent
from django.db import models
from django.db.models import Sum, Count
import requests
from django.conf import settings


def home(request):
    userprofiles = UserProfile.objects.all()
    
    # Check to see if user is logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        # User Authentication
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Log in successful!")
            return redirect('login_user')
        else:
            messages.success(request, "An error occurred. Please try again.")
            return redirect('login_user')
    else:
        return render(request, 'home.html', {'userprofiles':userprofiles})


def login_user(request):
    # Check to see if user is logging in
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        # User Authentication
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Log in successful!")
            return redirect('loginUser')
        else:
            messages.success(request, "An error occurred. Please try again.")
            return redirect('loginUser')
    else:
        return render(request, 'loginUser.html', {})


def logout_user(request):
    logout(request)
    messages.success(request, "Log out successful!")
    return redirect('home')


def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()   
              
            login(request, user)
            messages.success(request, "You have successfully registered! Welcome!")
            return redirect('home')
        else:
            print(f"DEBUG: Form errors: {form.errors}") 
            messages.error(request, "Registration failed. Please fix the errors.")
    else:
        form = SignUpForm()

    return render(request, 'register.html', {'form': form})

def donate(request):
    if request.method == 'POST':
        print(request.POST)
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user  # Associate the donation with the logged-in user

            # Ensure correct fields are saved based on donation type
            if donation.donation_type == "monetary":
                donation.item_name = None
                donation.item_quantity = None
                donation.item_description = None
                donation.pickup_location = None  # No pickup location for monetary donations
            else:
                donation.amount = None  # No amount for in-kind donations
                donation.message = None  # No message for in-kind donations

            donation.save()  # Save the donation to the database
            messages.success(request, "You have successfully made a donation")
            return redirect('home')
    else:
        form = DonationForm()
    return render(request, 'donate.html', {'form': form})

def donation_success(request):
    return render(request, 'donate.html',{'form': form})

def about(request):
    return render(request, 'about.html', {})

def account(request):
    donations = Donation.objects.filter(donor=request.user)
    
    # Separate monetary and in-kind donations
    monetary_donations = donations.filter(donation_type="monetary")
    in_kind_donations = donations.filter(donation_type="in_kind")
    
    # Convert pickup_location (coordinates) into an address
    for donation in in_kind_donations:
        if donation.pickup_location:
            donation.pickup_address = get_address_from_coordinates(donation.pickup_location)
        else:
            donation.pickup_address = "No pickup location provided"
    
    # Calculate the total donations for the logged-in user only
    total_donations = donations.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'monetary_donations': monetary_donations,
        'in_kind_donations': in_kind_donations,
        'total_donations': total_donations,
    }
    return render(request, 'account.html', context)

def get_address_from_coordinates(coordinates):
    """Convert latitude, longitude to a human-readable address using Google Maps API"""
    if not coordinates:
        return "No pickup location provided"

    lat, lng = coordinates.split(", ")
    google_maps_api_key = settings.GOOGLE_API_KEY
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={google_maps_api_key}"

    response = requests.get(url)
    data = response.json()

    if data["status"] == "OK":
        return data["results"][0]["formatted_address"]
    else:
        return "Address not found"

def report(request):
    total_donations = Donation.objects.filter(donation_type="monetary").aggregate(total=Sum('amount'))['total'] or 0
    number_of_donors = Donation.objects.values('donor').distinct().count()

    donations_per_donor = Donation.objects.filter(donation_type="monetary").values('donor__username').annotate(total_donated=Sum('amount'))
    in_kind_donations = Donation.objects.filter(donation_type="in_kind").select_related('donor')

    # Convert pickup_location (coordinates) into an address
    for donation in in_kind_donations:
        if donation.pickup_location:
            donation.pickup_address = get_address_from_coordinates(donation.pickup_location)
        else:
            donation.pickup_address = "No pickup location provided"

    context = {
        'total_donations': total_donations,
        'number_of_donors': number_of_donors,
        'donations_per_donor': donations_per_donor,
        'in_kind_donations': in_kind_donations,
    }
    return render(request, 'report.html', context)

def jobs(request):
    """View for displaying assigned jobs"""
    agent_jobs = Job.objects.filter(assigned_agent=request.user)

    for job in agent_jobs:
        if job.pickup_address:  # Convert coordinates to an address if available
            job.pickup_address = get_address_from_coordinates(job.pickup_address)
    
    return render(request, 'jobs.html', {'jobs': agent_jobs})

def assign_agent(request):
    agents = Agent.objects.filter(user__userprofile__role='agent')
    donations = Donation.objects.filter(donation_type='in_kind',status='pending')

    if request.method == "POST":
        job_id = request.POST.get('job_id')  # Get job_id from form data
        agent_id = request.POST.get('agent_id')

        job = get_object_or_404(Job, id=job_id)  # Get job from database
        agent = get_object_or_404(Agent, id=agent_id)

        # Assign agent to the job
        job.assigned_agent = agent.user
        job.status = 'in_progress'
        job.save()

        return redirect('jobs')  # Redirect to jobs list

    return render(request, 'assign_agent.html', {'agents': agents, 'donations': donations})

@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:  # Ensure only admin can access
        return redirect("home")  # Redirect non-admin users

    unassigned_jobs = Job.objects.filter(assigned_agent__isnull=True)
    assigned_jobs = Job.objects.filter(assigned_agent__isnull=False)

    context = {
        "unassigned_jobs": unassigned_jobs,
        "assigned_jobs": assigned_jobs,
    }
    return render(request, "admin.html", context)