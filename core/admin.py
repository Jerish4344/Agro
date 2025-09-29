"""
Admin configuration for core models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    Firm, Location, Farmer, ProductCategory, MainCategory, SubCategory, Product, 
    UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile,
    PriceSubmission
)


@admin.register(Firm)
class FirmAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'region_code', 'farmer_count', 'created_at']
    list_filter = ['region_code', 'created_at']
    search_fields = ['name', 'region_code']
    ordering = ['name']
    
    def farmer_count(self, obj):
        return obj.farmers.count()
    farmer_count.short_description = 'Farmers'


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'location', 'submission_count', 'created_at']
    list_filter = ['location__region_code', 'location', 'created_at']
    search_fields = ['name', 'phone', 'location__name']
    ordering = ['name']
    
    def submission_count(self, obj):
        return obj.price_submissions.count()
    submission_count.short_description = 'Submissions'


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'product_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    ordering = ['name']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'subcategory_count', 'product_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    ordering = ['name']
    
    def subcategory_count(self, obj):
        return obj.subcategories.count()
    subcategory_count.short_description = 'Sub Categories'
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'main_category', 'product_count', 'created_at']
    list_filter = ['category', 'main_category', 'created_at']
    search_fields = ['name', 'code', 'category__name', 'main_category__name']
    ordering = ['category__name', 'main_category__name', 'name']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'main_category', 'sub_category', 'submission_count', 'avg_price', 'created_at']
    list_filter = ['category', 'main_category', 'sub_category', 'created_at']
    search_fields = ['name', 'category__name', 'main_category__name', 'sub_category__name']
    ordering = ['category__name', 'sub_category__name', 'name']
    
    def submission_count(self, obj):
        return obj.price_submissions.count()
    submission_count.short_description = 'Submissions'
    
    def avg_price(self, obj):
        from django.db.models import Avg
        avg = obj.price_submissions.filter(status='APPROVED').aggregate(
            avg_price=Avg('price_per_unit')
        )['avg_price']
        if avg:
            return f"₹{avg:.2f}"
        return "-"
    avg_price.short_description = 'Avg Price'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'firm', 'phone', 'role_display', 'created_at']
    list_filter = ['firm', 'user__groups', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'phone']
    ordering = ['user__username']
    
    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = 'Role'


@admin.register(BuyerProfile)
class BuyerProfileAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'firm', 'categories_display', 'submission_count']
    list_filter = ['user_profile__firm', 'allowed_categories']
    search_fields = ['user_profile__user__username']
    filter_horizontal = ['allowed_categories']
    
    def firm(self, obj):
        return obj.user_profile.firm
    firm.short_description = 'Firm'
    
    def categories_display(self, obj):
        categories = obj.allowed_categories.all()[:3]
        display = ', '.join([cat.name for cat in categories])
        if obj.allowed_categories.count() > 3:
            display += f" (+{obj.allowed_categories.count() - 3} more)"
        return display
    categories_display.short_description = 'Categories'
    
    def submission_count(self, obj):
        return obj.user_profile.user.price_submissions.count()
    submission_count.short_description = 'Submissions'


@admin.register(CategoryHeadProfile)
class CategoryHeadProfileAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'firm', 'categories_display']
    list_filter = ['user_profile__firm', 'scoped_categories']
    search_fields = ['user_profile__user__username']
    filter_horizontal = ['scoped_categories']
    
    def firm(self, obj):
        return obj.user_profile.firm
    firm.short_description = 'Firm'
    
    def categories_display(self, obj):
        categories = obj.scoped_categories.all()
        return ', '.join([cat.name for cat in categories])
    categories_display.short_description = 'Categories'


@admin.register(BusinessHeadProfile)
class BusinessHeadProfileAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'firm', 'approval_count']
    list_filter = ['user_profile__firm']
    search_fields = ['user_profile__user__username']
    
    def firm(self, obj):
        return obj.user_profile.firm
    firm.short_description = 'Firm'
    
    def approval_count(self, obj):
        return obj.user_profile.user.approved_submissions.count()
    approval_count.short_description = 'Approvals'


@admin.register(PriceSubmission)
class PriceSubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'product', 'farmer', 'price_per_unit', 'quantity', 
        'total_value_display', 'buyer', 'status', 'approved_by'
    ]
    list_filter = [
        'status', 'date', 'firm', 'category', 'location', 
        'created_at', 'approved_at'
    ]
    search_fields = [
        'product__name', 'farmer__name', 'buyer__username', 
        'buyer__first_name', 'buyer__last_name', 'notes'
    ]
    ordering = ['-date', '-created_at']
    readonly_fields = ['created_at', 'updated_at', 'approval_version']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('date', 'firm', 'location', 'farmer')
        }),
        ('Product Details', {
            'fields': ('category', 'product', 'price_per_unit', 'quantity', 'unit')
        }),
        ('Submission Details', {
            'fields': ('buyer', 'notes')
        }),
        ('Approval Information', {
            'fields': ('status', 'approved_by', 'approved_at', 'approval_version')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_value_display(self, obj):
        return f"₹{obj.total_value:.2f}"
    total_value_display.short_description = 'Total Value'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'firm', 'product', 'category', 'location', 'farmer', 'buyer', 'approved_by'
        )
    
    actions = ['approve_submissions', 'export_csv']
    
    def approve_submissions(self, request, queryset):
        """Bulk approve selected submissions"""
        from .services.approval_service import ApprovalService, ApprovalError
        
        success_count = 0
        error_count = 0
        
        for submission in queryset.filter(status='PENDING'):
            try:
                ApprovalService.approve_submission(
                    submission_id=submission.id,
                    approved_by=request.user
                )
                success_count += 1
            except ApprovalError:
                error_count += 1
        
        if success_count:
            self.message_user(request, f"Successfully approved {success_count} submissions.")
        if error_count:
            self.message_user(request, f"Failed to approve {error_count} submissions.", level='warning')
    
    approve_submissions.short_description = "Approve selected submissions"
    
    def export_csv(self, request, queryset):
        """Export selected submissions as CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="price_submissions.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Date', 'Firm', 'Category', 'Product', 'Location', 'Farmer',
            'Price per Unit', 'Quantity', 'Unit', 'Total Value',
            'Buyer', 'Status', 'Notes', 'Approved By', 'Approved At'
        ])
        
        for submission in queryset:
            writer.writerow([
                submission.date,
                submission.firm.name,
                submission.category.name,
                submission.product.name,
                submission.location.name,
                submission.farmer.name,
                submission.price_per_unit,
                submission.quantity,
                submission.unit,
                submission.total_value,
                submission.buyer.get_full_name() or submission.buyer.username,
                submission.get_status_display(),
                submission.notes,
                submission.approved_by.get_full_name() if submission.approved_by else '',
                submission.approved_at.strftime('%Y-%m-%d %H:%M') if submission.approved_at else ''
            ])
        
        return response
    
    export_csv.short_description = "Export selected submissions as CSV"


# Customize admin site
admin.site.site_header = "Kannammal Agro Administration"
admin.site.site_title = "Kannammal Agro Admin"
admin.site.index_title = "Welcome to Kannammal Agro Administration"