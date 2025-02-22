from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Donation


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="Email", widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Email Address'}))
    first_name = forms.CharField(label="First Name", max_length="50", widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(label="Last Name", max_length="50", widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Last Name'}))
    ROLE_CHOICES = [
        ('donor', 'Donor'),
        ('recipient', 'Recipient'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Register as")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name',
                  'email', 'password1', 'password2','role')

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
            
class DonationForm(forms.ModelForm):
    PICKUP_CHOICES = [
        ('current', 'Use Current Location'),
        ('manual', 'Enter Another Location'),
    ]
    donation_type = forms.ChoiceField(choices=[('monetary', 'Monetary'), ('in-kind', 'In-Kind')])
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    message = forms.CharField(widget=forms.Textarea(attrs={'cols': 40, 'rows': 3}))  # Adjust cols and rows
    item_name = forms.CharField(required=False) # Required for in-kind donations
    item_description = forms.CharField(required=False) # Required for in-kind donations
    item_quantity = forms.IntegerField(required=False) # Required for in-kind donations
    pickup_choice = forms.ChoiceField(
        choices=PICKUP_CHOICES, widget=forms.Select(attrs={'id': 'pickup-choice'})
    )
    pickup_location = forms.CharField(
        required=False,  # Only required if "manual" is selected
        widget=forms.TextInput(attrs={'id': 'pickup-location', 'style': 'display:none;', 'placeholder': 'Enter preferred address'}))
    class Meta:
        model = Donation
        fields = ['amount', 'message','pickup_choice','pickup_location','item_name','quantity','description',]  # Fields to include in the form
