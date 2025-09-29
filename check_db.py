from core.models import PriceSubmission, UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile, AdminProfile
from django.contrib.auth.models import User

# Check pending submissions
pending_count = PriceSubmission.objects.filter(status="PENDING").count()
total_submissions = PriceSubmission.objects.count()
print("Total submissions:", total_submissions)
print("Pending submissions:", pending_count)

# Check user profiles
users = User.objects.all()
print("Total users:", users.count())

for user in users:
    print(f"User: {user.username}")
    print(f"  - Is superuser: {user.is_superuser}")
    
    try:
        buyer_profile = BuyerProfile.objects.get(user=user)
        print(f"  - Buyer profile: {buyer_profile}")
    except BuyerProfile.DoesNotExist:
        pass
    
    try:
        category_head_profile = CategoryHeadProfile.objects.get(user=user)
        print(f"  - Category head profile: {category_head_profile}")
    except CategoryHeadProfile.DoesNotExist:
        pass
    
    try:
        business_head_profile = BusinessHeadProfile.objects.get(user=user)
        print(f"  - Business head profile: {business_head_profile}")
    except BusinessHeadProfile.DoesNotExist:
        pass
    
    try:
        admin_profile = AdminProfile.objects.get(user=user)
        print(f"  - Admin profile: {admin_profile}")
    except AdminProfile.DoesNotExist:
        pass

