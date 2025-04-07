from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from ..models import Donation
from ..forms import DonationForm
from ..utils import get_address_from_coordinates
from itertools import chain


@login_required
def donate(request):
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user  

            # Handle donation type logic
            if donation.donation_type == "monetary":
                donation.item_name, donation.item_quantity, donation.status = "Money", 1, "completed"
                donation.item_description = donation.item_condition = donation.pickup_location = None
                donation.amount = donation.amount or 0  
            else:
                donation.currency = 'USD'
                donation.status = donation.status or 'pending'

                if donation.pickup_location and not (donation.pickup_latitude and donation.pickup_longitude):
                    pass  # Geocoding logic (if needed)

            donation.save()

            if donation.donation_type == "in_kind":
                donation.assign_to_recipient()

            messages.success(request, "Donation submitted successfully!")
            return redirect('account')
    else:
        form = DonationForm(initial={'donation_type': 'monetary', 'currency': 'USD', 'item_quantity': 1})

    return render(request, 'donate.html', {'form': form})

@login_required
def account(request):
    # Check if user is a recipient
    is_recipient = hasattr(request.user, 'recipient')
    recipient = request.user.recipient if is_recipient else None
    
    # Get donations made by the user
    donations = Donation.objects.filter(donor=request.user).select_related(
        "assigned_agent", 
        "assigned_recipient__user"  # Pull recipient and their user info
    ).order_by('-created_at')

    # Split by donation type
    monetary_donations = donations.filter(donation_type="monetary")
    in_kind_donations = donations.filter(donation_type="in_kind")

    # Donations assigned *to* this user (if they're a recipient)
    assigned_donations = Donation.objects.none()
    if is_recipient:
        assigned_donations = Donation.objects.filter(
            assigned_recipient=request.user.recipient
        ).select_related("donor", "assigned_agent")

    # Convert pickup coordinates to addresses
    for donation in chain(in_kind_donations, assigned_donations):
        donation.pickup_address = get_address_from_coordinates(
            donation.pickup_location
        ) if donation.pickup_location else "No pickup location provided"

    # Paginate
    monetary_page_obj = Paginator(monetary_donations, 10).get_page(request.GET.get('monetary_page'))
    in_kind_page_obj = Paginator(in_kind_donations, 10).get_page(request.GET.get('in_kind_page'))
    assigned_page_obj = Paginator(assigned_donations, 10).get_page(request.GET.get('assigned_page'))

    context = {
        "monetary_page_obj": monetary_page_obj,
        "in_kind_page_obj": in_kind_page_obj,
        "assigned_page_obj": assigned_page_obj,
        "total_donations": sum(d.amount for d in monetary_page_obj if d.amount) or 0,
        "is_recipient": is_recipient,
        "recipient": recipient,
    }
    return render(request, "account.html", context)