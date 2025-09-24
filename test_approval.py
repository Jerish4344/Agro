from core.models import PriceSubmission, UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile
from django.contrib.auth.models import User
from core.services.approval_service import ApprovalService

# Test with buyer1
user = User.objects.get(username="buyer1")
print(f"Testing approval system for user: {user.username}")

# Test the approval service method
approvable_submissions = ApprovalService.get_approvable_submissions(user)
print(f"Number of approvable submissions: {approvable_submissions.count()}")

for submission in approvable_submissions:
    print(f"  - Submission {submission.id}: {submission.status}")
    
# Check if user is admin or business head
profile = user.profile
print(f"User firm: {profile.firm}")
print(f"Is admin: {profile.is_admin()}")
print(f"Is business head: {profile.is_business_head()}")

# Test with admin user
try:
    admin_user = User.objects.filter(is_superuser=True).first()
    if admin_user:
        print(f"\nTesting with admin user: {admin_user.username}")
        admin_approvable = ApprovalService.get_approvable_submissions(admin_user)
        print(f"Admin can approve: {admin_approvable.count()} submissions")
    else:
        print("No admin user found")
except Exception as e:
    print(f"Error with admin user: {e}")

