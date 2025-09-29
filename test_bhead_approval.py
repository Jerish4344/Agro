from core.models import PriceSubmission
from django.contrib.auth.models import User
from core.services.approval_service import ApprovalService

# Test with business head
user = User.objects.get(username="bhead")
print(f"Testing approval system for business head: {user.username}")

profile = user.profile
print(f"User firm: {profile.firm}")
print(f"Is admin: {profile.is_admin()}")
print(f"Is business head: {profile.is_business_head()}")

# Test the approval service method
approvable_submissions = ApprovalService.get_approvable_submissions(user)
print(f"Number of approvable submissions: {approvable_submissions.count()}")

for submission in approvable_submissions:
    print(f"  - Submission {submission.id}: {submission.status} - Firm: {submission.firm}")

