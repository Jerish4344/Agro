"""
Management command to seed initial data for the application.
Creates firms, categories, products, locations, farmers, and demo users.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.utils import timezone

from core.models import (
    Firm, Location, Farmer, ProductCategory, Product,
    UserProfile, BuyerProfile, CategoryHeadProfile, BusinessHeadProfile
)


class Command(BaseCommand):
    help = 'Seed initial data for the application'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='Skip creating demo users',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all data before seeding (DESTRUCTIVE)',
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('⚠️  Resetting all data. This will delete existing data!')
            )
            response = input('Are you sure? Type "yes" to continue: ')
            if response != 'yes':
                self.stdout.write('Cancelled.')
                return
            
            self.reset_data()
        
        with transaction.atomic():
            self.stdout.write('🌱 Seeding initial data...')
            
            # Create firms
            firms = self.create_firms()
            
            # Create categories
            categories = self.create_categories()
            
            # Create products
            products = self.create_products(categories)
            
            # Create locations
            locations = self.create_locations()
            
            # Create farmers
            farmers = self.create_farmers(locations)
            
            # Create demo users if not skipped
            if not options['skip_users']:
                self.create_demo_users(firms[0], categories)  # Use first firm
            
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully seeded initial data!')
            )
    
    def reset_data(self):
        """Reset all application data"""
        self.stdout.write('🗑️  Resetting data...')
        
        # Delete in correct order to handle foreign keys
        from core.models import PriceSubmission
        PriceSubmission.objects.all().delete()
        
        BuyerProfile.objects.all().delete()
        CategoryHeadProfile.objects.all().delete()
        BusinessHeadProfile.objects.all().delete()
        UserProfile.objects.all().delete()
        
        # Delete users except superusers
        User.objects.filter(is_superuser=False).delete()
        
        Farmer.objects.all().delete()
        Product.objects.all().delete()
        ProductCategory.objects.all().delete()
        Location.objects.all().delete()
        Firm.objects.all().delete()
        
        self.stdout.write('✅ Data reset complete.')
    
    def create_firms(self):
        """Create initial firms"""
        self.stdout.write('📊 Creating firms...')
        
        firms_data = [
            {'name': 'Ramachandran', 'code': 'RAM'},
            {'name': 'Jeyachandran', 'code': 'JEY'},
        ]
        
        firms = []
        for firm_data in firms_data:
            firm, created = Firm.objects.get_or_create(
                code=firm_data['code'],
                defaults={'name': firm_data['name']}
            )
            firms.append(firm)
            
            if created:
                self.stdout.write(f'  ✅ Created firm: {firm.name}')
            else:
                self.stdout.write(f'  ℹ️  Firm already exists: {firm.name}')
        
        return firms
    
    def create_categories(self):
        """Create product categories"""
        self.stdout.write('🏷️  Creating categories...')
        
        categories_data = [
            {'name': 'Fruits', 'code': 'FRT'},
            {'name': 'Vegetables', 'code': 'VEG'},
        ]
        
        categories = []
        for cat_data in categories_data:
            category, created = ProductCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults={'name': cat_data['name']}
            )
            categories.append(category)
            
            if created:
                self.stdout.write(f'  ✅ Created category: {category.name}')
            else:
                self.stdout.write(f'  ℹ️  Category already exists: {category.name}')
        
        return categories
    
    def create_products(self, categories):
        """Create initial products"""
        self.stdout.write('🍎 Creating products...')
        
        fruits_category = next(cat for cat in categories if cat.code == 'FRT')
        vegetables_category = next(cat for cat in categories if cat.code == 'VEG')
        
        products_data = [
            # Fruits
            {'name': 'Apple', 'category': fruits_category},
            {'name': 'Banana', 'category': fruits_category},
            {'name': 'Orange', 'category': fruits_category},
            {'name': 'Mango', 'category': fruits_category},
            {'name': 'Grapes', 'category': fruits_category},
            {'name': 'Pomegranate', 'category': fruits_category},
            
            # Vegetables
            {'name': 'Tomato', 'category': vegetables_category},
            {'name': 'Brinjal', 'category': vegetables_category},
            {'name': 'Onion', 'category': vegetables_category},
            {'name': 'Potato', 'category': vegetables_category},
            {'name': 'Carrot', 'category': vegetables_category},
            {'name': 'Cabbage', 'category': vegetables_category},
            {'name': 'Cauliflower', 'category': vegetables_category},
            {'name': 'Green Beans', 'category': vegetables_category},
        ]
        
        products = []
        for product_data in products_data:
            product, created = Product.objects.get_or_create(
                name=product_data['name'],
                category=product_data['category']
            )
            products.append(product)
            
            if created:
                self.stdout.write(f'  ✅ Created product: {product.name} ({product.category.name})')
            else:
                self.stdout.write(f'  ℹ️  Product already exists: {product.name}')
        
        return products
    
    def create_locations(self):
        """Create initial locations"""
        self.stdout.write('📍 Creating locations...')
        
        locations_data = [
            {'name': 'Coimbatore', 'region_code': 'CBE'},
            {'name': 'Erode', 'region_code': 'ERD'},
            {'name': 'Salem', 'region_code': 'SLM'},
            {'name': 'Tirupur', 'region_code': 'TPR'},
            {'name': 'Karur', 'region_code': 'KRR'},
            {'name': 'Namakkal', 'region_code': 'NMK'},
        ]
        
        locations = []
        for loc_data in locations_data:
            location, created = Location.objects.get_or_create(
                name=loc_data['name'],
                region_code=loc_data['region_code']
            )
            locations.append(location)
            
            if created:
                self.stdout.write(f'  ✅ Created location: {location.name} ({location.region_code})')
            else:
                self.stdout.write(f'  ℹ️  Location already exists: {location.name}')
        
        return locations
    
    def create_farmers(self, locations):
        """Create initial farmers"""
        self.stdout.write('👨‍🌾 Creating farmers...')
        
        import random
        
        farmer_names = [
            'Rajesh Kumar', 'Suresh Babu', 'Murugan', 'Selvam',
            'Ravi Chandran', 'Krishna Moorthy', 'Ganesan', 'Prakash',
            'Senthil Kumar', 'Ramesh Babu', 'Vignesh', 'Dinesh',
            'Mahesh Kumar', 'Venkatesh', 'Surya', 'Arun Kumar'
        ]
        
        farmers = []
        for i, name in enumerate(farmer_names):
            location = locations[i % len(locations)]  # Distribute across locations
            
            farmer, created = Farmer.objects.get_or_create(
                name=name,
                location=location,
                defaults={
                    'phone': f'+91 9{random.randint(100000000, 999999999)}'
                }
            )
            farmers.append(farmer)
            
            if created:
                self.stdout.write(f'  ✅ Created farmer: {farmer.name} ({farmer.location.name})')
            else:
                self.stdout.write(f'  ℹ️  Farmer already exists: {farmer.name}')
        
        return farmers
    
    def create_demo_users(self, firm, categories):
        """Create demo users with different roles"""
        self.stdout.write('👥 Creating demo users...')
        
        # Get or create groups
        buyer_group, _ = Group.objects.get_or_create(name='BUYER')
        category_head_group, _ = Group.objects.get_or_create(name='CATEGORY_HEAD')
        business_head_group, _ = Group.objects.get_or_create(name='BUSINESS_HEAD')
        admin_group, _ = Group.objects.get_or_create(name='ADMIN')
        
        fruits_category = next(cat for cat in categories if cat.code == 'FRT')
        vegetables_category = next(cat for cat in categories if cat.code == 'VEG')
        
        users_data = [
            {
                'username': 'buyer1',
                'first_name': 'John',
                'last_name': 'Buyer',
                'email': 'buyer1@example.com',
                'role': 'buyer',
                'categories': [fruits_category, vegetables_category]
            },
            {
                'username': 'buyer2',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'email': 'buyer2@example.com',
                'role': 'buyer',
                'categories': [fruits_category]
            },
            {
                'username': 'chead_fruits',
                'first_name': 'Mike',
                'last_name': 'Johnson',
                'email': 'chead.fruits@example.com',
                'role': 'category_head',
                'categories': [fruits_category]
            },
            {
                'username': 'chead_veg',
                'first_name': 'Sarah',
                'last_name': 'Wilson',
                'email': 'chead.veg@example.com',
                'role': 'category_head',
                'categories': [vegetables_category]
            },
            {
                'username': 'chead_both',
                'first_name': 'David',
                'last_name': 'Brown',
                'email': 'chead.both@example.com',
                'role': 'category_head',
                'categories': [fruits_category, vegetables_category]
            },
            {
                'username': 'bhead',
                'first_name': 'Lisa',
                'last_name': 'Davis',
                'email': 'bhead@example.com',
                'role': 'business_head',
                'categories': []
            },
            {
                'username': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@example.com',
                'role': 'admin',
                'categories': []
            }
        ]
        
        for user_data in users_data:
            # Create user
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'email': user_data['email'],
                    'is_staff': user_data['role'] in ['admin', 'business_head'],
                    'is_superuser': user_data['role'] == 'admin'
                }
            )
            
            if created:
                user.set_password('password123')  # Set default password
                user.save()
                self.stdout.write(f'  ✅ Created user: {user.username}')
            else:
                self.stdout.write(f'  ℹ️  User already exists: {user.username}')
                continue  # Skip if user already exists
            
            # Add to appropriate group
            if user_data['role'] == 'buyer':
                user.groups.add(buyer_group)
            elif user_data['role'] == 'category_head':
                user.groups.add(category_head_group)
            elif user_data['role'] == 'business_head':
                user.groups.add(business_head_group)
            elif user_data['role'] == 'admin':
                user.groups.add(admin_group)
            
            # Create user profile
            user_profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'firm': firm if user_data['role'] != 'admin' else None,
                    'phone': f'+91 9876543{user.id:03d}'
                }
            )
            
            # Create role-specific profiles
            if user_data['role'] == 'buyer':
                buyer_profile, _ = BuyerProfile.objects.get_or_create(
                    user_profile=user_profile
                )
                buyer_profile.allowed_categories.set(user_data['categories'])
                
            elif user_data['role'] == 'category_head':
                category_head_profile, _ = CategoryHeadProfile.objects.get_or_create(
                    user_profile=user_profile
                )
                category_head_profile.scoped_categories.set(user_data['categories'])
                
            elif user_data['role'] == 'business_head':
                BusinessHeadProfile.objects.get_or_create(
                    user_profile=user_profile
                )
        
        self.stdout.write('  📋 Demo user credentials:')
        self.stdout.write('    Username: buyer1, Password: password123')
        self.stdout.write('    Username: chead_fruits, Password: password123')
        self.stdout.write('    Username: bhead, Password: password123')
        self.stdout.write('    Username: admin, Password: password123')