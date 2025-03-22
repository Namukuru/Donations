from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .forms import  DonationForm, ProfileUpdateForm
from .models import UserProfile, Donation, Agent, Recipient
from .utils import get_address_from_coordinates, haversine
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
            donation.donor = request.user  # Associate donation with logged-in user

            # Assign message explicitly (This prevents it from being ignored)
            donation.message = form.cleaned_data.get("message", "")
            
            # Set default status only for in-kind donations
            if donation.donation_type == "in_kind" and not donation.status:
                donation.status = 'pending'

            # Ensure correct fields are saved based on donation type
            if donation.donation_type == "monetary":
                donation.item_name = None
                donation.item_quantity = None
                donation.item_description = None
                donation.pickup_location = None  # No pickup location for monetary donations
                donation.status = None  # No status for monetary donations
            else:
                donation.amount = None  # No amount for in-kind donations

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

@login_required
def profile(request):
    user = request.user

    # Fetch agent and recipient with select_related to avoid additional queries
    agent = Agent.objects.filter(user=user).select_related('user').first()
    recipient = Recipient.objects.filter(user=user).select_related('user').first()

    # Prefetch all necessary data
    context = {
        'agent': agent,
        'recipient': recipient,
        'user': user,  # Pass the user object explicitly
    }
    return render(request, 'profile.html', context)

@login_required
def edit_profile(request):
    user = request.user
    agent = getattr(user, 'agent', None)  # Get agent if it exists

    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=user)
        if agent:
            agent.location = request.POST.get("location", agent.location)
            agent.phone = request.POST.get("phone", agent.phone)
            agent.save()

        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("profile")  # Redirect to profile page

    else:
        form = ProfileUpdateForm(instance=user)

    return render(request, "edit_profile.html", {"form": form, "agent": agent})

def account(request):
    # Fetch all donations for the logged-in user, optimizing related queries
    donations = (
        Donation.objects.filter(donor=request.user)
        .select_related("assigned_agent")  # Optimizes foreign key lookup
        .only("id", "donation_type", "amount", "created_at", "item_name", "item_quantity", "item_description", "message", "pickup_location", "assigned_agent__username")  # Fetch only necessary fields
    )

    # Separate monetary and in-kind donations efficiently
    monetary_donations = [donation for donation in donations if donation.donation_type == "monetary"]
    in_kind_donations = [donation for donation in donations if donation.donation_type == "in_kind"]

    # Convert pickup_location (coordinates) into an address efficiently
    for donation in in_kind_donations:
        donation.pickup_address = get_address_from_coordinates(donation.pickup_location) if donation.pickup_location else "No pickup location provided"

    # Calculate the total monetary donations efficiently
    total_donations = sum(donation.amount for donation in monetary_donations if donation.amount) or 0

    context = {
        "monetary_donations": monetary_donations,
        "in_kind_donations": in_kind_donations,
        "total_donations": total_donations,
    }
    return render(request, "account.html", context)

def report(request):
    # Use select_related to optimize foreign key queries
    donations = Donation.objects.select_related("donor")

    # Aggregate monetary donations in one query
    total_donations = donations.filter(donation_type="monetary").aggregate(
        total=Sum("amount")
    )["total"] or 0

    # Optimize donor count query using distinct on donor_id
    number_of_donors = donations.values("donor_id").distinct().count()

    # Fetch total donations per donor efficiently
    donations_per_donor = (
        donations.filter(donation_type="monetary")
        .values("donor__username")
        .annotate(total_donated=Sum("amount"))
    )

    # Fetch in-kind donations with donor data
    in_kind_donations = donations.filter(donation_type="in_kind").select_related("donor")

    # Cache pickup addresses to avoid repeated function calls
    for donation in in_kind_donations:
        cache_key = f"pickup_address_{donation.id}"
        pickup_address = cache.get(cache_key)

        if not pickup_address:
            pickup_address = (
                get_address_from_coordinates(donation.pickup_location)
                if donation.pickup_location
                else "No pickup location provided"
            )
            cache.set(cache_key, pickup_address, timeout=86400)  # Cache for 1 day

        donation.pickup_address = pickup_address  # Attach cached address

    context = {
        "total_donations": total_donations,
        "number_of_donors": number_of_donors,
        "donations_per_donor": donations_per_donor,
        "in_kind_donations": in_kind_donations,
    }
    return render(request, "report.html", context)

