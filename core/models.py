"""
Core models for Kannammal Agro application.
Handles firms, locations, farmers, products, users, and price submissions.
"""

from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class Firm(models.Model):
    """Represents agro firms like Ramachandran, Jeyachandran"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(models.Model):
    """Represents locations where farmers operate"""
    name = models.CharField(max_length=100)
    region_code = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'region_code']
    
    def __str__(self):
        return f"{self.name} ({self.region_code})"


class Farmer(models.Model):
    """Represents farmers who supply produce"""
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='farmers')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.location.name}"


class ProductCategory(models.Model):
    """Product categories like Fruits, Vegetables"""
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = "Product Categories"
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Product(models.Model):
    """Individual products like Apple, Banana, Tomato"""
    name = models.CharField(max_length=100)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category__name', 'name']
        unique_together = ['name', 'category']
    
    def __str__(self):
        return f"{self.name} ({self.category.name})"


class UserProfile(models.Model):
    """Extended user profile with firm association"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, null=True, blank=True, 
                           help_text="Leave blank for admin users")
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.username} - {self.firm.name if self.firm else 'Admin'}"
    
    def get_role_display(self):
        """Get user's primary role from groups"""
        groups = self.user.groups.all()
        if groups:
            return groups.first().name
        return "No Role"
    
    @property
    def role(self):
        """Get user's primary role code for template usage"""
        groups = self.user.groups.all()
        if groups:
            return groups.first().name
        return None
    
    def is_admin(self):
        """Check if user is admin (superuser or in ADMIN group)"""
        return self.user.is_superuser or self.user.groups.filter(name='ADMIN').exists()
    
    def is_business_head(self):
        """Check if user is business head"""
        return self.user.groups.filter(name='BUSINESS_HEAD').exists()
    
    def is_category_head(self):
        """Check if user is category head"""
        return self.user.groups.filter(name='CATEGORY_HEAD').exists()
    
    def is_buyer(self):
        """Check if user is buyer"""
        return self.user.groups.filter(name='BUYER').exists()


class BuyerProfile(models.Model):
    """Profile for buyers with category permissions and region assignment"""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='buyer_profile')
    assigned_location = models.ForeignKey(Location, on_delete=models.CASCADE, null=True, blank=True,
                                        help_text="Region/Location this buyer is responsible for")
    allowed_categories = models.ManyToManyField(ProductCategory, blank=True,
                                              help_text="Categories this buyer can submit prices for")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user_profile__user__username']
    
    def __str__(self):
        return f"Buyer: {self.user_profile.user.username}"


class CategoryHeadProfile(models.Model):
    """Profile for category heads with scoped categories"""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='category_head_profile')
    scoped_categories = models.ManyToManyField(ProductCategory, blank=True,
                                             help_text="Categories this head can view and manage")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user_profile__user__username']
    
    def __str__(self):
        return f"Category Head: {self.user_profile.user.username}"


class BusinessHeadProfile(models.Model):
    """Profile for business heads"""
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='business_head_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user_profile__user__username']
    
    def __str__(self):
        return f"Business Head: {self.user_profile.user.username}"


class PriceSubmission(models.Model):
    """Main model for price submissions by buyers"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    UNIT_CHOICES = [
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('ton', 'Ton'),
        ('piece', 'Piece'),
        ('dozen', 'Dozen'),
        ('box', 'Box'),
        ('sack', 'Sack'),
    ]
    
    # Basic information
    date = models.DateField(default=timezone.now)
    firm = models.ForeignKey(Firm, on_delete=models.CASCADE, related_name='price_submissions')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='price_submissions')
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='price_submissions')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_submissions')
    
    # Product information
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='price_submissions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_submissions')
    
    # Price and quantity
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, 
                                       validators=[MinValueValidator(Decimal('0.01'))])
    quantity = models.DecimalField(max_digits=10, decimal_places=2,
                                 validators=[MinValueValidator(Decimal('0.01'))])
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='kg')
    
    # Additional information
    notes = models.TextField(blank=True, help_text="Additional notes about the submission")
    
    # Status and approval tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='approved_submissions')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_version = models.PositiveIntegerField(default=0,
                                                 help_text="Increments on each approve/cancel toggle")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        # Prevent exact duplicates
        unique_together = ['date', 'firm', 'category', 'product', 'farmer', 'buyer', 
                          'price_per_unit', 'quantity']
        indexes = [
            models.Index(fields=['date', 'firm', 'category']),
            models.Index(fields=['status']),
            models.Index(fields=['buyer']),
            models.Index(fields=['approved_by']),
        ]
    
    def __str__(self):
        return (f"{self.product.name} - ₹{self.price_per_unit}/{self.unit} "
                f"by {self.buyer.username} on {self.date}")
    
    def clean(self):
        """Validate the model"""
        super().clean()
        
        # Ensure product belongs to the selected category
        if self.product and self.category:
            if self.product.category != self.category:
                raise ValidationError({
                    'product': f'Product {self.product.name} does not belong to category {self.category.name}'
                })
        
        # Ensure farmer belongs to the selected location
        if self.farmer and self.location:
            if self.farmer.location != self.location:
                raise ValidationError({
                    'farmer': f'Farmer {self.farmer.name} is not from location {self.location.name}'
                })
    
    def save(self, *args, **kwargs):
        """Override save to run clean validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def total_value(self):
        """Calculate total value of this submission"""
        return self.price_per_unit * self.quantity
    
    def can_edit(self, user):
        """Check if user can edit this submission"""
        # Only buyers can edit their own pending submissions, or admins
        if user.is_superuser:
            return True
        
        # Buyer can edit only their own pending submissions
        if self.buyer == user and self.status == 'PENDING':
            return True
        
        return False
    
    def can_approve(self, user):
        """Check if user can approve this submission"""
        # Only business heads and admins can approve
        if user.is_superuser:
            return True
        
        if hasattr(user, 'profile'):
            return user.profile.is_business_head()
        
        return False