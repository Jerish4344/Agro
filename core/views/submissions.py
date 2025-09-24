"""
Views for price submission CRUD operations.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from datetime import datetime, timedelta
import json
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from datetime import datetime
import json
from decimal import Decimal

from ..models import PriceSubmission, Product, ProductCategory, Location, Farmer, Firm, UserProfile
from ..forms import BuyerSubmissionForm, PriceSubmissionFilterForm
from ..services.reporting_service import ReportingService


class SubmissionListView(LoginRequiredMixin, ListView):
    """List view for price submissions with filtering"""
    model = PriceSubmission
    template_name = 'core/submissions/list.html'
    context_object_name = 'submissions'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        """Redirect business heads to their dashboard when accessing submissions"""
        if hasattr(request.user, 'profile') and request.user.profile.is_business_head():
            from django.urls import reverse
            from django.shortcuts import redirect
            return redirect(reverse('core:business_head_submission'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        """Filter submissions based on user permissions and form filters"""
        user_profile = self.request.user.profile
        
        # Base queryset with optimizations
        queryset = PriceSubmission.objects.select_related(
            'firm', 'product', 'category', 'location', 'farmer', 'buyer', 'approved_by'
        ).order_by('-date', '-created_at')
        
        # Apply user-based filtering
        if not user_profile.is_admin():
            # Filter by firm
            if user_profile.firm:
                queryset = queryset.filter(firm=user_profile.firm)
            
            # Additional role-based filtering
            if user_profile.is_buyer():
                # Buyers see only their own submissions
                queryset = queryset.filter(buyer=self.request.user)
            
            elif user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
                # Category heads see submissions in their categories
                scoped_categories = user_profile.category_head_profile.scoped_categories.all()
                if scoped_categories:
                    queryset = queryset.filter(category__in=scoped_categories)
        
        # Apply form filters
        self.filter_form = PriceSubmissionFilterForm(
            self.request.GET, 
            user=self.request.user
        )
        
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            
            if data.get('date_from'):
                queryset = queryset.filter(date__gte=data['date_from'])
            
            if data.get('date_to'):
                queryset = queryset.filter(date__lte=data['date_to'])
            
            if data.get('firm'):
                queryset = queryset.filter(firm=data['firm'])
            
            if data.get('category'):
                queryset = queryset.filter(category=data['category'])
            
            if data.get('product'):
                queryset = queryset.filter(product=data['product'])
            
            if data.get('location'):
                queryset = queryset.filter(location=data['location'])
            
            if data.get('farmer'):
                queryset = queryset.filter(farmer=data['farmer'])
            
            if data.get('status'):
                queryset = queryset.filter(status=data['status'])
            
            if data.get('search'):
                search_term = data['search']
                queryset = queryset.filter(
                    Q(farmer__name__icontains=search_term) |
                    Q(notes__icontains=search_term) |
                    Q(buyer__username__icontains=search_term) |
                    Q(buyer__first_name__icontains=search_term) |
                    Q(buyer__last_name__icontains=search_term)
                )
        
        # Add highlighting annotations
        queryset = ReportingService.get_price_submissions_with_highlights(queryset)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = getattr(self, 'filter_form', 
                                       PriceSubmissionFilterForm(user=self.request.user))
        context['user_profile'] = self.request.user.profile
        
        # Add categories with submission counts for tabs
        user_profile = self.request.user.profile
        if user_profile.is_category_head():
            # Category heads only see their assigned categories
            if hasattr(user_profile, 'category_head_profile'):
                scoped_categories = user_profile.category_head_profile.scoped_categories.all()
            else:
                scoped_categories = ProductCategory.objects.none()
        else:
            # Others see all categories
            scoped_categories = ProductCategory.objects.all()
        
        # Annotate categories with submission counts
        from django.db.models import Count
        categories_with_counts = []
        for category in scoped_categories:
            # Apply same filters as queryset but for specific category
            category_submissions = PriceSubmission.objects.filter(category=category)
            
            # Apply role-based filtering
            if user_profile.is_buyer():
                category_submissions = category_submissions.filter(buyer=self.request.user)
            elif user_profile.is_category_head():
                if hasattr(user_profile, 'category_head_profile'):
                    scoped_cats = user_profile.category_head_profile.scoped_categories.all()
                    if category in scoped_cats:
                        pass  # Category head can see all submissions in their category
                    else:
                        category_submissions = category_submissions.none()
                else:
                    category_submissions = category_submissions.none()
            # BUSINESS_HEAD and ADMIN see all
            
            # Apply form filters
            if hasattr(self, 'filter_form') and self.filter_form.is_valid():
                data = self.filter_form.cleaned_data
                
                if data.get('date_from'):
                    category_submissions = category_submissions.filter(date__gte=data['date_from'])
                
                if data.get('date_to'):
                    category_submissions = category_submissions.filter(date__lte=data['date_to'])
                
                if data.get('firm'):
                    category_submissions = category_submissions.filter(firm=data['firm'])
                
                if data.get('product'):
                    category_submissions = category_submissions.filter(product=data['product'])
                
                if data.get('product'):
                    category_submissions = category_submissions.filter(product=data['product'])
                
                if data.get('location'):
                    category_submissions = category_submissions.filter(location=data['location'])
                
                if data.get('farmer'):
                    category_submissions = category_submissions.filter(farmer=data['farmer'])
                
                if data.get('status'):
                    category_submissions = category_submissions.filter(status=data['status'])
                
                if data.get('search'):
                    search_term = data['search']
                    category_submissions = category_submissions.filter(
                        Q(farmer__name__icontains=search_term) |
                        Q(notes__icontains=search_term) |
                        Q(buyer__username__icontains=search_term) |
                        Q(buyer__first_name__icontains=search_term) |
                        Q(buyer__last_name__icontains=search_term)
                    )
            
            category.submission_count = category_submissions.count()
            categories_with_counts.append(category)
        
        context['categories'] = categories_with_counts
        
        # Add farmers for the filter dropdown (filtered by user's location if applicable)
        farmers_queryset = Farmer.objects.all()
        user_profile = self.request.user.profile
        if hasattr(user_profile, 'assigned_location') and user_profile.assigned_location:
            farmers_queryset = farmers_queryset.filter(location=user_profile.assigned_location)
        context['farmers'] = farmers_queryset.order_by('name')
        
        # Add products for the filter dropdown
        context['products'] = Product.objects.all().order_by('name')
        
        return context


class SubmissionCreateView(LoginRequiredMixin, CreateView):
    """Create view for price submissions (buyers only)"""
    model = PriceSubmission
    form_class = BuyerSubmissionForm
    template_name = 'core/submissions/create.html'
    context_object_name = 'submission'
    success_url = reverse_lazy('core:submission_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user can create submissions"""
        if not hasattr(request.user, 'profile'):
            messages.error(request, "User profile not found.")
            return redirect('core:dashboard')
        
        user_profile = request.user.profile
        if not (user_profile.is_buyer() or user_profile.is_admin()):
            messages.error(request, "Only buyers can create price submissions.")
            return redirect('core:dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Price submission created successfully.")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group products by category for dropdown
        from collections import defaultdict
        products_by_category = defaultdict(list)
        categories = ProductCategory.objects.prefetch_related('products').all()
        for category in categories:
            products_by_category[category] = list(category.products.all())
        
        # Group farmers by location for dropdown
        farmers_by_location = defaultdict(list)
        locations = Location.objects.prefetch_related('farmers').all()
        for location in locations:
            farmers_by_location[location] = list(location.farmers.all())
        
        # Get all firms for dropdown
        firms = Firm.objects.all()
        
        context['products_by_category'] = dict(products_by_category)
        context['farmers_by_location'] = dict(farmers_by_location)
        context['firms'] = firms
        
        return context


class SubmissionUpdateView(LoginRequiredMixin, UpdateView):
    """Update view for price submissions"""
    model = PriceSubmission
    form_class = BuyerSubmissionForm
    template_name = 'core/submissions/edit.html'
    context_object_name = 'submission'
    success_url = reverse_lazy('core:submission_list')
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user can edit this submission"""
        submission = self.get_object()
        
        if not submission.can_edit(request.user):
            messages.error(request, "You don't have permission to edit this submission.")
            return redirect('core:submission_list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, "Price submission updated successfully.")
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Group products by category for dropdown
        from collections import defaultdict
        products_by_category = defaultdict(list)
        categories = ProductCategory.objects.prefetch_related('products').all()
        for category in categories:
            products_by_category[category] = list(category.products.all())
        
        # Group farmers by location for dropdown
        farmers_by_location = defaultdict(list)
        locations = Location.objects.prefetch_related('farmers').all()
        for location in locations:
            farmers_by_location[location] = list(location.farmers.all())
        
        # Get all firms for dropdown
        firms = Firm.objects.all()
        
        context['products_by_category'] = dict(products_by_category)
        context['farmers_by_location'] = dict(farmers_by_location)
        context['firms'] = firms
        
        return context


class SubmissionDetailView(LoginRequiredMixin, DetailView):
    """Detail view for price submissions"""
    model = PriceSubmission
    template_name = 'core/submissions/detail.html'
    context_object_name = 'submission'
    
    def get_queryset(self):
        """Filter based on user permissions"""
        user_profile = self.request.user.profile
        queryset = PriceSubmission.objects.select_related(
            'firm', 'product', 'category', 'location', 'farmer', 'buyer', 'approved_by'
        )
        
        if not user_profile.is_admin():
            # Non-admin users can only see submissions from their firm
            if user_profile.firm:
                queryset = queryset.filter(firm=user_profile.firm)
            
            # Buyers can only see their own submissions
            if user_profile.is_buyer():
                queryset = queryset.filter(buyer=self.request.user)
            
            # Category heads can only see submissions in their categories
            elif user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
                scoped_categories = user_profile.category_head_profile.scoped_categories.all()
                if scoped_categories:
                    queryset = queryset.filter(category__in=scoped_categories)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get related submissions (same product, date, firm) for comparison
        submission = self.object
        related_submissions = PriceSubmission.objects.filter(
            date=submission.date,
            firm=submission.firm,
            product=submission.product
        ).exclude(
            id=submission.id
        ).select_related(
            'farmer', 'location', 'buyer'
        ).order_by('price_per_unit')
        
        # Add highlighting
        all_submissions = PriceSubmission.objects.filter(
            date=submission.date,
            firm=submission.firm,
            product=submission.product
        )
        highlighted_submissions = ReportingService.get_price_submissions_with_highlights(
            all_submissions
        )
        
        context['related_submissions'] = highlighted_submissions
        context['user_profile'] = self.request.user.profile
        
        return context


@login_required
def ajax_get_products(request):
    """AJAX view to get products for a selected category"""
    category_id = request.GET.get('category_id')
    
    if category_id:
        products = Product.objects.filter(category_id=category_id).values(
            'id', 'name'
        ).order_by('name')
        return JsonResponse({'products': list(products)})
    
    return JsonResponse({'products': []})


@login_required
def ajax_get_categories_and_products(request):
    """AJAX view to get categories and their products"""
    user_profile = request.user.profile
    
    # Get allowed categories based on user role
    categories = ProductCategory.objects.all()
    
    if not user_profile.is_admin():
        if user_profile.is_buyer() and hasattr(user_profile, 'buyer_profile'):
            categories = user_profile.buyer_profile.allowed_categories.all()
        elif user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
            categories = user_profile.category_head_profile.scoped_categories.all()
    
    data = []
    for category in categories:
        products = category.products.all().values('id', 'name').order_by('name')
        data.append({
            'id': category.id,
            'name': category.name,
            'products': list(products)
        })
    
    return JsonResponse({'categories': data})


@login_required
def submission_delete(request, pk):
    """Delete a submission (for buyers and admins only)"""
    submission = get_object_or_404(PriceSubmission, pk=pk)
    
    # Check permissions
    user_profile = request.user.profile
    
    if not (user_profile.is_admin() or 
            (submission.buyer == request.user and submission.status == 'PENDING')):
        messages.error(request, "You don't have permission to delete this submission.")
        return redirect('core:submission_list')
    
    if request.method == 'POST':
        submission.delete()
        messages.success(request, "Submission deleted successfully.")
        return redirect('core:submission_list')
    
    return render(request, 'core/submissions/delete_confirm.html', {
        'submission': submission
    })


@login_required
def excel_submission_view(request):
    """Excel-style submission form view with region-based farmer filtering"""
    # Check if user is buyer
    if not hasattr(request.user, 'profile') or not request.user.profile.is_buyer():
        messages.error(request, "Only buyers can access the price submission form.")
        return redirect('core:submission_list')
    
    user_profile = request.user.profile
    
    # Check if buyer has assigned location
    buyer_location = None
    region_farmers = []
    
    if hasattr(user_profile, 'buyer_profile') and user_profile.buyer_profile.assigned_location:
        buyer_location = user_profile.buyer_profile.assigned_location
        # Get farmers from buyer's assigned region
        region_farmers = Farmer.objects.filter(
            location=buyer_location
        ).order_by('name')
    else:
        # If no assigned location, show all farmers (fallback)
        region_farmers = Farmer.objects.select_related('location').order_by('location__name', 'name')
        if region_farmers.exists():
            buyer_location = region_farmers.first().location
    
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
    ).select_related('category').order_by('category__name', 'name')
    
    # Generate date range (today + next 13 days for 2 weeks)
    today = timezone.now().date()
    date_range = [today + timedelta(days=i) for i in range(14)]
    
    # Prepare data for JavaScript
    products_data = [
        {
            'id': product.id,
            'name': product.name,
            'category_id': product.category.id,
            'category_name': product.category.name
        }
        for product in products
    ]
    
    dates_data = [date.strftime('%Y-%m-%d') for date in date_range]
    
    context = {
        'buyer_location': buyer_location,
        'region_farmers': region_farmers,
        'products': products,
        'products_json': json.dumps(products_data),
        'dates_json': json.dumps(dates_data),
        'categories': allowed_categories,
        'today': today,
        'date_range': date_range,
    }
    
    return render(request, 'core/submissions/form_excel.html', context)


@login_required
def business_head_excel_submission_view(request):
    """Excel-style view for business heads to VIEW submitted prices (read-only)"""
    # Check if user is business head
    if not hasattr(request.user, 'profile') or not request.user.profile.is_business_head():
        messages.error(request, "Only business heads can access this form.")
        return redirect('core:submission_list')
    
    user_profile = request.user.profile
    
    # Get all farmers for display
    all_farmers = Farmer.objects.select_related('location').order_by('location__name', 'name')
    
    # Get all product categories
    all_categories = ProductCategory.objects.all()
    
    # Get all products
    products = Product.objects.filter(
        category__in=all_categories
    ).select_related('category').order_by('category__name', 'name')
    
    # Get today's date
    today = timezone.now().date()
    
    # Get all price submissions for today
    todays_submissions = PriceSubmission.objects.filter(
        date=today,
        status__in=['PENDING', 'APPROVED']  # Show both pending and approved prices
    ).select_related('farmer', 'product', 'buyer')
    
    # Create a dictionary for quick lookup: {farmer_id: {product_id: price_data}}
    price_data = {}
    min_prices = {}  # Track minimum prices per product: {product_id: min_price}
    
    for submission in todays_submissions:
        farmer_id = submission.farmer.id
        product_id = submission.product.id
        price = float(submission.price_per_unit)
        
        if farmer_id not in price_data:
            price_data[farmer_id] = {}
        
        # Store price data
        price_data[farmer_id][product_id] = {
            'price': price,
            'buyer': submission.buyer.username if submission.buyer else 'Unknown',
            'submission_id': submission.id,
            'created_at': submission.created_at.isoformat() if submission.created_at else None
        }
        
        # Track minimum price for this product
        if product_id not in min_prices or price < min_prices[product_id]:
            min_prices[product_id] = price
    
    # Prepare data for JavaScript
    products_data = [
        {
            'id': product.id,
            'name': product.name,
            'category_id': product.category.id,
            'category_name': product.category.name
        }
        for product in products
    ]
    
    farmers_data = [
        {
            'id': farmer.id,
            'name': farmer.name,
            'location_name': farmer.location.name if farmer.location else 'Unknown'
        }
        for farmer in all_farmers
    ]
    
    context = {
        'all_farmers': all_farmers,
        'farmers_json': json.dumps(farmers_data),
        'products': products,
        'products_json': json.dumps(products_data),
        'categories': all_categories,
        'today': today,
        'is_business_head': True,
        'price_data': json.dumps(price_data),
        'min_prices': json.dumps(min_prices),
        'total_submissions': todays_submissions.count(),
    }
    
    return render(request, 'core/submissions/business_head_excel.html', context)


@login_required
def get_farmer_data(request):
    """Get existing price data for a specific farmer (AJAX endpoint)"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Only GET method allowed'})
    
    farmer_id = request.GET.get('farmer_id')
    if not farmer_id:
        return JsonResponse({'success': False, 'error': 'farmer_id parameter required'})
    
    try:
        # Check if user is buyer
        if not hasattr(request.user, 'profile') or not request.user.profile.is_buyer():
            return JsonResponse({'success': False, 'error': 'Only buyers can access farmer data'})
        
        # Get farmer
        farmer = get_object_or_404(Farmer, id=farmer_id)
        
        # Get user's firm and allowed categories
        user_profile = request.user.profile
        firm = user_profile.firm
        
        allowed_categories = []
        if hasattr(user_profile, 'buyer_profile'):
            allowed_categories = user_profile.buyer_profile.allowed_categories.all()
        else:
            allowed_categories = ProductCategory.objects.all()
        
        # Get price submissions for this farmer for a broader range to ensure data persistence
        from datetime import timedelta
        today = timezone.now().date()
        start_date = today - timedelta(days=1)  # Include yesterday 
        end_date = today + timedelta(days=13)  # Next 13 days (15 total days range)
        
        price_submissions = PriceSubmission.objects.filter(
            farmer=farmer,
            firm=firm,
            date__gte=start_date,
            date__lte=end_date,
            product__category__in=allowed_categories
        ).select_related('product').values(
            'date', 'product_id', 'product__name', 'price_per_unit', 'created_at'
        ).order_by('-created_at')  # Get most recent entries first
        
        # Format data for frontend
        prices_data = []
        for submission in price_submissions:
            prices_data.append({
                'date': submission['date'].strftime('%Y-%m-%d'),
                'product_id': submission['product_id'],
                'product_name': submission['product__name'],
                'price': float(submission['price_per_unit'])  # Map price_per_unit to price for frontend
            })
        
        return JsonResponse({
            'success': True,
            'farmer_id': farmer_id,
            'farmer_name': farmer.name,
            'prices': prices_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Error loading farmer data: {str(e)}'
        })


@login_required
@csrf_exempt
def save_excel_prices(request):
    """Save prices from Excel-style form"""
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
@csrf_exempt
def get_excel_price(request):
    """Get existing price for a specific farmer-product-date combination"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    # Check if user is buyer
    if not hasattr(request.user, 'profile') or not request.user.profile.is_buyer():
        return JsonResponse({'success': False, 'error': 'Only buyers can access price data'})
    
    try:
        data = json.loads(request.body)
        farmer_id = data.get('farmer_id')
        product_id = data.get('product_id')
        date_str = data.get('date')
        
        if not all([farmer_id, product_id, date_str]):
            return JsonResponse({'success': False, 'error': 'farmer_id, product_id, and date are required'})
        
        # Parse date
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get user's firm
        user_profile = request.user.profile
        firm = user_profile.firm
        
        # Get existing submission
        submission = PriceSubmission.objects.filter(
            date=date,
            product_id=product_id,
            farmer_id=farmer_id,
            buyer=request.user,
            firm=firm
        ).first()
        
        if submission:
            return JsonResponse({
                'success': True,
                'price': float(submission.price_per_unit),
                'quantity': float(submission.quantity),
                'unit': submission.unit,
                'status': submission.status
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No price found for this combination'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})