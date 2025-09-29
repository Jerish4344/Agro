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


# Bulk Upload Views
import csv
import io
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ..models import Product, ProductCategory, MainCategory, SubCategory


def is_admin_or_superuser(user):
    """Check if user is admin or superuser"""
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'admin')


@login_required
@user_passes_test(is_admin_or_superuser)
def bulk_upload_products(request):
    """Bulk upload products from CSV file"""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'No CSV file provided.')
            return render(request, 'core/utilities/bulk_upload_products.html')
        
        csv_file = request.FILES['csv_file']
        
        # Validate file type
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return render(request, 'core/utilities/bulk_upload_products.html')
        
        # Process the CSV file
        try:
            # Read the CSV content
            file_content = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_content))
            
            # Validate headers
            expected_headers = ['Name', 'Category', 'Main Cat.', 'Sub Cat']
            if not all(header in csv_reader.fieldnames for header in expected_headers):
                messages.error(request, f'CSV file must contain headers: {", ".join(expected_headers)}')
                return render(request, 'core/utilities/bulk_upload_products.html')
            
            # Convert to list to process
            products_data = list(csv_reader)
            
            if not products_data:
                messages.error(request, 'CSV file is empty or has no data rows.')
                return render(request, 'core/utilities/bulk_upload_products.html')
            
            # Get options from form
            clear_existing = request.POST.get('clear_existing') == 'on'
            dry_run = request.POST.get('dry_run') == 'on'
            
            # Process the products
            result = process_products_csv(products_data, clear_existing=clear_existing, dry_run=dry_run)
            
            if dry_run:
                messages.info(request, f"DRY RUN: Would process {len(products_data)} products. {result['summary']}")
            else:
                if result['errors']:
                    messages.warning(request, f"Import completed with {len(result['errors'])} errors. {result['summary']}")
                else:
                    messages.success(request, f"Successfully imported products! {result['summary']}")
            
            # Store detailed results in session for display
            request.session['upload_results'] = result
            return redirect('core:bulk_upload_results')
            
        except Exception as e:
            messages.error(request, f'Error processing CSV file: {str(e)}')
    
    return render(request, 'core/utilities/bulk_upload_products.html')


@login_required
@user_passes_test(is_admin_or_superuser)
def bulk_upload_results(request):
    """Display results of bulk upload"""
    results = request.session.get('upload_results', {})
    if not results:
        messages.info(request, 'No upload results to display.')
        return redirect('core:bulk_upload_products')
    
    # Clear results from session after displaying
    if 'upload_results' in request.session:
        del request.session['upload_results']
    
    return render(request, 'core/utilities/bulk_upload_results.html', {'results': results})


def process_products_csv(products_data, clear_existing=False, dry_run=False):
    """Process products CSV data and return results"""
    stats = {
        'categories_created': 0,
        'main_categories_created': 0,
        'sub_categories_created': 0,
        'products_created': 0,
        'products_updated': 0,
        'errors': [],
        'processed_products': []
    }
    
    try:
        with transaction.atomic():
            # Clear existing products if requested
            if clear_existing and not dry_run:
                Product.objects.all().delete()
            
            for row_num, row in enumerate(products_data, start=2):
                try:
                    name = row['Name'].strip()
                    category_name = row['Category'].strip()
                    main_cat_name = row['Main Cat.'].strip()
                    sub_cat_name = row['Sub Cat'].strip()
                    
                    if not all([name, category_name, main_cat_name, sub_cat_name]):
                        stats['errors'].append(f"Row {row_num}: Missing required fields")
                        continue
                    
                    if dry_run:
                        stats['processed_products'].append({
                            'name': name,
                            'category': category_name,
                            'main_category': main_cat_name,
                            'sub_category': sub_cat_name,
                            'action': 'would_process'
                        })
                        continue
                    
                    # Get or create Category
                    category, created = ProductCategory.objects.get_or_create(
                        name=category_name,
                        defaults={'code': category_name.replace(' ', '_').lower()}
                    )
                    if created:
                        stats['categories_created'] += 1
                    
                    # Get or create Main Category
                    main_category, created = MainCategory.objects.get_or_create(
                        name=main_cat_name,
                        defaults={
                            'code': main_cat_name.replace(' ', '_').lower(),
                            'description': f'{main_cat_name} in {category_name}'
                        }
                    )
                    if created:
                        stats['main_categories_created'] += 1
                    
                    # Get or create Sub Category
                    sub_category, created = SubCategory.objects.get_or_create(
                        name=sub_cat_name,
                        category=category,
                        main_category=main_category,
                        defaults={
                            'code': sub_cat_name.replace(' ', '_').lower(),
                            'description': f'{sub_cat_name} in {main_cat_name}'
                        }
                    )
                    if created:
                        stats['sub_categories_created'] += 1
                    
                    # Create or update Product
                    product, created = Product.objects.get_or_create(
                        name=name,
                        defaults={
                            'category': category,
                            'main_category': main_category,
                            'sub_category': sub_category
                        }
                    )
                    
                    if created:
                        stats['products_created'] += 1
                        action = 'created'
                    else:
                        # Update existing product
                        product.category = category
                        product.main_category = main_category
                        product.sub_category = sub_category
                        product.save()
                        stats['products_updated'] += 1
                        action = 'updated'
                    
                    stats['processed_products'].append({
                        'name': name,
                        'category': category_name,
                        'main_category': main_cat_name,
                        'sub_category': sub_cat_name,
                        'action': action
                    })
                    
                except Exception as e:
                    error_msg = f"Row {row_num}: Error processing '{row.get('Name', 'Unknown')}' - {str(e)}"
                    stats['errors'].append(error_msg)
                    continue
    
    except Exception as e:
        stats['errors'].append(f"Database error: {str(e)}")
    
    # Generate summary
    total_processed = stats['products_created'] + stats['products_updated']
    stats['summary'] = (
        f"Categories: {stats['categories_created']} created, "
        f"Main Categories: {stats['main_categories_created']} created, "
        f"Sub Categories: {stats['sub_categories_created']} created, "
        f"Products: {stats['products_created']} created, {stats['products_updated']} updated"
    )
    
    return stats