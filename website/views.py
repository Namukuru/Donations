from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm, DonationForm
from .models import UserProfile, Donation

# Create your views here.


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
    form = DonationForm(request.POST)
    if request.method == 'POST':  
        if form.is_valid():
            donation = form.save(commit=False)
            donation.donor = request.user  # Associate the donation with the logged-in user
            donation.save()
            messages.success(
                request, "You have successfully made a donation")
            return redirect('home')
    else:
        form = DonationForm()
    return render(request, 'donate.html', {'form': form})

def donation_success(request):
    return render(request, 'donate.html',{'form': form})

def account(request):
    # Get donations made by the logged-in user
    donations = Donation.objects.filter(donor=request.user)
    
    # Render the donations to the template
    return render(request, 'account.html', {'donations': donations})