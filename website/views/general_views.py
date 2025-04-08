from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from ..models import Donation, Agent
from ..utils import get_address_from_coordinates

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
    
def about(request):
    return render(request, 'about.html', {})

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
            "donor__first_name",
            "donor__last_name",
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

