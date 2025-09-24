"""
URL configuration for the core app.
"""

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import dashboard, submissions, approvals, reports, bulk_entry

app_name = 'core'

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='core/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', dashboard.dashboard_view, name='dashboard'),
    
    # Submissions
    path('submissions/', submissions.SubmissionListView.as_view(), name='submission_list'),
    path('submissions/create/', submissions.excel_submission_view, name='submission_create'),
    path('submissions/business-head/', submissions.business_head_excel_submission_view, name='business_head_submission'),
    path('submissions/save-excel-prices/', submissions.save_excel_prices, name='excel_save'),
    path('submissions/get-excel-price/', submissions.get_excel_price, name='excel_get_price'),
    path('api/farmer-data/', submissions.get_farmer_data, name='farmer_data'),
    path('submissions/create-old/', submissions.SubmissionCreateView.as_view(), name='submission_create_old'),
    path('submissions/bulk-entry/', bulk_entry.BulkPriceEntryView.as_view(), name='bulk_entry'),
    path('submissions/bulk-save/', bulk_entry.bulk_save_prices, name='bulk_save'),
    path('api/products-by-category/', bulk_entry.get_products_by_category, name='products_by_category'),
    path('api/farmers-by-location/', bulk_entry.get_farmers_by_location, name='farmers_by_location'),
    path('submissions/<int:pk>/', submissions.SubmissionDetailView.as_view(), name='submission_detail'),
    path('submissions/<int:pk>/edit/', submissions.SubmissionUpdateView.as_view(), name='submission_edit'),
    path('submissions/<int:pk>/delete/', submissions.submission_delete, name='submission_delete'),
    
    # Approvals
    path('submissions/<int:pk>/approve/', approvals.approve_submission, name='submission_approve'),
    path('submissions/<int:pk>/disapprove/', approvals.disapprove_submission, name='submission_disapprove'),
    path('submissions/<int:pk>/cancel-approval/', approvals.cancel_approval, name='submission_cancel_approval'),
    path('approvals/', approvals.pending_approvals, name='approval_list'),
    path('approvals/bulk-approve/', approvals.bulk_approve_submissions, name='bulk_approve'),
    
    # Reports
    path('reports/', reports.reports_index, name='reports'),
]