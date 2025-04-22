from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from ..models import Donation, Need
from ..forms import DonationForm
from ..utils import get_address_from_coordinates
from itertools import chain
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@login_required
def donate(request):
    if request.method == 'POST':
        form = DonationForm(request.POST)
        if form.is_valid():
            try:
                donation = form.save(commit=False)
                donation.donor = request.user

                # Handle monetary donations
                if donation.donation_type == "monetary":
                    donation.item_name = "Money"
                    donation.item_quantity = 1
                    donation.item_description = None
                    donation.item_condition = None
                    donation.pickup_location = None
                    
                    if not donation.amount or donation.amount <= 0:
                        raise ValidationError("Please enter a valid donation amount")
                    
                # Handle in-kind donations
                else:
                    donation.amount = None
                    donation.currency = None
                    
                    if not donation.item_name:
                        raise ValidationError("Please specify the item name")
                    if not donation.item_quantity or donation.item_quantity <= 0:
                        raise ValidationError("Please enter a valid quantity")
                    if not donation.pickup_location:
                        raise ValidationError("Please provide a pickup location")

                    # Suggest matching needs
                    matching_needs = Need.objects.filter(
                        name__iexact=donation.item_name,
                        is_fulfilled=False
                    )[:5]

                donation.save()

                # Send confirmation email
                if donation.donor and donation.donor.email:
                    subject = f"Thank you for your {donation.get_donation_type_display()} donation!"
                    
                    # Prepare context for email template
                    context = {
                        'donation': donation,
                        'donor': donation.donor,
                        'matching_needs': matching_needs if donation.donation_type == "in_kind" else None,
                    }
                    
                    # Render HTML email template
                    html_message = render_to_string('emails/donation_confirmation.html', context)
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        html_message=html_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[donation.donor.email],
                        fail_silently=False,
                    )

                messages.success(request, 
                    f"Donation submitted successfully! Status: {donation.get_status_display()}")
                
                if donation.donation_type == "in_kind":
                    if matching_needs.exists():
                        messages.info(request, 
                            f"This donation matches {matching_needs.count()} active needs")
                
                return redirect('donation_detail', donation_id=donation.id)

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Error processing donation: {str(e)}")
    else:
        initial_data = {
            'donation_type': 'monetary',
            'currency': 'KES',
            'item_quantity': 1,
        }
        form = DonationForm(initial=initial_data)

    # Get popular needs for suggestions
    popular_needs = Need.objects.filter(
        is_fulfilled=False
    ).values('name', 'category').annotate(
        total_needed=Sum('quantity_needed') - Sum('quantity_received')
    ).order_by('-total_needed')[:10]

    return render(request, 'donate.html', {
        'form': form,
        'popular_needs': popular_needs,
        'category_choices': Need.CATEGORY_CHOICES,
    })


@login_required
def account(request):
    # Check if user is a recipient
    is_recipient = hasattr(request.user, 'recipient')
    recipient = request.user.recipient if is_recipient else None
    
    # Get donations made by the user
    donations = Donation.objects.filter(donor=request.user).select_related(
        "assigned_agent", 
        "assigned_agent__agent", 
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

