from core.models import ProductCategory, Product, PriceSubmission

# Check available categories and products
categories = ProductCategory.objects.all()
print("Available categories:")
for cat in categories:
    print(f"  - {cat.name} (ID: {cat.id})")
    products = Product.objects.filter(category=cat)
    for prod in products:
        print(f"    * {prod.name} (ID: {prod.id})")

print()
print("Current submissions:")
submissions = PriceSubmission.objects.all()
for sub in submissions:
    print(f"  - ID {sub.id}: {sub.product.name} ({sub.product.category.name}) - {sub.status}")

