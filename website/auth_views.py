from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import SignUpForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def login_user(request):
    if request.method == 'POST':
        try:
            # Basic validation
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '').strip()
            
            if not username or not password:
                raise ValidationError(_("Please provide both username and password."))
            
            # Rate limiting check could be added here
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, _("You have successfully logged in!"))
                    
                    # Redirect to 'next' parameter if it exists and is safe
                    next_url = request.POST.get('next') or request.GET.get('next')
                    if next_url and not next_url.startswith(('http:', 'https:')):
                        return redirect(next_url)
                    return redirect('home')
                else:
                    messages.error(request, _("This account is inactive."))
            else:
                # Generic error message to avoid revealing whether username exists
                messages.error(request, _("Invalid login credentials. Please try again."))
                
        except ValidationError as e:
            messages.error(request, e.message)
        except Exception as e:
            # Log the actual error for admin review
            # logger.error(f"Login error: {str(e)}")
            messages.error(request, _("An unexpected error occurred. Please try again later."))
        
        # Return to login page with preserved username (but not password)
        return render(request, 'loginUser.html', {
            'username': username,
            'next': request.POST.get('next', '')
        })
    
    # GET request - show login form
    return render(request, 'loginUser.html', {
        'next': request.GET.get('next', '')
    })

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

