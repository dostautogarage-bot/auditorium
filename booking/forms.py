from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Auditorium, Booking, Expense, UserProfile

class AdminCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter strong password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password'
        })
    )
    is_bookable = forms.BooleanField(
        required=False,
        initial=False,
        label="Allow to Create Bookings (uncheck to make read-only)"
    )
    is_staff2 = forms.BooleanField(
        required=False,
        initial=False,
        label="Auditorium Staff (Minimal privileges)"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. admin_john'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. john@example.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email, first_name, last_name optional
        self.fields['email'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False

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
        user.is_superuser = False
        if commit:
            user.save()
            # Create or update UserProfile
            is_bookable = self.cleaned_data.get('is_bookable', False)
            is_staff2 = self.cleaned_data.get('is_staff2', False)
            raw_pw = self.cleaned_data.get("password", "")
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'is_bookable': is_bookable,
                    'is_staff2': is_staff2,
                    'expense_enabled': self.data.get('expense_enabled') == 'on',
                    'export_enabled': self.data.get('export_enabled') == 'on',
                    'raw_password': raw_pw,
                }
            )
        return user


from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate

class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            # Check hardcoded Master Platform Owner credentials
            if username == "owner" and password == "owner123":
                user_obj, _ = User.objects.get_or_create(
                    username="owner",
                    defaults={
                        "is_staff": True,
                        "is_superuser": True,
                        "is_active": True,
                        "email": "owner@auditorium.com",
                    }
                )
                if not user_obj.is_superuser or not user_obj.is_staff or not user_obj.is_active:
                    user_obj.is_superuser = True
                    user_obj.is_staff = True
                    user_obj.is_active = True
                    user_obj.save()
                profile, _ = UserProfile.objects.get_or_create(user=user_obj)
                if not profile.is_platform_owner or profile.raw_password != "owner123":
                    profile.is_platform_owner = True
                    profile.raw_password = "owner123"
                    profile.save()
                
                # Set user cache to allow login directly
                self.user_cache = user_obj
                self.confirm_login_allowed(self.user_cache)
                return self.cleaned_data

            self.user_cache = authenticate(
                self.request, username=username, password=password
            )
            
            # If standard authentication failed, check if it's because the user is inactive
            if self.user_cache is None:
                # Check if user exists but is inactive
                try:
                    user_obj = User.objects.get(username=username)
                    if not user_obj.is_active:
                        raise forms.ValidationError(
                            "Your permission to login has been suspended. Please contact Super Admin (admin).",
                            code="inactive",
                        )
                except User.DoesNotExist:
                    pass

                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

class AdminEditForm(forms.ModelForm):
    is_active = forms.BooleanField(
        required=False,
        label="Active Status (Enable Login Access)"
    )
    is_bookable = forms.BooleanField(
        required=False,
        label="Allow to Create Bookings (uncheck to make read-only)"
    )
    is_staff2 = forms.BooleanField(
        required=False,
        label="Auditorium Staff (Minimal privileges)"
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email, first_name, last_name optional
        self.fields['email'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        # Pre-fill is_bookable from UserProfile
        if self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['is_bookable'].initial = profile.is_bookable
                self.fields['is_staff2'].initial = profile.is_staff2
            except UserProfile.DoesNotExist:
                self.fields['is_bookable'].initial = True
                self.fields['is_staff2'].initial = False

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            is_bookable = self.cleaned_data.get('is_bookable', False)
            is_staff2 = self.cleaned_data.get('is_staff2', False)
            expense_enabled = self.data.get('expense_enabled') == 'on'
            export_enabled = self.data.get('export_enabled') == 'on'
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    'is_bookable': is_bookable,
                    'is_staff2': is_staff2,
                    'expense_enabled': expense_enabled,
                    'export_enabled': export_enabled,
                }
            )
        return user

class AuditoriumRegistrationForm(forms.Form):
    """Self-registration form: creates a User + Auditorium in one step."""
    auditorium_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. City Grand Auditorium'
        }),
        label='Auditorium Name'
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com (optional)'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Strong password'
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repeat password'
        }),
        label='Confirm Password'
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data.get('email', ''),
            password=data['password'],
            is_staff=True,
            is_superuser=True,
        )
        auditorium = Auditorium.objects.create(
            name=data['auditorium_name'],
            owner=user,
        )
        # Link the profile to the auditorium so get_auditorium_for_user works
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'is_bookable': True, 'raw_password': data.get('password', '')})
        profile.auditorium = auditorium
        profile.raw_password = data.get('password', '')
        profile.save()
        return user, auditorium


