from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm
from .models import Agent


def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Log in successful!")
            return redirect('home')
        else:
            messages.success(request, "An error occurred. Please try again.")
            return redirect('login_user')
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
            user = form.save(commit=False)

            # Set the role and location in the User instance (temporarily)
            user.role = form.cleaned_data.get('role', 'donor')  # Default to 'donor' if role is not provided
            user.location = form.cleaned_data.get('location', '')  # Default to empty string if location is not provided
            user.population = form.cleaned_data.get('population', 0)
            user.phone_number = form.cleaned_data.get('phone_number', '')
    
            user.save()  # Save the User instance
            print(f"DEBUG: User created with username: {user.username}, role: {user.role}, location: {user.location}, population: {user.population}, phone_number: {user.phone_number}")
            login(request, user)
            messages.success(request, "You have successfully registered! Welcome!")
            return redirect('home')
        else:
            print(f"DEBUG: Form errors: {form.errors}")
            messages.error(request, "Registration failed. Please fix the errors.")
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

