"""
Forms for the Kannammal Agro application.
Handles price submission forms with validation.
"""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from .models import (
    PriceSubmission, Firm, Location, Farmer, ProductCategory, 
    Product, UserProfile
)


class BuyerSubmissionForm(forms.ModelForm):
    """Form for buyers to submit price data"""
    
    class Meta:
        model = PriceSubmission
        fields = [
            'date', 'firm', 'location', 'farmer', 'category', 
            'product', 'price_per_unit', 'quantity', 'unit', 'notes'
        ]
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'firm': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'location': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'farmer': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'category': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'product': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'price_per_unit': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0.01'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'step': '0.01',
                'min': '0.01'
            }),
            'unit': forms.Select(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default date to today
        if not self.instance.pk:
            self.fields['date'].initial = timezone.now().date()
            self.fields['unit'].initial = 'kg'
        
        # Filter querysets based on user permissions
        if self.user:
            self._setup_user_specific_querysets()
    
    def _setup_user_specific_querysets(self):
        """Setup querysets based on user's permissions and firm"""
        if not self.user or not hasattr(self.user, 'profile'):
            return
        
        user_profile = self.user.profile
        
        # Non-admin users see only their firm
        if not user_profile.is_admin():
            if user_profile.firm:
                self.fields['firm'].queryset = Firm.objects.filter(id=user_profile.firm.id)
                self.fields['firm'].initial = user_profile.firm
                self.fields['firm'].widget.attrs['readonly'] = True
        
        # Buyers can only submit for their allowed categories
        if user_profile.is_buyer() and hasattr(user_profile, 'buyer_profile'):
            allowed_categories = user_profile.buyer_profile.allowed_categories.all()
            if allowed_categories:
                self.fields['category'].queryset = allowed_categories
        
        # Update product choices when category is selected (handled by JS in template)
        
    def clean_price_per_unit(self):
        """Validate price per unit"""
        price = self.cleaned_data.get('price_per_unit')
        if price is not None and price <= 0:
            raise ValidationError("Price per unit must be greater than 0")
        return price
    
    def clean_quantity(self):
        """Validate quantity"""
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        return quantity
    
    def clean_date(self):
        """Validate submission date"""
        date = self.cleaned_data.get('date')
        if date:
            # Don't allow future dates beyond tomorrow
            max_date = timezone.now().date() + timezone.timedelta(days=1)
            if date > max_date:
                raise ValidationError("Cannot submit prices for dates more than 1 day in the future")
            
            # Don't allow dates too far in the past (e.g., more than 30 days)
            min_date = timezone.now().date() - timezone.timedelta(days=30)
            if date < min_date:
                raise ValidationError("Cannot submit prices for dates more than 30 days in the past")
        
        return date
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        category = cleaned_data.get('category')
        farmer = cleaned_data.get('farmer')
        location = cleaned_data.get('location')
        
        # Ensure product belongs to selected category
        if product and category and product.category != category:
            raise ValidationError({
                'product': f'Product "{product.name}" does not belong to category "{category.name}"'
            })
        
        # Ensure farmer belongs to selected location
        if farmer and location and farmer.location != location:
            raise ValidationError({
                'farmer': f'Farmer "{farmer.name}" is not from location "{location.name}"'
            })
        
        # Check for duplicate submissions (same buyer, same day, same product details)
        if self.user and not self.instance.pk:  # Only for new submissions
            existing = PriceSubmission.objects.filter(
                date=cleaned_data.get('date'),
                firm=cleaned_data.get('firm'),
                category=category,
                product=product,
                farmer=farmer,
                buyer=self.user,
                price_per_unit=cleaned_data.get('price_per_unit'),
                quantity=cleaned_data.get('quantity')
            ).exists()
            
            if existing:
                raise ValidationError(
                    "A submission with identical details already exists for this date."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the form with buyer information"""
        submission = super().save(commit=False)
        
        if self.user:
            submission.buyer = self.user
        
        if commit:
            submission.save()
        
        return submission


class PriceSubmissionFilterForm(forms.Form):
    """Form for filtering price submissions"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    firm = forms.ModelChoiceField(
        queryset=Firm.objects.all(),
        required=False,
        empty_label="All Firms",
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.all(),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        empty_label="All Products",
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    location = forms.ModelChoiceField(
        queryset=Location.objects.all(),
        required=False,
        empty_label="All Locations",
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    farmer = forms.ModelChoiceField(
        queryset=Farmer.objects.all(),
        required=False,
        empty_label="All Farmers",
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + PriceSubmission.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm',
            'placeholder': 'Search by farmer name, notes, or buyer...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and hasattr(user, 'profile'):
            self._setup_user_specific_querysets(user.profile)
    
    def _setup_user_specific_querysets(self, user_profile):
        """Limit choices based on user's permissions"""
        if not user_profile.is_admin():
            # Non-admin users see only their firm
            if user_profile.firm:
                self.fields['firm'].queryset = Firm.objects.filter(id=user_profile.firm.id)
                self.fields['firm'].initial = user_profile.firm
        
        # Category heads and buyers see only their allowed categories
        if user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
            scoped_categories = user_profile.category_head_profile.scoped_categories.all()
            if scoped_categories:
                self.fields['category'].queryset = scoped_categories
                # Update products based on these categories
                self.fields['product'].queryset = Product.objects.filter(category__in=scoped_categories)
        
        elif user_profile.is_buyer() and hasattr(user_profile, 'buyer_profile'):
            allowed_categories = user_profile.buyer_profile.allowed_categories.all()
            if allowed_categories:
                self.fields['category'].queryset = allowed_categories
                # Update products based on these categories
                self.fields['product'].queryset = Product.objects.filter(category__in=allowed_categories)
        
        # Filter farmers based on user's assigned location if applicable
        if hasattr(user_profile, 'assigned_location') and user_profile.assigned_location:
            self.fields['farmer'].queryset = Farmer.objects.filter(location=user_profile.assigned_location)