from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .forms import  DonationForm
from .models import UserProfile, Donation, Agent
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
    return render(request, 'donate.html')

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
        'donations': donations,
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
    """ Show jobs assigned to the logged-in agent """
    if not request.user.is_authenticated:
        return render(request, "error.html", {"message": "You must be logged in."})

    # Retrieve assigned donations based on User, not Agent
    assigned_donations = Donation.objects.filter(assigned_agent=request.user)

    return render(request, "jobs.html", {"assigned_donations": assigned_donations})

def assign_agent(request):
    if request.method == "POST":
        donation_id = request.POST.get('job_id')
        agent_id = request.POST.get('agent_id')

        # Debugging: Print values to check if they're being received correctly
        print(f"Donation ID: {donation_id}, Agent ID: {agent_id}")

        # Check if donation_id is valid
        if not donation_id:
            messages.error(request, "Invalid donation ID.")
            return redirect("admin_dashboard")

        # Fetch donation object
        donation = get_object_or_404(Donation, id=donation_id)

        # Fetch agent object
        if agent_id:
            agent = get_object_or_404(Agent, id=agent_id)
            donation.assigned_agent = agent.user  # Assign agent's user
            donation.status = "assigned"
        else:
            donation.assigned_agent = None
            donation.status = "unassigned"

        donation.save()
        messages.success(request, f"Donation {donation.id} assigned successfully.")
        return redirect("admin_dashboard")

    return redirect("admin_dashboard")

def unassign_agent(request):
    if request.method == "POST":
        donation_id = request.POST.get('donation_id')
        
        donation = get_object_or_404(Donation, id=donation_id)

        donation.assigned_agent = None
        donation.status = 'pending'  # Change status back to pending
        donation.save(update_fields=['assigned_agent', 'status'])

        messages.success(request, f"Agent unassigned from donation {donation_id}")
        return redirect("admin_dashboard")

@login_required
def admin_dashboard(request):
    # Get donations that are in-kind and unassigned
    unassigned_donations = Donation.objects.filter(donation_type="in_kind", assigned_agent__isnull=True)
    assigned_donations = Donation.objects.filter(donation_type="in_kind", assigned_agent__isnull=False)

    # Convert donations into structured data for the template
    unassigned_donations_data = [
        {
            "id": donation.id,
            "donor_name": donation.donor.username if donation.donor else "Anonymous",
            "pickup_address": donation.pickup_location,  # Original address (assumed not to be coordinates)
            "formatted_address": get_address_from_coordinates(donation.pickup_location) if donation.pickup_location else "N/A",
            "donation_items": f"{donation.item_quantity or 1}x {donation.item_name}",
        }
        for donation in unassigned_donations
    ]

    assigned_donations_data = [
        {
            "id": donation.id,
            "donor_name": donation.donor.username if donation.donor else "Anonymous",
            "pickup_address": donation.pickup_location,
            "formatted_address": get_address_from_coordinates(donation.pickup_location) if donation.pickup_location else "N/A",
            "donation_items": f"{donation.item_quantity or 1}x {donation.item_name}",
            "assigned_agent": donation.assigned_agent.username if donation.assigned_agent else "Unassigned",
            "status": donation.status,
        }
        for donation in assigned_donations
    ]

    context = {
        "unassigned_donations": unassigned_donations_data,
        "assigned_donations": assigned_donations_data,
        "agents": Agent.objects.all(),
    }
    return render(request, "admin.html", context)