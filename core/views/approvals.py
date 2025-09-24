"""
Views for approval actions (approve/cancel submissions).
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
from django.urls import reverse

from ..models import PriceSubmission
from ..services.approval_service import ApprovalService, ApprovalError


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def approve_submission(request, pk):
    """Approve a price submission"""
    submission = get_object_or_404(PriceSubmission, pk=pk)
    
    # Check if user can approve this submission
    if not submission.can_approve(request.user):
        messages.error(request, "You don't have permission to approve this submission.")
        return redirect('core:submission_list')
    
    if request.method == 'POST':
        expected_version = request.POST.get('expected_version')
        if expected_version:
            try:
                expected_version = int(expected_version)
            except ValueError:
                expected_version = None
        
        try:
            updated_submission = ApprovalService.approve_submission(
                submission_id=submission.id,
                approved_by=request.user,
                expected_version=expected_version
            )
            
            messages.success(
                request, 
                f"Submission for {updated_submission.product.name} approved successfully."
            )
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Submission approved successfully.',
                    'new_status': updated_submission.status,
                    'approved_by': updated_submission.approved_by.get_full_name() or updated_submission.approved_by.username,
                    'approved_at': updated_submission.approved_at.strftime('%Y-%m-%d %H:%M') if updated_submission.approved_at else '',
                    'approval_version': updated_submission.approval_version
                })
            
            # Redirect based on where the request came from
            next_url = request.POST.get('next', 'core:submission_list')
            return redirect(next_url)
            
        except ApprovalError as e:
            messages.error(request, str(e))
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            
            return redirect('core:submission_list')
    
    # GET request - show confirmation page
    context = {
        'submission': submission,
        'action': 'approve',
        'user_profile': request.user.profile
    }
    
    return render(request, 'core/approvals/confirm_approve.html', context)


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def disapprove_submission(request, pk):
    """Disapprove/undo approval of a price submission"""
    submission = get_object_or_404(PriceSubmission, pk=pk)
    
    # Check if user has permission to disapprove
    user_profile = request.user.profile
    if not (user_profile.is_admin() or user_profile.is_business_head()):
        messages.error(request, "You don't have permission to disapprove submissions.")
        return redirect('core:submission_list')
    
    # Check if submission is currently approved
    if submission.status != 'APPROVED':
        messages.error(request, "This submission is not currently approved.")
        return redirect('core:submission_list')
    
    if request.method == 'POST':
        try:
            # Change status back to PENDING
            submission.status = 'PENDING'
            submission.approved_by = None
            submission.approved_at = None
            submission.save()
            
            messages.success(
                request,
                f"Approval for {submission.product.name} has been reverted to pending."
            )
            
            return redirect('core:approval_list')
            
        except Exception as e:
            messages.error(request, f"Error disapproving submission: {str(e)}")
            return redirect('core:submission_list')
    
    # GET request - show confirmation page
    context = {
        'submission': submission,
        'action': 'disapprove',
        'user_profile': request.user.profile
    }
    
    return render(request, 'core/approvals/confirm_disapprove.html', context)


@login_required
@csrf_protect
@require_http_methods(["GET", "POST"])
def cancel_approval(request, pk):
    """Cancel approval of a price submission"""
    submission = get_object_or_404(PriceSubmission, pk=pk)
    
    # Check if user can cancel this approval
    if not submission.can_approve(request.user):
        messages.error(request, "You don't have permission to cancel this approval.")
        return redirect('core:submission_list')
    
    if submission.status != 'APPROVED':
        messages.error(request, "Can only cancel approved submissions.")
        return redirect('core:submission_list')
    
    if request.method == 'POST':
        expected_version = request.POST.get('expected_version')
        if expected_version:
            try:
                expected_version = int(expected_version)
            except ValueError:
                expected_version = None
        
        try:
            updated_submission = ApprovalService.cancel_approval(
                submission_id=submission.id,
                cancelled_by=request.user,
                expected_version=expected_version
            )
            
            messages.success(
                request, 
                f"Approval for {updated_submission.product.name} cancelled successfully."
            )
            
            # Handle AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Approval cancelled successfully.',
                    'new_status': updated_submission.status,
                    'approval_version': updated_submission.approval_version
                })
            
            # Redirect based on where the request came from
            next_url = request.POST.get('next', 'core:submission_list')
            return redirect(next_url)
            
        except ApprovalError as e:
            messages.error(request, str(e))
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            
            return redirect('core:submission_list')
    
    # GET request - show confirmation page
    context = {
        'submission': submission,
        'action': 'cancel',
        'user_profile': request.user.profile
    }
    
    return render(request, 'core/approvals/confirm_cancel.html', context)


@login_required
def bulk_approve_submissions(request):
    """Bulk approve multiple submissions"""
    if request.method != 'POST':
        messages.error(request, "Invalid request method.")
        return redirect('core:submission_list')
    
    submission_ids = request.POST.getlist('submission_ids')
    if not submission_ids:
        messages.error(request, "No submissions selected.")
        return redirect('core:submission_list')
    
    # Check if user can approve submissions
    user_profile = request.user.profile
    if not (user_profile.is_business_head() or user_profile.is_admin()):
        messages.error(request, "You don't have permission to approve submissions.")
        return redirect('core:submission_list')
    
    success_count = 0
    error_count = 0
    errors = []
    
    for submission_id in submission_ids:
        try:
            submission_id = int(submission_id)
            ApprovalService.approve_submission(
                submission_id=submission_id,
                approved_by=request.user
            )
            success_count += 1
        except (ValueError, ApprovalError) as e:
            error_count += 1
            errors.append(f"Submission {submission_id}: {str(e)}")
    
    if success_count > 0:
        messages.success(request, f"Successfully approved {success_count} submission(s).")
    
    if error_count > 0:
        messages.error(request, f"Failed to approve {error_count} submission(s).")
        for error in errors[:5]:  # Show only first 5 errors
            messages.error(request, error)
    
    return redirect('core:submission_list')


@login_required
def approval_history(request, pk):
    """View approval history for a submission"""
    submission = get_object_or_404(PriceSubmission, pk=pk)
    
    # Check permissions
    user_profile = request.user.profile
    
    # Users can only view history for submissions they have access to
    if not user_profile.is_admin():
        if user_profile.firm and submission.firm != user_profile.firm:
            messages.error(request, "You don't have permission to view this submission.")
            return redirect('core:submission_list')
        
        if user_profile.is_buyer() and submission.buyer != request.user:
            messages.error(request, "You can only view your own submissions.")
            return redirect('core:submission_list')
        
        if user_profile.is_category_head() and hasattr(user_profile, 'category_head_profile'):
            scoped_categories = user_profile.category_head_profile.scoped_categories.all()
            if scoped_categories and submission.category not in scoped_categories:
                messages.error(request, "You don't have permission to view this submission.")
                return redirect('core:submission_list')
    
    # For now, we'll show basic approval info
    # In a more complex system, you might have an ApprovalHistory model
    context = {
        'submission': submission,
        'user_profile': user_profile
    }
    
    return render(request, 'core/approvals/history.html', context)


@login_required
def pending_approvals(request):
    """View all pending approvals for the user"""
    user_profile = request.user.profile
    
    if not (user_profile.is_business_head() or user_profile.is_admin()):
        messages.error(request, "You don't have permission to view pending approvals.")
        return redirect('core:dashboard')
    
    # Get submissions that this user can approve (include both pending and approved)
    if user_profile.is_admin():
        all_submissions = PriceSubmission.objects.filter(status__in=['PENDING', 'APPROVED'])
    elif user_profile.is_business_head() and user_profile.firm:
        all_submissions = PriceSubmission.objects.filter(
            status__in=['PENDING', 'APPROVED'],
            firm=user_profile.firm
        )
    else:
        all_submissions = PriceSubmission.objects.none()
    
    # Apply filters
    category_id = request.GET.get('category')
    product_id = request.GET.get('product')
    status_filter = request.GET.get('status')
    
    if category_id:
        all_submissions = all_submissions.filter(product__category_id=category_id)
    
    if product_id:
        all_submissions = all_submissions.filter(product_id=product_id)
    
    if status_filter:
        all_submissions = all_submissions.filter(status=status_filter)
    
    # Get filter options for dropdowns
    from ..models import ProductCategory, Product
    categories = ProductCategory.objects.all().order_by('name')
    products = Product.objects.all().order_by('category__name', 'name')
    
    # Calculate stats
    from django.utils import timezone
    today = timezone.now().date()
    
    total_pending = all_submissions.filter(status='PENDING').count()
    today_pending = all_submissions.filter(status='PENDING', created_at__date=today).count()
    today_approved = all_submissions.filter(
        status='APPROVED',
        updated_at__date=today
    ).count()
    
    # Add pagination
    from django.core.paginator import Paginator
    paginator = Paginator(all_submissions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'submissions': page_obj,  # Template expects 'submissions' not 'pending_submissions'
        'pending_submissions': page_obj,
        'user_profile': user_profile,
        'categories': categories,
        'products': products,
        'total_pending': total_pending,
        'today_pending': today_pending,
        'today_approved': today_approved,
        'total_count': all_submissions.count()
    }
    
    return render(request, 'core/approvals/pending_list.html', context)