from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from .forms import  DonationForm, ProfileUpdateForm, NeedForm
from .models import  Donation, Agent, Recipient,Need
from .utils import get_address_from_coordinates
from django.core.cache import cache
from django.core.paginator import Paginator

def home(request):
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
            messages.error(request, "An error occurred. Please try again.")
            return redirect('login_user')
    else:
        return render(request, 'home.html')
def donate(request):
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user  # Associate donation with logged-in user

            # Handle donation type specific fields
            if donation.donation_type == "monetary":
                # Clear in-kind specific fields
                donation.item_name = "Money"  # Set default for monetary donations
                donation.item_quantity = 1
                donation.item_description = None
                donation.item_condition = None
                donation.pickup_location = None
                donation.pickup_latitude = None
                donation.pickup_longitude = None
                donation.preferred_pickup_time = None
                donation.status = 'completed'  # Monetary donations complete immediately
            else:
                # Clear monetary specific fields
                donation.amount = None
                donation.currency = 'USD'
                
                # Set default status for in-kind
                if not donation.status:
                    donation.status = 'pending'
                
                # Geocode pickup location if provided
                if donation.pickup_location and not (donation.pickup_latitude and donation.pickup_longitude):
                    try:
                        # Add geocoding logic here if needed
                        pass
                    except Exception as e:
                        messages.warning(request, "Could not verify pickup location coordinates")

            # Save the donation
            donation.save()
            
            # Handle post-save actions based on donation type
            if donation.donation_type == "in_kind":
                # Automatically try to assign to recipient if possible
                donation.assign_to_recipient()
            
            messages.success(request, "Donation submitted successfully!")
            return redirect('account')
    else:
        # Initialize form with default values
        form = DonationForm(initial={
            'donation_type': 'monetary',
            'currency': 'USD',
            'item_quantity': 1,
        })

    return render(request, 'donate.html', {
        'form': form,
        'monetary_fields': ['amount', 'currency'],
        'in_kind_fields': ['item_name', 'item_category', 'item_quantity', 
                          'item_description', 'item_condition',
                          'pickup_location', 'preferred_pickup_time']
    })
    

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
    # Fetch all donations for the logged-in user with optimizations
    donations = (
        Donation.objects.filter(donor=request.user)
        .select_related("assigned_agent")
        .only("id", "donation_type", "amount", "created_at", "item_name", 
              "item_quantity", "item_description", "message", "pickup_location", 
              "assigned_agent__username")
        .order_by('-created_at')  # Newest first
    )

    # Separate donations by type
    monetary_donations = donations.filter(donation_type="monetary")
    in_kind_donations = donations.filter(donation_type="in_kind")

    # Convert pickup locations to addresses
    for donation in in_kind_donations:
        donation.pickup_address = get_address_from_coordinates(donation.pickup_location) if donation.pickup_location else "No pickup location provided"

    # Paginate monetary donations
    monetary_paginator = Paginator(monetary_donations, 10)  # Show 10 per page
    monetary_page_number = request.GET.get('monetary_page')
    monetary_page_obj = monetary_paginator.get_page(monetary_page_number)

    # Paginate in-kind donations
    in_kind_paginator = Paginator(in_kind_donations, 10)  # Show 10 per page
    in_kind_page_number = request.GET.get('in_kind_page')
    in_kind_page_obj = in_kind_paginator.get_page(in_kind_page_number)

    # Calculate total donations
    total_donations = sum(donation.amount for donation in monetary_page_obj.object_list if donation.amount) or 0

    context = {
        "monetary_page_obj": monetary_page_obj,
        "in_kind_page_obj": in_kind_page_obj,
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
        "agents": Agent.objects.select_related('user').only('id', 'user__username'),
    }
    return render(request, "admin.html", context)

@login_required
def need_list(request):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can view needs")
        return redirect('home')
    
    needs = Need.objects.filter(recipient=request.user.recipient).order_by('-priority', 'is_fulfilled', '-date_logged')
    context = {
        'needs': needs,
        'total_needs': needs.count(),
        'fulfilled_needs': needs.filter(is_fulfilled=True).count(),
        'urgent_needs': needs.filter(priority=4, is_fulfilled=False).count(),
    }
    return render(request, 'need_list.html', context)

@login_required
def need_create(request):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can create needs")
        return redirect('home')
    
    if request.method == 'POST':
        form = NeedForm(request.POST)
        if form.is_valid():
            need = form.save(commit=False)
            need.recipient = request.user.recipient
            need.save()
            messages.success(request, "Need successfully recorded!")
            return redirect('need_list')
    else:
        form = NeedForm()
    
    context = {'form': form, 'title': "Record New Need", 'submit_text': "Create Need"}
    return render(request, 'need_form.html', context)

@login_required
def need_update(request, pk):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can edit needs")
        return redirect('home')
    
    need = get_object_or_404(Need, pk=pk, recipient=request.user.recipient)
    if request.method == 'POST':
        form = NeedForm(request.POST, instance=need)
        if form.is_valid():
            form.save()
            messages.success(request, "Need successfully updated!")
            return redirect('need_list')
    else:
        form = NeedForm(instance=need)
    
    context = {'form': form, 'title': "Update Need", 'submit_text': "Update Need"}
    return render(request, 'need_form.html', context)

@login_required
def need_delete(request, pk):
    if not hasattr(request.user, 'recipient'):
        messages.error(request, "Only recipients can delete needs")
        return redirect('home')
    
    need = get_object_or_404(Need, pk=pk, recipient=request.user.recipient)
    if request.method == 'POST':
        need.delete()
        messages.success(request, "Need successfully deleted")
        return redirect('need_list')
    
    return render(request, 'need_delete.html', {'need': need})
