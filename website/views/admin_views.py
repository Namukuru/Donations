from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Donation, Agent
from ..utils import get_address_from_coordinates
from django.core.cache import cache
from django.db.models import Sum

@login_required
def admin_dashboard(request):
    unassigned_donations = Donation.objects.filter(donation_type="in_kind", assigned_agent__isnull=True).select_related('donor')
    assigned_donations = Donation.objects.filter(donation_type="in_kind", assigned_agent__isnull=False).select_related('donor', 'assigned_agent')

    address_map = {loc: get_address_from_coordinates(loc) for loc in {d.pickup_location for d in unassigned_donations | assigned_donations if d.pickup_location}}

    context = {
        "unassigned_donations": [
            {"id": d.id, "donor_name": d.donor.username, "pickup_address": address_map.get(d.pickup_location, "N/A"), "donation_items": f"{d.item_quantity or 1}x {d.item_name}"}
            for d in unassigned_donations
        ],
        "assigned_donations": [
            {"id": d.id, "donor_name": d.donor.username, "pickup_address": address_map.get(d.pickup_location, "N/A"), "assigned_agent": d.assigned_agent.username, "status": d.status}
            for d in assigned_donations
        ],
        "agents": Agent.objects.select_related('user').only('id', 'user__username'),
    }
    return render(request, "admin.html", context)

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


