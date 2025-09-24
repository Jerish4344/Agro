"""
Approval service for handling price submission approvals/cancellations.
Implements optimistic locking and business logic for approval workflow.
"""

from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from ..models import PriceSubmission
import logging

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Custom exception for approval-related errors"""
    pass


class ApprovalService:
    """Service class for handling price submission approvals"""
    
    @staticmethod
    @transaction.atomic
    def approve_submission(submission_id: int, approved_by: User, expected_version: int = None) -> PriceSubmission:
        """
        Approve a price submission with optimistic locking.
        
        Args:
            submission_id: ID of the submission to approve
            approved_by: User who is approving the submission
            expected_version: Expected approval version for optimistic locking
            
        Returns:
            Updated PriceSubmission instance
            
        Raises:
            ApprovalError: If approval fails due to business rules or conflicts
        """
        try:
            # Lock the submission for update
            submission = PriceSubmission.objects.select_for_update().get(id=submission_id)
            
            # Check if user can approve this submission
            if not submission.can_approve(approved_by):
                raise ApprovalError("You don't have permission to approve this submission")
            
            # Check optimistic locking if version provided
            if expected_version is not None and submission.approval_version != expected_version:
                raise ApprovalError(
                    f"Submission has been modified by another user. "
                    f"Expected version {expected_version}, current version {submission.approval_version}"
                )
            
            # Check current status
            if submission.status == 'APPROVED':
                raise ApprovalError("Submission is already approved")
            
            if submission.status == 'CANCELLED':
                # Allow re-approval of cancelled submissions
                logger.info(f"Re-approving previously cancelled submission {submission_id}")
            
            # Check firm access for non-admin users
            if not approved_by.is_superuser:
                if hasattr(approved_by, 'profile') and approved_by.profile.firm:
                    if submission.firm != approved_by.profile.firm:
                        raise ApprovalError("You can only approve submissions from your firm")
                else:
                    raise ApprovalError("User profile not properly configured")
            
            # Update submission
            submission.status = 'APPROVED'
            submission.approved_by = approved_by
            submission.approved_at = timezone.now()
            submission.approval_version += 1
            
            submission.save()
            
            logger.info(
                f"Submission {submission_id} approved by {approved_by.username} "
                f"(version {submission.approval_version})"
            )
            
            return submission
            
        except PriceSubmission.DoesNotExist:
            raise ApprovalError(f"Submission with ID {submission_id} not found")
        except Exception as e:
            logger.error(f"Error approving submission {submission_id}: {str(e)}")
            raise ApprovalError(f"Failed to approve submission: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def cancel_approval(submission_id: int, cancelled_by: User, expected_version: int = None) -> PriceSubmission:
        """
        Cancel approval of a price submission.
        
        Args:
            submission_id: ID of the submission to cancel
            cancelled_by: User who is cancelling the approval
            expected_version: Expected approval version for optimistic locking
            
        Returns:
            Updated PriceSubmission instance
            
        Raises:
            ApprovalError: If cancellation fails due to business rules or conflicts
        """
        try:
            # Lock the submission for update
            submission = PriceSubmission.objects.select_for_update().get(id=submission_id)
            
            # Check if user can cancel this approval
            if not submission.can_approve(cancelled_by):
                raise ApprovalError("You don't have permission to cancel this approval")
            
            # Check optimistic locking if version provided
            if expected_version is not None and submission.approval_version != expected_version:
                raise ApprovalError(
                    f"Submission has been modified by another user. "
                    f"Expected version {expected_version}, current version {submission.approval_version}"
                )
            
            # Check current status
            if submission.status != 'APPROVED':
                raise ApprovalError("Can only cancel approved submissions")
            
            # Check firm access for non-admin users
            if not cancelled_by.is_superuser:
                if hasattr(cancelled_by, 'profile') and cancelled_by.profile.firm:
                    if submission.firm != cancelled_by.profile.firm:
                        raise ApprovalError("You can only cancel approvals from your firm")
                else:
                    raise ApprovalError("User profile not properly configured")
            
            # Update submission
            submission.status = 'CANCELLED'
            submission.approved_by = None
            submission.approved_at = None
            submission.approval_version += 1
            
            submission.save()
            
            logger.info(
                f"Submission {submission_id} approval cancelled by {cancelled_by.username} "
                f"(version {submission.approval_version})"
            )
            
            return submission
            
        except PriceSubmission.DoesNotExist:
            raise ApprovalError(f"Submission with ID {submission_id} not found")
        except Exception as e:
            logger.error(f"Error cancelling approval for submission {submission_id}: {str(e)}")
            raise ApprovalError(f"Failed to cancel approval: {str(e)}")
    
    @staticmethod
    def get_approvable_submissions(user: User) -> 'QuerySet':
        """
        Get submissions that the user can approve.
        
        Args:
            user: User to check permissions for
            
        Returns:
            QuerySet of PriceSubmission objects
        """
        if not hasattr(user, 'profile'):
            return PriceSubmission.objects.none()
        
        # Admin can approve all submissions
        if user.is_superuser or user.profile.is_admin():
            return PriceSubmission.objects.filter(status='PENDING')
        
        # Business heads can approve submissions from their firm
        if user.profile.is_business_head():
            if user.profile.firm:
                return PriceSubmission.objects.filter(
                    status='PENDING',
                    firm=user.profile.firm
                )
        
        # Other roles cannot approve
        return PriceSubmission.objects.none()
    
    @staticmethod
    def get_approval_stats(firm=None, date_from=None, date_to=None) -> dict:
        """
        Get approval statistics for reporting.
        
        Args:
            firm: Optional firm to filter by
            date_from: Optional start date
            date_to: Optional end date
            
        Returns:
            Dictionary with approval statistics
        """
        queryset = PriceSubmission.objects.all()
        
        if firm:
            queryset = queryset.filter(firm=firm)
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        total_submissions = queryset.count()
        approved_submissions = queryset.filter(status='APPROVED').count()
        pending_submissions = queryset.filter(status='PENDING').count()
        cancelled_submissions = queryset.filter(status='CANCELLED').count()
        
        approval_rate = 0
        if total_submissions > 0:
            approval_rate = (approved_submissions / total_submissions) * 100
        
        return {
            'total_submissions': total_submissions,
            'approved_submissions': approved_submissions,
            'pending_submissions': pending_submissions,
            'cancelled_submissions': cancelled_submissions,
            'approval_rate': round(approval_rate, 2)
        }