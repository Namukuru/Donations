from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm


def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Log in successful!")
            return redirect('login_user')
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
        print(f"DEBUG: Incoming POST data: {request.POST}")  # Debugging
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            print(f"DEBUG: Form cleaned data: {form.cleaned_data}")  # Check role in cleaned data
            user=form.save()
            login(request, user)
            messages.success(request, "You have successfully registered! Welcome!")
            return redirect('home')
        else:
            print(f"DEBUG: Form errors: {form.errors}")
            messages.error(request, "Registration failed. Please fix the errors.")
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})