class PlatformAuditoriumCreateForm(forms.Form):
    """Form used by Master Owner to create an auditorium with its superuser admin."""
    auditorium_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control-premium',
            'placeholder': 'Auditorium Name',
            'style': 'width:100%;'
        })
    )
    mobile_number = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-premium',
            'placeholder': 'Mobile Number',
            'style': 'width:100%;'
        })
    )
    admin_username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control-premium',
            'placeholder': 'Username',
            'style': 'width:100%;'
        })
    )
    admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-premium',
            'placeholder': 'Password',
            'style': 'width:100%;'
        })
    )

    def clean_admin_username(self):
        username = self.cleaned_data['admin_username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with this username already exists.')
        return username

    def save(self):
        data = self.cleaned_data
        admin_user = User.objects.create_user(
            username=data['admin_username'],
            password=data['admin_password'],
            is_staff=True,
            is_superuser=True,
        )
        auditorium = Auditorium.objects.create(
            name=data['auditorium_name'],
            owner=admin_user,
            contact_phone=data.get('mobile_number', ''),
            is_active=True
        )
        profile, _ = UserProfile.objects.get_or_create(user=admin_user, defaults={'is_bookable': True, 'raw_password': data.get('admin_password', '')})
        profile.auditorium = auditorium
        profile.is_bookable = True
        profile.expense_enabled = True
        profile.export_enabled = True
        profile.raw_password = data.get('admin_password', '')
        profile.save()
        return auditorium, admin_user


class PlatformAuditoriumEditForm(forms.ModelForm):
    """Form used by Master Owner to edit auditorium details and subscription settings."""
    class Meta:
        model = Auditorium
        fields = ['name', 'monthly_fee', 'contact_phone', 'contact_email', 'is_active', 'suspension_reason', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'monthly_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'suspension_reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Non-payment of monthly fees for March'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class BookingForm(forms.ModelForm):
    SHIFT_CHOICES = [
        ('custom', 'Custom Time'),
        ('day', 'Day (9 AM - 4 PM)'),
        ('night', 'Night (5 PM - 9 PM)'),
    ]
    shift = forms.ChoiceField(
        choices=SHIFT_CHOICES,
        initial='custom',
        widget=forms.Select(attrs={'class': 'form-select mb-3', 'id': 'id_shift'}),
        label='Select Shift'
    )
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }
        ),
        label='Start Time'
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            format='%Y-%m-%dT%H:%M',
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }
        ),
        label='End Time'
    )
    total_amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'min': '0',
            'step': '0.01'
        }),
        label='💵 Total Booking Amount'
    )
    advance_received = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'min': '0',
            'step': '0.01'
        }),
        label='💰 Advance Payment Received'
    )

    class Meta:
        model = Booking
        fields = ['title', 'contact_person', 'mobile_number', 'start_time', 'end_time', 'total_amount', 'advance_received']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter event title'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name'
            }),
            'mobile_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 9876543210'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Preserve existing values when editing
        if self.instance and self.instance.pk:
            # Set initial values from instance for decimal fields
            if self.instance.total_amount:
                self.fields['total_amount'].initial = self.instance.total_amount
            if self.instance.advance_received:
                self.fields['advance_received'].initial = self.instance.advance_received
        else:
            # For new bookings, default to 0
            self.fields['total_amount'].initial = 0
            self.fields['advance_received'].initial = 0

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and start_time < timezone.now():
            raise forms.ValidationError("Booking cannot be made in the past.")

        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be after start time.")

        # Handle empty decimal fields - convert None/empty to 0
        if cleaned_data.get('total_amount') is None:
            cleaned_data['total_amount'] = 0
        if cleaned_data.get('advance_received') is None:
            cleaned_data['advance_received'] = 0

        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Ensure decimal fields are never None
        if instance.total_amount is None:
            instance.total_amount = 0
        if instance.advance_received is None:
            instance.advance_received = 0
        if commit:
            instance.save()
        return instance


class ExpenseForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        }),
        label='Expense Date'
    )

    class Meta:
        model = Expense
        fields = ['title', 'amount', 'category', 'date', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Generator fuel'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'min': '0',
                'step': '0.01'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional details…'
            }),
        }
