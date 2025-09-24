"""
Dashboard views for role-aware landing pages.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from django.contrib import messages

from ..models import PriceSubmission, Firm, ProductCategory
from ..services.reporting_service import ReportingService
from ..services.approval_service import ApprovalService


@login_required
def dashboard_view(request):
    """
    Role-aware dashboard that redirects to appropriate dashboard based on user role.
    """
    if not hasattr(request.user, 'profile'):
        messages.error(request, "User profile not found. Please contact administrator.")
        return redirect('admin:index')
    
    user_profile = request.user.profile
    
    if user_profile.is_admin():
        return admin_dashboard_view(request)
    elif user_profile.is_business_head():
        return business_head_dashboard_view(request)
    elif user_profile.is_category_head():
        return category_head_dashboard_view(request)
    elif user_profile.is_buyer():
        return buyer_dashboard_view(request)
    else:
        messages.error(request, "No role assigned. Please contact administrator.")
        return redirect('login')


@login_required
def buyer_dashboard_view(request):
    """Dashboard for buyers"""
    user_profile = request.user.profile
    
    # Get recent submissions by this buyer
    recent_submissions = PriceSubmission.objects.filter(
        buyer=request.user
    ).select_related(
        'firm', 'product', 'category', 'location', 'farmer'
    ).order_by('-created_at')[:10]
    
    # Get submission statistics
    today = timezone.now().date()
    week_ago = today - timezone.timedelta(days=7)
    month_ago = today - timezone.timedelta(days=30)
    
    stats = {
        'today': PriceSubmission.objects.filter(buyer=request.user, date=today).count(),
        'this_week': PriceSubmission.objects.filter(buyer=request.user, date__gte=week_ago).count(),
        'this_month': PriceSubmission.objects.filter(buyer=request.user, date__gte=month_ago).count(),
        'total': PriceSubmission.objects.filter(buyer=request.user).count(),
    }
    
    # Status breakdown
    status_stats = PriceSubmission.objects.filter(buyer=request.user).aggregate(
        pending=Count('id', filter=Q(status='PENDING')),
        approved=Count('id', filter=Q(status='APPROVED')),
        cancelled=Count('id', filter=Q(status='CANCELLED'))
    )
    
    # Get allowed categories for this buyer
    allowed_categories = []
    if hasattr(user_profile, 'buyer_profile'):
        allowed_categories = user_profile.buyer_profile.allowed_categories.all()
    
    context = {
        'user_profile': user_profile,
        'recent_submissions': recent_submissions,
        'stats': stats,
        'status_stats': status_stats,
        'allowed_categories': allowed_categories,
        'dashboard_type': 'buyer'
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def category_head_dashboard_view(request):
    """Dashboard for category heads"""
    user_profile = request.user.profile
    
    # Get scoped categories
    scoped_categories = []
    if hasattr(user_profile, 'category_head_profile'):
        scoped_categories = user_profile.category_head_profile.scoped_categories.all()
    
    # Build queryset based on user's permissions
    submissions_qs = PriceSubmission.objects.all()
    
    if not user_profile.is_admin():
        # Filter by firm and categories
        if user_profile.firm:
            submissions_qs = submissions_qs.filter(firm=user_profile.firm)
        
        if scoped_categories:
            submissions_qs = submissions_qs.filter(category__in=scoped_categories)
    
    # Get recent submissions
    recent_submissions = submissions_qs.select_related(
        'firm', 'product', 'category', 'location', 'farmer', 'buyer'
    ).order_by('-created_at')[:10]
    
    # Get statistics
    today = timezone.now().date()
    stats = {
        'total_today': submissions_qs.filter(date=today).count(),
        'pending_today': submissions_qs.filter(date=today, status='PENDING').count(),
        'approved_today': submissions_qs.filter(date=today, status='APPROVED').count(),
        'total_pending': submissions_qs.filter(status='PENDING').count(),
    }
    
    # Category-wise breakdown
    category_stats = submissions_qs.filter(
        date=today
    ).values(
        'category__name'
    ).annotate(
        total=Count('id'),
        pending=Count('id', filter=Q(status='PENDING')),
        approved=Count('id', filter=Q(status='APPROVED'))
    ).order_by('category__name')
    
    context = {
        'user_profile': user_profile,
        'recent_submissions': recent_submissions,
        'stats': stats,
        'category_stats': category_stats,
        'scoped_categories': scoped_categories,
        'dashboard_type': 'category_head'
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def business_head_dashboard_view(request):
    """Dashboard for business heads"""
    user_profile = request.user.profile
    
    # Build queryset based on user's permissions
    submissions_qs = PriceSubmission.objects.all()
    
    if not user_profile.is_admin():
        # Filter by firm
        if user_profile.firm:
            submissions_qs = submissions_qs.filter(firm=user_profile.firm)
    
    # Get submissions that need approval
    pending_approvals = ApprovalService.get_approvable_submissions(request.user)[:10]
    
    # Get recent submissions
    recent_submissions = submissions_qs.select_related(
        'firm', 'product', 'category', 'location', 'farmer', 'buyer'
    ).order_by('-created_at')[:10]
    
    # Get approval statistics
    today = timezone.now().date()
    approval_stats = ApprovalService.get_approval_stats(
        firm=user_profile.firm if not user_profile.is_admin() else None,
        date_from=today,
        date_to=today
    )
    
    # Get daily summary
    daily_summary = ReportingService.get_daily_price_summary(
        date=today,
        firm=user_profile.firm if not user_profile.is_admin() else None
    )
    
    context = {
        'user_profile': user_profile,
        'pending_approvals': pending_approvals,
        'recent_submissions': recent_submissions,
        'approval_stats': approval_stats,
        'daily_summary': daily_summary,
        'dashboard_type': 'business_head'
    }
    
    return render(request, 'core/dashboard.html', context)


@login_required
def admin_dashboard_view(request):
    """Dashboard for admins"""
    user_profile = request.user.profile
    
    # Get overall statistics
    today = timezone.now().date()
    
    # Firm-wise daily report
    firm_reports = ReportingService.get_firm_wise_daily_report(date=today)
    
    # Overall stats
    total_stats = {
        'total_submissions': PriceSubmission.objects.filter(date=today).count(),
        'pending_approvals': PriceSubmission.objects.filter(date=today, status='PENDING').count(),
        'approved_today': PriceSubmission.objects.filter(date=today, status='APPROVED').count(),
        'total_firms': Firm.objects.count(),
        'total_categories': ProductCategory.objects.count(),
    }
    
    # Recent activity across all firms
    recent_submissions = PriceSubmission.objects.select_related(
        'firm', 'product', 'category', 'location', 'farmer', 'buyer'
    ).order_by('-created_at')[:15]
    
    # Top performing locations
    top_locations = ReportingService.get_top_performing_locations(
        date_from=today - timezone.timedelta(days=7),
        date_to=today,
        limit=5
    )
    
    context = {
        'user_profile': user_profile,
        'firm_reports': firm_reports,
        'total_stats': total_stats,
        'recent_submissions': recent_submissions,
        'top_locations': top_locations,
        'dashboard_type': 'admin'
    }
    
    return render(request, 'core/dashboard.html', context)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Class-based view for dashboard (alternative implementation)"""
    template_name = 'core/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Redirect to function-based view for simplicity
        return context
    
    def get(self, request, *args, **kwargs):
        # Redirect to the function-based dashboard view
        return dashboard_view(request)
    