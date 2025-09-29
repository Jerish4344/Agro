from core.models import PriceSubmission, UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile
from django.contrib.auth.models import User

# Check a specific user
user = User.objects.get(username="buyer1")
print(f"User: {user.username}")
print(f"Is superuser: {user.is_superuser}")

# Check if user has profile
if hasattr(user, "profile"):
    profile = user.profile
    print(f"Profile: {profile}")
    print(f"Is admin: {profile.is_admin()}")
    print(f"Is business head: {profile.is_business_head()}")
    print(f"Firm: {profile.firm}")
else:
    print("No profile found")

