from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Booking

class AdminCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control-premium', 'placeholder': 'Enter strong password'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control-premium', 'placeholder': 'Repeat password'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control-premium', 'placeholder': 'e.g. admin_john'}),
            'email': forms.EmailInput(attrs={'class': 'form-control-premium', 'placeholder': 'e.g. john@example.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control-premium', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control-premium', 'placeholder': 'Last Name'})
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.is_staff = True
        user.is_superuser = False # Explicitly not a super admin
        if commit:
            user.save()
        return user


class AdminEditForm(forms.ModelForm):
    is_active = forms.BooleanField(required=False, label="Active Status (Enable Login Access)")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control-premium'}),
            'email': forms.EmailInput(attrs={'class': 'form-control-premium'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control-premium'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control-premium'})
        }

class BookingForm(forms.ModelForm):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        label='Start Time'
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
        }),
        label='End Time'
    )

    class Meta:
        model = Booking
        fields = ['title', 'contact_person', 'mobile_number', 'start_time', 'end_time']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter event title'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and start_time < timezone.now():
            raise forms.ValidationError("Booking cannot be made in the past.")

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")

        return cleaned_data
