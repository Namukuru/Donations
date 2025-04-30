from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django import forms
from .models import Donation, Agent, UserProfile, Recipient, Need

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

    # Fields specific to recipients
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=15,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        required=False
    )
    population = forms.IntegerField(
        label="Population",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Population'}),
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'location', 'phone_number', 'population')

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
        phone_number = cleaned_data.get("phone_number")
        population = cleaned_data.get("population")

        # Ensure agents and recipients provide a location
        if role != "donor" and not location:
            self.add_error("location", "This field is required for agents and recipients.")

        # Ensure recipients provide a phone number and population
        if role == "recipient":
            if not phone_number:
                self.add_error("phone_number", "This field is required for recipients.")
            if not population:
                self.add_error("population", "This field is required for recipients.")

        return cleaned_data

    def save(self, commit=True):
        print("DEBUG: save() method called!") 
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        location = self.cleaned_data.get('location') if role != 'donor' else None
        phone_number = self.cleaned_data.get('phone_number') if role == 'recipient' else None
        population = self.cleaned_data.get('population') if role == 'recipient' else None

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

            # Create Agent or Recipient instance based on role
            if role == 'agent':
                Agent.objects.create(user=user, location=location)  # Save location in Agent model
            elif role == 'recipient':
                Recipient.objects.create(
                    user=user,
                    phone_number=phone_number,
                    population=population,
                    location=location
                )

        return user


    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'role', 'location', 'phone_number', 'population')

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
        phone_number = cleaned_data.get("phone_number")
        population = cleaned_data.get("population")

        # Ensure agents and recipients provide a location
        if role != "donor" and not location:
            self.add_error("location", "This field is required for agents and recipients.")

        # Ensure recipients provide a phone number and population
        if role == "recipient":
            if not phone_number:
                self.add_error("phone_number", "This field is required for recipients.")
            if not population:
                self.add_error("population", "This field is required for recipients.")

        return cleaned_data

    def save(self, commit=True):
        print("DEBUG: save() method called!") 
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        location = self.cleaned_data.get('location') if role != 'donor' else None
        phone_number = self.cleaned_data.get('phone_number') if role == 'recipient' else None
        population = self.cleaned_data.get('population') if role == 'recipient' else None

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

            # Create Agent or Recipient instance based on role
            if role == 'agent':
                Agent.objects.create(user=user, location=location)  # Save location in Agent model
            elif role == 'recipient':
                Recipient.objects.create(
                    user=user,
                    phone_number=phone_number,
                    population=population,
                    location=location
                )

        return user
        
