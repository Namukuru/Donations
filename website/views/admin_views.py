from django.contrib.auth.decorators import login_required
from ..utils import get_address_from_coordinates
from django.template.loader import get_template
from django.shortcuts import render
from ..models import Donation, Agent
from django.core.cache import cache
from django.db.models import Sum, Q
from django.http import HttpResponse
from io import BytesIO
import pandas as pd
import csv
import json
from xhtml2pdf import pisa

from datetime import datetime

@login_required
def admin_dashboard(request):
    unassigned_donations = Donation.objects.filter(donation_type="in_kind", assigned_agent__isnull=True).select_related('donor')
    assigned_donations = Donation.objects.filter(donation_type="in_kind", assigned_agent__isnull=False).select_related('donor', 'assigned_agent')

    address_map = {loc: get_address_from_coordinates(loc) for loc in {d.pickup_location for d in unassigned_donations | assigned_donations if d.pickup_location}}

    context = {
        "unassigned_donations": [
            {"id": d.id, "donor_name": f"{d.donor.first_name} {d.donor.last_name}", "pickup_address": address_map.get(d.pickup_location, "N/A"), "quantity": d.item_quantity or 1,
            "donation_items": f"{d.item_name}",}
            for d in unassigned_donations
        ],
        "assigned_donations": [
        {
            "id": d.id,
            "donor_name": f"{d.donor.first_name or ''} {d.donor.last_name or ''}".strip() if d.donor.first_name or d.donor.last_name else d.donor.username,
            "pickup_address": address_map.get(d.pickup_location, "N/A"),
            "assigned_agent": f"{d.assigned_agent.first_name or ''} {d.assigned_agent.last_name or ''}".strip() if d.assigned_agent.first_name or d.assigned_agent.last_name else d.assigned_agent.username,
            "status": d.status,
            "quantity": d.item_quantity or 1,
            "donation_items": f"{d.item_name}",
        }
        for d in assigned_donations
        ],
        "agents": Agent.objects.select_related('user').only('id', 'user__username'),
    }
            
    return render(request, "admin.html", context)


def report(request):
    # Extract filters from request
    donation_type = request.GET.get("donation_type")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    donor_name = request.GET.get("donor_name")

    # Base queryset
    donations = Donation.objects.select_related("donor")

    # Apply filters
    if donation_type in ["monetary", "in_kind"]:
        donations = donations.filter(donation_type=donation_type)
    if start_date:
        donations = donations.filter(date__gte=start_date)
    if end_date:
        donations = donations.filter(date__lte=end_date)
    if donor_name:
        donations = donations.filter(
            Q(donor__first_name__icontains=donor_name) |
            Q(donor__last_name__icontains=donor_name)
        )

    # Aggregate total monetary donations
    total_donations = donations.filter(donation_type="monetary").aggregate(
        total=Sum("amount")
    )["total"] or 0

    # Count distinct donors
    number_of_donors = donations.values("donor_id").distinct().count()

    # Monetary donations per donor
    donations_per_donor = (
        donations.filter(donation_type="monetary")
        .values("donor__first_name", "donor__last_name")
        .annotate(total_donated=Sum("amount"))
    )

    # In-kind donations
    in_kind_donations = donations.filter(donation_type="in_kind").select_related("donor")

    # Add pickup addresses from cache or function
    for donation in in_kind_donations:
        cache_key = f"pickup_address_{donation.id}"
        pickup_address = cache.get(cache_key)

        if not pickup_address:
            pickup_address = (
                get_address_from_coordinates(donation.pickup_location)
                if donation.pickup_location
                else "No pickup location provided"
            )
            cache.set(cache_key, pickup_address, timeout=86400)

        donation.pickup_address = pickup_address

    # Handle export formats
    format = request.GET.get("format")

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="donation_report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Donor", "Total Donated"])
        for donor in donations_per_donor:
            name = f"{donor['donor__first_name']} {donor['donor__last_name']}".strip()
            writer.writerow([name or "Anonymous", donor["total_donated"]])
        return response

    elif format == "pdf":
        template = get_template("report_pdf.html")
        html = template.render({
            "total_donations": total_donations,
            "number_of_donors": number_of_donors,
            "donations_per_donor": donations_per_donor,
            "in_kind_donations": in_kind_donations,
        })
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="donation_report.pdf"'
        pisa.CreatePDF(BytesIO(html.encode("UTF-8")), dest=response)
        return response

    # Default HTML render
    context = {
        "total_donations": total_donations,
        "number_of_donors": number_of_donors,
        "donations_per_donor": donations_per_donor,
        "in_kind_donations": in_kind_donations,
    }
    return render(request, "report.html", context)


def in_kind_donations_analysis(request):
    # Fetch in-kind donations
    in_kind_donations = Donation.objects.filter(donation_type="in_kind").values(
        'item_name', 'item_quantity', 'pickup_location', 'date'
    )

    # Convert to Pandas DataFrame
    df = pd.DataFrame(in_kind_donations)

    if df.empty:
        context = {
            'most_donated_items': {},
            'monthly_quantities': json.dumps({}),
            'pickup_locations': {},
        }
        return render(request, 'in_kind_analysis.html', context)

    # Most donated items
    most_donated_items = (
        df.groupby('item_name')['item_quantity']
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    # Convert date column
    df['date'] = pd.to_datetime(df['date'])
    df['year_month'] = df['date'].dt.to_period('M').astype(str)

    monthly_quantities = (
        df.groupby('year_month')['item_quantity']
        .sum()
        .to_dict()
    )

    # Pickup locations
    pickup_locations = df['pickup_location'].value_counts().to_dict()

    # Pass data to the template (convert monthly_quantities to JSON)
    context = {
        'most_donated_items': most_donated_items,
        'monthly_quantities': json.dumps(monthly_quantities),  # Important
        'pickup_locations': pickup_locations,
    }
    return render(request, 'in_kind_analysis.html', context)

