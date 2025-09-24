from core.models import PriceSubmission, UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile
from django.contrib.auth.models import User, Group

# Check all users and their groups
users = User.objects.all()
print("All users and their roles:")
for user in users:
    groups = user.groups.all()
    group_names = [g.name for g in groups]
    print(f"  {user.username}: {group_names}")

# Check available groups
print("\nAvailable groups:")
groups = Group.objects.all()
for group in groups:
    print(f"  - {group.name}")

# Check business heads specifically  
business_heads = User.objects.filter(groups__name="BUSINESS_HEAD")
print(f"\nBusiness heads count: {business_heads.count()}")
for bh in business_heads:
    profile = bh.profile if hasattr(bh, "profile") else None
    firm = profile.firm if profile else "No profile"
    print(f"  - {bh.username}: {firm}")

