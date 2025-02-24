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
    class Meta:
        model = Donation
        fields = ["donation_type", "amount", "message", "item_name", "quantity", "description", "pickup_location"]

    def clean(self):
        cleaned_data = super().clean()
        donation_type = cleaned_data.get("donation_type")
        amount = cleaned_data.get("amount")
        item_name = cleaned_data.get("item_name")
        quantity = cleaned_data.get("quantity")

        if donation_type == "monetary" and not amount:
            raise forms.ValidationError("Amount is required for monetary donations.")
        elif donation_type == "in_kind" and not item_name:
            raise forms.ValidationError("Item name is required for in-kind donations.")

        return cleaned_data