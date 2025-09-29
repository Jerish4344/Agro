from core.models import PriceSubmission, UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile
from django.contrib.auth.models import User

# Check pending submissions
pending_count = PriceSubmission.objects.filter(status="PENDING").count()
total_submissions = PriceSubmission.objects.count()
print("Total submissions:", total_submissions)
print("Pending submissions:", pending_count)

# Check submissions in detail
submissions = PriceSubmission.objects.all()
for submission in submissions:
    print(f"Submission {submission.id}: {submission.status} - Firm: {submission.firm}")

# Check user profiles
users = User.objects.all()
print("Total users:", users.count())

for user in users:
    print(f"User: {user.username} (ID: {user.id})")
    print(f"  - Is superuser: {user.is_superuser}")
    
    try:
        buyer_profile = BuyerProfile.objects.get(user=user)
        print(f"  - Buyer profile: {buyer_profile} - Firm: {buyer_profile.firm}")
    except BuyerProfile.DoesNotExist:
        pass
    
    try:
        category_head_profile = CategoryHeadProfile.objects.get(user=user)
        print(f"  - Category head profile: {category_head_profile} - Category: {category_head_profile.category}")
    except CategoryHeadProfile.DoesNotExist:
        pass
    
    try:
        business_head_profile = BusinessHeadProfile.objects.get(user=user)
        print(f"  - Business head profile: {business_head_profile} - Firm: {business_head_profile.firm}")
    except BusinessHeadProfile.DoesNotExist:
        pass
    
    try:
        user_profile = UserProfile.objects.get(user=user)
        print(f"  - User profile: {user_profile} - Role: {user_profile.role}")
    except UserProfile.DoesNotExist:
        pass

