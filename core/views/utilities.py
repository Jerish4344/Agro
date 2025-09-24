"""
Utility functions for views, permissions, and common operations.
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import QuerySet
from functools import wraps

from ..models import PriceSubmission, UserProfile


def user_passes_test_with_message(test_func, message="Access denied", redirect_url='core:dashboard'):
    """
    Decorator for views that checks if user passes a test with custom message.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, message)
                return redirect(redirect_url)
        return wrapper
    return decorator


def is_buyer(user):
    """Check if user is a buyer"""
    return hasattr(user, 'profile') and user.profile.is_buyer()


def is_category_head(user):
    """Check if user is a category head"""
    return hasattr(user, 'profile') and user.profile.is_category_head()


def is_business_head(user):
    """Check if user is a business head"""
    return hasattr(user, 'profile') and user.profile.is_business_head()


def is_admin(user):
    """Check if user is an admin"""
    return hasattr(user, 'profile') and user.profile.is_admin()


def can_approve_submissions(user):
    """Check if user can approve submissions"""
    return is_business_head(user) or is_admin(user)


def buyer_required(message="Only buyers can access this page"):
    """Decorator to require buyer role"""
    return user_passes_test_with_message(is_buyer, message)


def category_head_required(message="Only category heads can access this page"):
    """Decorator to require category head role"""
    return user_passes_test_with_message(is_category_head, message)


def business_head_required(message="Only business heads can access this page"):
    """Decorator to require business head role"""
    return user_passes_test_with_message(is_business_head, message)


def admin_required(message="Only administrators can access this page"):
    """Decorator to require admin role"""
    return user_passes_test_with_message(is_admin, message)


def approval_permission_required(message="You don't have permission to approve submissions"):
    """Decorator to require approval permissions"""
    return user_passes_test_with_message(can_approve_submissions, message)


def get_user_scoped_submissions(user: User) -> QuerySet:
    """
    Get submissions queryset scoped to user's permissions.
    
    Args:
        user: User to scope submissions for
        
    Returns:
        QuerySet of PriceSubmission objects the user can access
    """
    if not hasattr(user, 'profile'):
        return PriceSubmission.objects.none()
    
    user_profile = user.profile
    queryset = PriceSubmission.objects.all()
    
    # Admin can see everything
    if user_profile.is_admin():
        return queryset
    
    # Filter by firm for non-admin users
    if user_profile.firm:
        queryset = queryset.filter(firm=user_profile.firm)
    else:
        return PriceSubmission.objects.none()
    
    # Additional role-based filtering
    if user_profile.is_buyer():
        # Buyers can only see their own submissions
        queryset = queryset.filter(buyer=user)
    
    elif user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
        # Category heads can see submissions in their scoped categories
        scoped_categories = user_profile.category_head_profile.scoped_categories.all()
        if scoped_categories:
            queryset = queryset.filter(category__in=scoped_categories)
        else:
            return PriceSubmission.objects.none()
    
    # Business heads can see all submissions in their firm (no additional filtering needed)
    
    return queryset


def get_user_allowed_categories(user: User):
    """
    Get categories that the user is allowed to work with.
    
    Args:
        user: User to get categories for
        
    Returns:
        QuerySet of ProductCategory objects
    """
    if not hasattr(user, 'profile'):
        from ..models import ProductCategory
        return ProductCategory.objects.none()
    
    user_profile = user.profile
    
    # Admin can work with all categories
    if user_profile.is_admin():
        from ..models import ProductCategory
        return ProductCategory.objects.all()
    
    # Buyer's allowed categories
    if user_profile.is_buyer() and hasattr(user_profile, 'buyer_profile'):
        return user_profile.buyer_profile.allowed_categories.all()
    
    # Category head's scoped categories
    if user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
        return user_profile.category_head_profile.scoped_categories.all()
    
    # Business head can work with all categories in their firm
    if user_profile.is_business_head():
        from ..models import ProductCategory
        return ProductCategory.objects.all()
    
    # Default: no categories
    from ..models import ProductCategory
    return ProductCategory.objects.none()


def annotate_price_highlights(queryset, group_by_location=False):
    """
    Annotate queryset with min/max price highlighting information.
    
    Args:
        queryset: QuerySet of PriceSubmission objects
        group_by_location: Whether to group by location as well
        
    Returns:
        QuerySet with is_min_price and is_max_price annotations
    """
    from ..services.reporting_service import ReportingService
    return ReportingService.get_price_submissions_with_highlights(
        queryset, group_by_location
    )


def format_price(price):
    """Format price for display"""
    if price is None:
        return "₹0.00"
    return f"₹{price:,.2f}"


def format_quantity(quantity, unit):
    """Format quantity with unit for display"""
    if quantity is None:
        return "0"
    return f"{quantity:,.2f} {unit}"


def get_status_badge_class(status):
    """Get CSS class for status badge"""
    status_classes = {
        'PENDING': 'bg-yellow-100 text-yellow-800',
        'APPROVED': 'bg-green-100 text-green-800',
        'CANCELLED': 'bg-red-100 text-red-800'
    }
    return status_classes.get(status, 'bg-gray-100 text-gray-800')


def get_role_badge_class(role):
    """Get CSS class for role badge"""
    role_classes = {
        'BUYER': 'bg-blue-100 text-blue-800',
        'CATEGORY_HEAD': 'bg-purple-100 text-purple-800',
        'BUSINESS_HEAD': 'bg-indigo-100 text-indigo-800',
        'ADMIN': 'bg-red-100 text-red-800'
    }
    return role_classes.get(role, 'bg-gray-100 text-gray-800')


def check_submission_permissions(user, submission, action='view'):
    """
    Check if user has permission to perform action on submission.
    
    Args:
        user: User to check permissions for
        submission: PriceSubmission object
        action: Action to check ('view', 'edit', 'delete', 'approve')
        
    Returns:
        tuple: (has_permission: bool, error_message: str)
    """
    if not hasattr(user, 'profile'):
        return False, "User profile not found"
    
    user_profile = user.profile
    
    # Admin can do everything
    if user_profile.is_admin():
        return True, ""
    
    # Check firm access
    if user_profile.firm and submission.firm != user_profile.firm:
        return False, "You can only access submissions from your firm"
    
    if action == 'view':
        # Category heads can view submissions in their categories
        if user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
            scoped_categories = user_profile.category_head_profile.scoped_categories.all()
            if scoped_categories and submission.category not in scoped_categories:
                return False, "You can only view submissions in your assigned categories"
        
        # Buyers can view their own submissions
        if user_profile.is_buyer() and submission.buyer != user:
            return False, "You can only view your own submissions"
    
    elif action == 'edit':
        # Only buyers can edit their own pending submissions
        if not user_profile.is_buyer():
            return False, "Only buyers can edit submissions"
        
        if submission.buyer != user:
            return False, "You can only edit your own submissions"
        
        if submission.status != 'PENDING':
            return False, "You can only edit pending submissions"
    
    elif action == 'delete':
        # Buyers can delete their own pending submissions
        if user_profile.is_buyer():
            if submission.buyer != user:
                return False, "You can only delete your own submissions"
            
            if submission.status != 'PENDING':
                return False, "You can only delete pending submissions"
        else:
            return False, "Only buyers can delete submissions"
    
    elif action == 'approve':
        # Only business heads can approve
        if not user_profile.is_business_head():
            return False, "Only business heads can approve submissions"
    
    return True, ""