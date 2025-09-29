"""
Bulk price entry views with Excel-like grid interface.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
import json
from decimal import Decimal

from ..models import (
    PriceSubmission, Product, ProductCategory, MainCategory, SubCategory,
    Location, Farmer, Firm, UserProfile
)


class BulkPriceEntryView(LoginRequiredMixin, TemplateView):
    """Excel-like bulk price entry interface"""
    template_name = 'core/submissions/bulk_entry.html'
    
    def dispatch(self, request, *args, **kwargs):
        """Ensure only buyers can access this view"""
        if not hasattr(request.user, 'profile') or not request.user.profile.is_buyer():
            messages.error(request, "Only buyers can access the bulk price entry.")
            return redirect('core:submission_list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Prepare context for Excel-like grid"""
        context = super().get_context_data(**kwargs)
        
        # Get user's firm and allowed categories
        user_profile = self.request.user.profile
        firm = user_profile.firm
        
        # Get allowed categories for buyer
        allowed_categories = []
        if hasattr(user_profile, 'buyer_profile'):
            allowed_categories = user_profile.buyer_profile.allowed_categories.all()
        else:
            # If no specific categories, allow all
            allowed_categories = ProductCategory.objects.all()
        
        # Get products from allowed categories
        products = Product.objects.filter(
            category__in=allowed_categories
        ).select_related('category', 'main_category', 'sub_category').order_by(
            'category__name', 'sub_category__name', 'name'
        )
        
        # Generate date range (current week + next week)
        today = timezone.now().date()
        start_date = today - timedelta(days=today.weekday())  # Monday of current week
        date_range = [start_date + timedelta(days=i) for i in range(14)]  # 2 weeks
        
        # Get farmers with their locations
        farmers = Farmer.objects.select_related('location').order_by('location__name', 'name')
        
        # Get existing submissions for the date range
        existing_submissions = PriceSubmission.objects.filter(
            date__range=[start_date, start_date + timedelta(days=13)],
            buyer=self.request.user,
            firm=firm
        ).select_related('product', 'farmer')
        
        # Create lookup dictionary for existing prices
        existing_prices = {}
        for submission in existing_submissions:
            key = f"{submission.date}_{submission.product.id}_{submission.farmer.id}"
            existing_prices[key] = {
                'price': submission.price_per_unit,
                'quantity': submission.quantity,
                'unit': submission.unit,
                'submission_id': submission.id,
                'status': submission.status
            }
        
        # Get hierarchical categories
        main_categories = MainCategory.objects.all().order_by('name')
        sub_categories = SubCategory.objects.filter(
            category__in=allowed_categories
        ).select_related('category', 'main_category').order_by('category__name', 'name')
        
        context.update({
            'firm': firm,
            'products': products,
            'farmers': farmers,
            'date_range': date_range,
            'existing_prices': existing_prices,
            'categories': allowed_categories,
            'main_categories': main_categories,
            'sub_categories': sub_categories,
            'units': PriceSubmission.UNIT_CHOICES,
        })
        
        return context


@login_required
@csrf_exempt
def bulk_save_prices(request):
    """Save bulk price entries from Excel-like grid"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    # Check if user is buyer
    if not hasattr(request.user, 'profile') or not request.user.profile.is_buyer():
        return JsonResponse({'success': False, 'error': 'Only buyers can submit prices'})
    
    try:
        data = json.loads(request.body)
        entries = data.get('entries', [])
        
        if not entries:
            return JsonResponse({'success': False, 'error': 'No entries to save'})
        
        user_profile = request.user.profile
        firm = user_profile.firm
        
        saved_count = 0
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            for entry in entries:
                try:
                    # Parse entry data
                    date_str = entry.get('date')
                    product_id = entry.get('product_id')
                    farmer_id = entry.get('farmer_id')
                    price = entry.get('price')
                    quantity = entry.get('quantity', 1)
                    unit = entry.get('unit', 'kg')
                    
                    # Validate required fields
                    if not all([date_str, product_id, farmer_id, price]):
                        continue
                    
                    # Parse date
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    
                    # Get related objects
                    product = Product.objects.get(id=product_id)
                    farmer = Farmer.objects.get(id=farmer_id)
                    
                    # Check if submission already exists
                    existing = PriceSubmission.objects.filter(
                        date=date,
                        product=product,
                        farmer=farmer,
                        buyer=request.user,
                        firm=firm
                    ).first()
                    
                    if existing:
                        # Update existing submission if it's still pending
                        if existing.status == 'PENDING':
                            existing.price_per_unit = Decimal(str(price))
                            existing.quantity = Decimal(str(quantity))
                            existing.unit = unit
                            existing.save()
                            updated_count += 1
                        else:
                            errors.append(f"Cannot update {product.name} for {date} - already {existing.status.lower()}")
                    else:
                        # Create new submission
                        PriceSubmission.objects.create(
                            date=date,
                            firm=firm,
                            location=farmer.location,  # Location comes from farmer
                            farmer=farmer,
                            buyer=request.user,
                            category=product.category,
                            product=product,
                            price_per_unit=Decimal(str(price)),
                            quantity=Decimal(str(quantity)),
                            unit=unit
                        )
                        saved_count += 1
                        
                except Exception as e:
                    errors.append(f"Error processing entry: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'saved_count': saved_count,
            'updated_count': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def get_products_by_category(request):
    """Get products filtered by category for dynamic loading"""
    category_id = request.GET.get('category_id')
    
    if not category_id:
        return JsonResponse({'products': []})
    
    try:
        # Get user's allowed categories
        user_profile = request.user.profile
        allowed_categories = []
        
        if hasattr(user_profile, 'buyer_profile'):
            allowed_categories = user_profile.buyer_profile.allowed_categories.all()
        else:
            allowed_categories = ProductCategory.objects.all()
        
        # Check if requested category is allowed
        if not allowed_categories.filter(id=category_id).exists():
            return JsonResponse({'products': []})
        
        products = Product.objects.filter(category_id=category_id).order_by('name')
        products_data = [
            {'id': p.id, 'name': p.name}
            for p in products
        ]
        
        return JsonResponse({'products': products_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)})


@login_required
def get_farmers_by_location(request):
    """Get farmers filtered by location"""
    location_id = request.GET.get('location_id')
    
    if not location_id:
        farmers = Farmer.objects.select_related('location').order_by('location__name', 'name')
    else:
        farmers = Farmer.objects.filter(location_id=location_id).order_by('name')
    
    farmers_data = [
        {
            'id': f.id, 
            'name': f.name,
            'location': f.location.name,
            'location_id': f.location.id
        }
        for f in farmers
    ]
    
    return JsonResponse({'farmers': farmers_data})