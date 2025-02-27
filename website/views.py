from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm, DonationForm
from .models import UserProfile, Donation
from django.db import models
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Sum, Count

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
            form.save() #Saving the user
            role = form.cleaned_data['role'] #Getting the selected role
            
            # Create a UserProfile and save the role
            UserProfile.objects.create(user=user, role=role)
            
            # authenticate and log them in
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(
                request, "You Have Successfully Registered! Welcome!")
            return redirect('home')
    else:
        form = SignUpForm()
        return render(request, 'register.html', {'form': form})
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

def account(request):
    donations = Donation.objects.filter(donor=request.user)
    
    # Separate monetary and in-kind donations
    monetary_donations = donations.filter(donation_type="monetary")
    in_kind_donations = donations.filter(donation_type="in_kind")
    
    # Calculate the total donations for the logged-in user only
    total_donations = donations.aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'monetary_donations': monetary_donations,
        'in_kind_donations': in_kind_donations,
        'total_donations': total_donations,
    }
    return render(request, 'account.html', context)

def about(request):
    return render(request, 'about.html', {})

def report(request):
    # Calculate total donations and number of donors
    total_donations = Donation.objects.filter(donation_type="monetary").aggregate(total=Sum('amount'))['total'] or 0
    number_of_donors = Donation.objects.values('donor').distinct().count()

    # Donations per donor (monetary)
    donations_per_donor = Donation.objects.filter(donation_type="monetary").values('donor__username').annotate(total_donated=Sum('amount'))

    # In-kind donations per donor
    in_kind_donations_per_donor = Donation.objects.filter(donation_type="in_kind").values('donor__username').annotate(
        total_items=Sum('item_quantity'),
        total_donated=Sum('item_quantity')  # Assuming you want to count items as "total donated"
    )

    context = {
        'total_donations': total_donations,
        'number_of_donors': number_of_donors,
        'donations_per_donor': donations_per_donor,
        'in_kind_donations_per_donor': in_kind_donations_per_donor,
    }
    return render(request, 'report.html', context)