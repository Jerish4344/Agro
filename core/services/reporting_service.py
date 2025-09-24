"""
Reporting service for generating reports and analytics.
Handles KPIs, aggregations, and data export functionality.
"""

from django.db import models
from django.db.models import Count, Avg, Min, Max, Sum, Q, F, Case, When
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import logging

from ..models import PriceSubmission, Firm, ProductCategory, Product, Location

logger = logging.getLogger(__name__)


class ReportingService:
    """Service class for generating reports and analytics"""
    
    @staticmethod
    def get_price_submissions_with_highlights(queryset=None, group_by_location=False):
        """
        Get price submissions annotated with min/max price highlights.
        
        Args:
            queryset: Optional base queryset to work with
            group_by_location: Whether to group by location as well
            
        Returns:
            QuerySet with annotations for highlighting min/max prices
        """
        if queryset is None:
            queryset = PriceSubmission.objects.all()
        
        # Define grouping fields
        group_fields = ['date', 'firm', 'category', 'product']
        if group_by_location:
            group_fields.append('location')
        
        # Create subquery to get min and max prices for each group
        price_aggregates = queryset.values(*group_fields).annotate(
            min_price=Min('price_per_unit'),
            max_price=Max('price_per_unit')
        )
        
        # Create a dictionary for quick lookup
        price_lookup = {}
        for item in price_aggregates:
            key = tuple(item[field] for field in group_fields)
            price_lookup[key] = {
                'min_price': item['min_price'],
                'max_price': item['max_price']
            }
        
        # Annotate the original queryset
        annotated_queryset = queryset.annotate(
            # Calculate if this row has the minimum price in its group
            is_min_price=Case(
                When(
                    price_per_unit__in=[
                        price_lookup.get(
                            (
                                models.OuterRef('date'),
                                models.OuterRef('firm'),
                                models.OuterRef('category'),
                                models.OuterRef('product'),
                                models.OuterRef('location') if group_by_location else None
                            ), {}
                        ).get('min_price')
                    ]
                ),
                then=models.Value(True),
                default=models.Value(False),
                output_field=models.BooleanField()
            ),
            # Calculate if this row has the maximum price in its group
            is_max_price=Case(
                When(
                    price_per_unit__in=[
                        price_lookup.get(
                            (
                                models.OuterRef('date'),
                                models.OuterRef('firm'),
                                models.OuterRef('category'),
                                models.OuterRef('product'),
                                models.OuterRef('location') if group_by_location else None
                            ), {}
                        ).get('max_price')
                    ]
                ),
                then=models.Value(True),
                default=models.Value(False),
                output_field=models.BooleanField()
            )
        )
        
        return annotated_queryset
    
    @staticmethod
    def get_daily_price_summary(date=None, firm=None, category=None):
        """
        Get daily price summary with min, max, average prices per product.
        
        Args:
            date: Specific date to filter by (defaults to today)
            firm: Optional firm filter
            category: Optional category filter
            
        Returns:
            QuerySet with price aggregations
        """
        if date is None:
            date = timezone.now().date()
        
        queryset = PriceSubmission.objects.filter(
            date=date,
            status='APPROVED'
        )
        
        if firm:
            queryset = queryset.filter(firm=firm)
        
        if category:
            queryset = queryset.filter(category=category)
        
        summary = queryset.values(
            'product__name',
            'product__category__name',
            'location__name'
        ).annotate(
            submission_count=Count('id'),
            min_price=Min('price_per_unit'),
            max_price=Max('price_per_unit'),
            avg_price=Avg('price_per_unit'),
            total_quantity=Sum('quantity'),
            total_value=Sum(F('price_per_unit') * F('quantity'))
        ).order_by('product__category__name', 'product__name', 'location__name')
        
        return summary
    
    @staticmethod
    def get_firm_wise_daily_report(date=None):
        """
        Get firm-wise daily report with KPIs.
        
        Args:
            date: Date to generate report for (defaults to today)
            
        Returns:
            List of dictionaries with firm statistics
        """
        if date is None:
            date = timezone.now().date()
        
        firms = Firm.objects.all()
        report_data = []
        
        for firm in firms:
            submissions = PriceSubmission.objects.filter(firm=firm, date=date)
            
            total_submissions = submissions.count()
            approved_submissions = submissions.filter(status='APPROVED').count()
            pending_submissions = submissions.filter(status='PENDING').count()
            
            if total_submissions > 0:
                approval_rate = (approved_submissions / total_submissions) * 100
            else:
                approval_rate = 0
            
            # Get price statistics for approved submissions
            approved_qs = submissions.filter(status='APPROVED')
            price_stats = approved_qs.aggregate(
                min_price=Min('price_per_unit'),
                max_price=Max('price_per_unit'),
                avg_price=Avg('price_per_unit'),
                total_value=Sum(F('price_per_unit') * F('quantity'))
            )
            
            # Get top locations by submission count
            top_locations = approved_qs.values(
                'location__name'
            ).annotate(
                submission_count=Count('id')
            ).order_by('-submission_count')[:5]
            
            report_data.append({
                'firm': firm,
                'date': date,
                'total_submissions': total_submissions,
                'approved_submissions': approved_submissions,
                'pending_submissions': pending_submissions,
                'approval_rate': round(approval_rate, 2),
                'min_price': price_stats['min_price'] or 0,
                'max_price': price_stats['max_price'] or 0,
                'avg_price': price_stats['avg_price'] or 0,
                'total_value': price_stats['total_value'] or 0,
                'top_locations': list(top_locations)
            })
        
        return report_data
    
    @staticmethod
    def get_category_wise_report(date_from=None, date_to=None, firm=None):
        """
        Get category-wise report with trends.
        
        Args:
            date_from: Start date for the report
            date_to: End date for the report
            firm: Optional firm filter
            
        Returns:
            Dictionary with category statistics
        """
        if date_from is None:
            date_from = timezone.now().date() - timezone.timedelta(days=30)
        
        if date_to is None:
            date_to = timezone.now().date()
        
        queryset = PriceSubmission.objects.filter(
            date__range=[date_from, date_to],
            status='APPROVED'
        )
        
        if firm:
            queryset = queryset.filter(firm=firm)
        
        category_stats = queryset.values(
            'category__name',
            'category__code'
        ).annotate(
            total_submissions=Count('id'),
            unique_products=Count('product', distinct=True),
            unique_farmers=Count('farmer', distinct=True),
            unique_locations=Count('location', distinct=True),
            min_price=Min('price_per_unit'),
            max_price=Max('price_per_unit'),
            avg_price=Avg('price_per_unit'),
            total_quantity=Sum('quantity'),
            total_value=Sum(F('price_per_unit') * F('quantity'))
        ).order_by('category__name')
        
        return {
            'date_range': (date_from, date_to),
            'firm': firm,
            'categories': list(category_stats)
        }
    
    @staticmethod
    def get_product_price_trends(product_id, days=30, firm=None):
        """
        Get price trends for a specific product over time.
        
        Args:
            product_id: ID of the product
            days: Number of days to look back
            firm: Optional firm filter
            
        Returns:
            QuerySet with daily price trends
        """
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=days)
        
        queryset = PriceSubmission.objects.filter(
            product_id=product_id,
            date__range=[start_date, end_date],
            status='APPROVED'
        )
        
        if firm:
            queryset = queryset.filter(firm=firm)
        
        trends = queryset.values('date').annotate(
            submission_count=Count('id'),
            min_price=Min('price_per_unit'),
            max_price=Max('price_per_unit'),
            avg_price=Avg('price_per_unit'),
            total_quantity=Sum('quantity')
        ).order_by('date')
        
        return trends
    
    @staticmethod
    def get_top_performing_locations(date_from=None, date_to=None, firm=None, limit=10):
        """
        Get top performing locations by submission volume and value.
        
        Args:
            date_from: Start date
            date_to: End date
            firm: Optional firm filter
            limit: Number of top locations to return
            
        Returns:
            List of top locations with statistics
        """
        if date_from is None:
            date_from = timezone.now().date() - timezone.timedelta(days=30)
        
        if date_to is None:
            date_to = timezone.now().date()
        
        queryset = PriceSubmission.objects.filter(
            date__range=[date_from, date_to],
            status='APPROVED'
        )
        
        if firm:
            queryset = queryset.filter(firm=firm)
        
        top_locations = queryset.values(
            'location__name',
            'location__region_code'
        ).annotate(
            total_submissions=Count('id'),
            unique_farmers=Count('farmer', distinct=True),
            unique_products=Count('product', distinct=True),
            total_value=Sum(F('price_per_unit') * F('quantity')),
            avg_price=Avg('price_per_unit')
        ).order_by('-total_value', '-total_submissions')[:limit]
        
        return list(top_locations)
    
    @staticmethod
    def get_user_activity_stats(user, date_from=None, date_to=None):
        """
        Get activity statistics for a specific user.
        
        Args:
            user: User object
            date_from: Start date
            date_to: End date
            
        Returns:
            Dictionary with user activity statistics
        """
        if date_from is None:
            date_from = timezone.now().date() - timezone.timedelta(days=30)
        
        if date_to is None:
            date_to = timezone.now().date()
        
        # Submissions by the user (if buyer)
        submissions_stats = PriceSubmission.objects.filter(
            buyer=user,
            date__range=[date_from, date_to]
        ).aggregate(
            total_submissions=Count('id'),
            approved_submissions=Count('id', filter=Q(status='APPROVED')),
            pending_submissions=Count('id', filter=Q(status='PENDING')),
            cancelled_submissions=Count('id', filter=Q(status='CANCELLED'))
        )
        
        # Approvals by the user (if business head/admin)
        approvals_stats = PriceSubmission.objects.filter(
            approved_by=user,
            approved_at__date__range=[date_from, date_to]
        ).aggregate(
            total_approvals=Count('id')
        )
        
        return {
            'user': user,
            'date_range': (date_from, date_to),
            'submissions': submissions_stats,
            'approvals': approvals_stats
        }