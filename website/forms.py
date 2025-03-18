from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Donation, Agent, UserProfile
class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'})
    )
    first_name = forms.CharField(
        label="First Name",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        label="Last Name",
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )

    ROLE_CHOICES = [
        ('donor', 'Donor'),
        ('recipient', 'Recipient'),
        ('agent', 'Agent'),
    ]
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="Register as",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    location = forms.CharField(
        label="Location",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False  # Only required for agents/recipients
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'location')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'User Name'})
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

        # Remove default help text
        for field_name in self.fields:
            self.fields[field_name].help_text = None

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        location = cleaned_data.get("location")

        # Ensure agents and recipients provide a location
        if role != "donor" and not location:
            self.add_error("location", "This field is required for agents and recipients.")

        return cleaned_data

    def save(self, commit=True):
        print("DEBUG: save() method called!") 
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        location = self.cleaned_data.get('location') if role != 'donor' else None

        print(f"DEBUG: Saving user with role {role}")  # Debugging output

        if commit:
            user.save()
            print(f"DEBUG: User saved with ID {user.id}")

            # Ensure a unique UserProfile is created
            profile, created = UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': role, 'location': location}
            )

            print(f"DEBUG: UserProfile created/updated with role: {profile.role}")

            if role == 'agent':
                Agent.objects.create(user=user, location=location)  # Save location in Agent model

        return user

        
class DonationForm(forms.ModelForm):
    
    class Meta:
        model = Donation
        fields = '__all__'
        exclude = [] 
        widgets = {
            'message': forms.Textarea(attrs={'placeholder': 'Make a comment ...', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        donation_type = cleaned_data.get("donation_type")
        amount = cleaned_data.get("amount")
        item_name = cleaned_data.get("item_name")
        item_quantity = cleaned_data.get("item_quantity")
        message = cleaned_data.get("message")

        if donation_type == "monetary":
            if not amount:
                self.add_error('amount', "Amount is required for monetary donations.")
            # Clear in-kind fields for monetary donations
            cleaned_data["item_name"] = None
            cleaned_data["item_quantity"] = None
            cleaned_data["item_description"] = None
            cleaned_data["pickup_location"] = None
            cleaned_data["message"] = None
            cleaned_data["status"] = None 
            
        elif donation_type == "in_kind":
            if not item_name:
                self.add_error('item_name', "Item name is required for in-kind donations.")
            if not item_quantity:
                self.add_error('item_quantity', "Quantity is required for in-kind donations.")
            if not message: 
                self.add_error('message', "Message is required for in-kind donations.")
            # Clear monetary field for in-kind donations
            cleaned_data["amount"] = None
        return cleaned_data