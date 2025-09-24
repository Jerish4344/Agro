from django.contrib.auth.models import User
from core.services.approval_service import ApprovalService

# Check current user Lisa Davis
try:
    user = User.objects.get(first_name="Lisa", last_name="Davis")
    print(f"Found user: {user.username}")
except User.DoesNotExist:
    # Try by display name or other fields
    users = User.objects.filter(first_name__icontains="Lisa")
    if users.exists():
        user = users.first()
        print(f"Found user by first name: {user.username}")
    else:
        print("Lisa Davis user not found")
        print("Available users:")
        for u in User.objects.all():
            print(f"  - {u.username}: {u.first_name} {u.last_name}")
        exit()

print(f"User details:")
print(f"  - Username: {user.username}")
print(f"  - First name: {user.first_name}")
print(f"  - Last name: {user.last_name}")
print(f"  - Is superuser: {user.is_superuser}")

if hasattr(user, "profile"):
    profile = user.profile
    print(f"  - Profile: {profile}")
    print(f"  - Is admin: {profile.is_admin()}")
    print(f"  - Is business head: {profile.is_business_head()}")
    print(f"  - Is category head: {profile.is_category_head()}")
    print(f"  - Is buyer: {profile.is_buyer()}")
    print(f"  - Firm: {profile.firm}")
else:
    print("  - No profile found")

# Test approval access
groups = user.groups.all()
print(f"  - Groups: {[g.name for g in groups]}")

# Test the approval service
approvable = ApprovalService.get_approvable_submissions(user)
print(f"  - Approvable submissions: {approvable.count()}")