class DonationForm(forms.ModelForm):
    # Common fields
    donation_type = forms.ChoiceField(
        choices=Donation.DONATION_TYPES,
        widget=forms.RadioSelect,
        initial='monetary'  # Default to monetary
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Any additional information...', 'rows': 3}),
        required=False
    )
    
    # Monetary donation fields
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': '0.00'})
    )
    currency = forms.ChoiceField(
        choices=[('KES','KES'),('USD', 'USD'), ('EUR', 'EUR')],  # Add more as needed
        initial='KES',
        required=False
    )
    
    # In-kind donation fields
    item_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Item name'})
    )
    item_category = forms.ChoiceField(
        choices=Need.CATEGORY_CHOICES,
        required=False,
        help_text="General category of the item"
    )
    item_quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': '1'})
    )
    item_description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Item description...', 'rows': 3}),
        required=False
    )
    item_condition = forms.ChoiceField(
        choices=[
            ('new', 'New'), 
            ('used', 'Used'), 
            ('refurbished', 'Refurbished')
        ],
        required=False
    )
    
    # Location fields (primarily for in-kind donations)
    pickup_location = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Full address for pickup'})
    )
    preferred_pickup_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        help_text="Preferred date/time for pickup"
    )
    
    assigned_recipient = forms.ModelChoiceField(
        queryset=Recipient.objects.all(),
        required=False,
        help_text="Optionally select a recipient, or leave blank to let the system assign one automatically."
    )

    class Meta:
        model = Donation
        fields = [
            'donation_type',
            'message',
            # Monetary fields
            'amount', 'currency',
            # In-kind fields
            'item_name', 'item_category', 'item_quantity',
            'item_description', 'item_condition','assigned_recipient',
            # Location fields
            'pickup_location', 'preferred_pickup_time',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set initial values based on donation type if instance exists
        if self.instance and self.instance.pk:
            if self.instance.donation_type == 'monetary':
                self.fields['amount'].initial = self.instance.amount
                self.fields['currency'].initial = self.instance.currency
            elif self.instance.donation_type == 'in_kind':
                self.fields['item_name'].initial = self.instance.item_name
                self.fields['item_quantity'].initial = self.instance.item_quantity
                self.fields['item_description'].initial = self.instance.item_description
                self.fields['item_condition'].initial = self.instance.item_condition
                self.fields['pickup_location'].initial = self.instance.pickup_location
                self.fields['preferred_pickup_time'].initial = self.instance.preferred_pickup_time

        # Add CSS classes for JavaScript handling
        self.fields['donation_type'].widget.attrs.update({'class': 'donation-type-toggle'})
        self.fields['amount'].widget.attrs.update({'class': 'monetary-field'})
        self.fields['currency'].widget.attrs.update({'class': 'monetary-field'})
        
        in_kind_fields = ['item_name', 'item_category', 'item_quantity', 
                         'item_description', 'item_condition',
                         'pickup_location', 'preferred_pickup_time']
        for field in in_kind_fields:
            self.fields[field].widget.attrs.update({'class': 'in-kind-field'})

    def clean(self):
        cleaned_data = super().clean()
        donation_type = cleaned_data.get("donation_type")
        
        if donation_type == "monetary":
            # Validate monetary fields
            if not cleaned_data.get("amount"):
                self.add_error('amount', "Amount is required for monetary donations.")
            
            # Clear in-kind fields
            for field in ['item_name', 'item_category', 'item_quantity', 
                         'item_description', 'item_condition', 'pickup_location', 
                         'preferred_pickup_time']:
                cleaned_data[field] = None
        
        elif donation_type == "in_kind":
            # Validate in-kind fields
            if not cleaned_data.get("item_name"):
                self.add_error('item_name', "Item name is required for in-kind donations.")
            if not cleaned_data.get("item_quantity"):
                self.add_error('item_quantity', "Quantity is required for in-kind donations.")
            if not cleaned_data.get("pickup_location"):
                self.add_error('pickup_location', "Pickup location is required for in-kind donations.")
            
            # Set default category if not provided
            if not cleaned_data.get("item_category"):
                cleaned_data['item_category'] = 'other'
            
            # Clear monetary fields
            cleaned_data["amount"] = None
            cleaned_data["currency"] = 'KES'
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Assign user-selected recipient if provided
        recipient = self.cleaned_data.get('assigned_recipient')
        if recipient:
            instance.assigned_recipient = recipient
            instance.status = 'in_progress'
        else:
            instance.assigned_recipient = None  # Let backend handle assignment

        if instance.donation_type == "monetary":
            # Set monetary fields
            instance.amount = self.cleaned_data['amount']
            instance.currency = self.cleaned_data['currency']
            # Clear in-kind fields
            instance.item_name = "Money"
            instance.item_quantity = 1
            instance.item_description = None
            instance.item_condition = None
            instance.pickup_location = None
            instance.pickup_latitude = None
            instance.pickup_longitude = None
            instance.preferred_pickup_time = None

        elif instance.donation_type == "in_kind":
            # Set in-kind fields
            instance.item_name = self.cleaned_data['item_name']
            instance.item_quantity = self.cleaned_data['item_quantity']
            instance.item_description = self.cleaned_data['item_description']
            instance.item_condition = self.cleaned_data['item_condition']
            instance.pickup_location = self.cleaned_data['pickup_location']
            instance.preferred_pickup_time = self.cleaned_data['preferred_pickup_time']
            # Clear monetary fields
            instance.amount = None
            instance.currency = 'KES'

        if commit:
            instance.save()

        return instance
  

class DonationCompletionForm(forms.Form):
    photo1 = forms.ImageField(label='Photo 1', required=True)
    photo2 = forms.ImageField(label='Photo 2', required=True)
    photo3 = forms.ImageField(label='Photo 3', required=True)
    notes = forms.CharField(label='Completion Notes', widget=forms.Textarea, required=False)
    
    
class ProfileUpdateForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field and help text
        self.fields.pop('password')
        self.fields['email'].required = True


class NeedForm(forms.ModelForm):
    class Meta:
        model = Need
        fields = ['category', 'name', 'description', 'quantity_needed', 'unit', 'priority']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'quantity_needed': forms.NumberInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_quantity_needed(self):
        quantity_needed = self.cleaned_data.get('quantity_needed')
        if quantity_needed <= 0:
            raise forms.ValidationError("Quantity needed must be greater than zero.")
        return quantity_needed