def jobs(request):
    """Show jobs assigned to the logged-in agent."""
    if not request.user.is_authenticated:
        return render(request, "error.html", {"message": "You must be logged in."})

    # Retrieve assigned donations for the logged-in agent
    assigned_donations = (
        Donation.objects.filter(assigned_agent=request.user)
        .select_related("donor")  # Optimize foreign key lookup
        .only(
            "id",
            "donation_type",
            "amount",
            "created_at",
            "item_name",
            "item_quantity",
            "item_description",
            "message",
            "pickup_location",
            "status",
            "donor__username",  # Fetch donor's username
        )
    )

    # Convert pickup_location (coordinates) into a readable address
    for donation in assigned_donations:
        donation.pickup_address = (
            get_address_from_coordinates(donation.pickup_location)
            if donation.pickup_location
            else "No pickup location provided"
        )

    # Count donations by status
    pending_jobs_count = assigned_donations.filter(status="pending").count()
    in_progress_jobs_count = assigned_donations.filter(status="in_progress").count()
    completed_jobs_count = assigned_donations.filter(status="completed").count()

    context = {
        "assigned_donations": assigned_donations,
        "pending_jobs_count": pending_jobs_count,
        "in_progress_jobs_count": in_progress_jobs_count,
        "completed_jobs_count": completed_jobs_count,
    }
    return render(request, "jobs.html", context)

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

def mark_completed(request, donation_id):
    """
    Mark a donation as completed.
    """
    # Fetch the donation object
    donation = get_object_or_404(Donation, id=donation_id)

    # Update the donation status to "completed"
    donation.status = "completed"
    donation.save()

    # Add a success message
    messages.success(request, f"Donation {donation.id} marked as completed.")

    # Redirect to the jobs page or any other page
    return redirect("jobs")  # Replace "jobs" with the appropriate URL name
@login_required
def admin_dashboard(request):
    # Optimize database queries using select_related
    unassigned_donations = Donation.objects.filter(
        donation_type="in_kind", assigned_agent__isnull=True
    ).select_related('donor', 'assigned_agent')

    assigned_donations = Donation.objects.filter(
        donation_type="in_kind", assigned_agent__isnull=False
    ).select_related('donor', 'assigned_agent')

    # Batch geocoding for pickup addresses
    pickup_locations = set()
    for donation in unassigned_donations:
        if donation.pickup_location:
            pickup_locations.add(donation.pickup_location)
    for donation in assigned_donations:
        if donation.pickup_location:
            pickup_locations.add(donation.pickup_location)

    # Cache pickup addresses
    address_map = {}
    for location in pickup_locations:
        address_map[location] = get_address_from_coordinates(location)

    # Convert donations into structured data
    unassigned_donations_data = [
        {
            "id": donation.id,
            "donor_name": donation.donor.username if donation.donor else "Anonymous",
            "pickup_address": donation.pickup_location,
            "formatted_address": address_map.get(donation.pickup_location, "N/A"),
            "donation_items": f"{donation.item_quantity or 1}x {donation.item_name}",
        }
        for donation in unassigned_donations
    ]

    assigned_donations_data = [
        {
            "id": donation.id,
            "donor_name": donation.donor.username if donation.donor else "Anonymous",
            "pickup_address": donation.pickup_location,
            "formatted_address": address_map.get(donation.pickup_location, "N/A"),
            "donation_items": f"{donation.item_quantity or 1}x {donation.item_name}",
            "assigned_agent": donation.assigned_agent.username if donation.assigned_agent else "Unassigned",
            "status": donation.status,
        }
        for donation in assigned_donations
    ]

    context = {
        "unassigned_donations": unassigned_donations_data,
        "assigned_donations": assigned_donations_data,
        "agents": Agent.objects.all().only('id', 'username'),  # Optimize agent query
    }
    return render(request, "admin.html", context)