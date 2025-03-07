from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from .forms import SignUpForm, DonationForm
from .models import UserProfile, Donation, Job, Agent
from django.db import models
from .utils import get_address_from_coordinates 
from django.core.cache import cache

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
            return redirect('account')
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
    
def report(request):
    # Fetch all donations efficiently (avoid multiple DB hits)
    donations = Donation.objects.select_related('donor')

    # Aggregate total monetary donations
    total_donations = donations.filter(donation_type="monetary").aggregate(total=Sum('amount'))['total'] or 0

    # Count unique donors
    number_of_donors = donations.values('donor').distinct().count()

    # Donations per donor (optimized query)
    donations_per_donor = donations.filter(donation_type="monetary").values('donor__username').annotate(total_donated=Sum('amount'))

    # Fetch in-kind donations and prevent N+1 queries
    in_kind_donations = donations.filter(donation_type="in_kind").select_related('donor')

    # Cache addresses to avoid repeated calls
    for donation in in_kind_donations:
        cache_key = f"pickup_address_{donation.id}"
        pickup_address = cache.get(cache_key)

        if not pickup_address:
            if donation.pickup_location:
                pickup_address = get_address_from_coordinates(donation.pickup_location)
            else:
                pickup_address = "No pickup location provided"
            cache.set(cache_key, pickup_address, timeout=86400)  # Cache for 1 day

        donation.pickup_address = pickup_address  # Attach cached address

    # Context for rendering
    context = {
        'total_donations': total_donations,
        'number_of_donors': number_of_donors,
        'donations_per_donor': donations_per_donor,
        'in_kind_donations': in_kind_donations,  # pickup_address is cached
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
        
        print(f"Assigning job {job_id} to agent {agent_id}")  # Debugging statement

        job = get_object_or_404(Job, id=job_id)  # Get job from database
        agent = get_object_or_404(Agent, id=agent_id)

        # Assign agent to the job
        job.assigned_agent = agent.user
        job.status = 'pending'
        job.save()

        messages.success(request, f"Agent {agent.user.username} assigned to job {job_id}")
        return redirect("admin_dashboard")

def unassign_agent(request):
    if request.method == "POST":
        job_id = request.POST.get('job_id')
        
        job = get_object_or_404(Job, id=job_id)

        job.assigned_agent = None
        job.status = 'unassigned'
        job.save()

        messages.success(request, f"Agent unassigned from job {job_id}")
        return redirect("admin_dashboard")

@login_required
def admin_dashboard(request):
    unassigned_jobs = Job.objects.filter(assigned_agent__isnull=True)
    assigned_jobs = Job.objects.filter(assigned_agent__isnull=False)
    agents = Agent.objects.all()
    
    # Pass both original and formatted addresses to the template
    unassigned_jobs_data = []
    assigned_jobs_data = []

    for job in unassigned_jobs:
        unassigned_jobs_data.append({
            "id": job.id,
            "donor_name": job.donor_name,
            "pickup_address": job.pickup_address,  # Original coordinates
            "formatted_address": get_address_from_coordinates(job.pickup_address),  # Converted address
            "donation_items": job.donation_items,
        })

    for job in assigned_jobs:
        assigned_jobs_data.append({
            "id": job.id,
            "donor_name": job.donor_name,
            "pickup_address": job.pickup_address,  # Original coordinates
            "formatted_address": get_address_from_coordinates(job.pickup_address),  # Converted address
            "donation_items": job.donation_items,
            "assigned_agent": job.assigned_agent,
            "status": job.status,
        })

    context = {
        "unassigned_jobs": unassigned_jobs_data,
        "assigned_jobs": assigned_jobs_data,
        "agents": agents,
    }
    return render(request, "admin.html", context)