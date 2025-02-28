from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Donation
from .models import UserProfile
class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="Email", widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    first_name = forms.CharField(label="First Name", max_length=50, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(label="Last Name", max_length=50, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    ROLE_CHOICES = [
        ('donor', 'Donor'),
        ('agent', 'Agent'),
        ('recipient', 'Recipient'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Register as")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)

        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['username'].widget.attrs['placeholder'] = 'User Name'
        self.fields['username'].label = 'Username'

        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password1'].label = 'Password'

        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password'
        self.fields['password2'].label = 'Password'

        # Remove default help text
        for field_name in self.fields:
            self.fields[field_name].help_text = None

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role') 
        
        if commit:
            user.save()  # Now save the user first
        
            # Ensure no existing profile is interfering
            UserProfile.objects.filter(user=user).delete()
            
            # Create a UserProfile with the correct role
            profile = UserProfile.objects.create(user=user, role=role)


        return user
class DonationForm(forms.ModelForm):
    class Meta:
        model = Donation
        fields = ["donation_type", "amount", "message", "item_name", "item_quantity", "item_description", "pickup_location"]

    def clean(self):
        cleaned_data = super().clean()
        donation_type = cleaned_data.get("donation_type")
        amount = cleaned_data.get("amount")
        item_name = cleaned_data.get("item_name")
        item_quantity = cleaned_data.get("item_quantity")
        item_description = cleaned_data.get("item_description")

        if donation_type == "monetary":
            if not amount:
                raise forms.ValidationError("Amount is required for monetary donations.")
            # Clear in-kind fields for monetary donations
            cleaned_data["item_name"] = None
            cleaned_data["item_quantity"] = None
            cleaned_data["item_description"] = None
            cleaned_data["pickup_location"] = None
        elif donation_type == "in_kind":
            if not item_name:
                raise forms.ValidationError("Item name is required for in-kind donations.")
            if not item_quantity:
                raise forms.ValidationError("Quantity is required for in-kind donations.")
            # Clear monetary field for in-kind donations
            cleaned_data["amount"] = None
        return cleaned_data