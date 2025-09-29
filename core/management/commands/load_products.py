"""
Management command to load comprehensive product data from CSV file.
Creates hierarchical structure: Category -> Main Category -> Sub Category -> Product
"""

import csv
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings

from core.models import ProductCategory, MainCategory, SubCategory, Product


class Command(BaseCommand):
    help = 'Load comprehensive product data from products.csv file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-file',
            type=str,
            default='products.csv',
            help='Path to CSV file (relative to project root)',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing products before loading new data',
        )
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        # Construct full path
        if not os.path.isabs(csv_file):
            csv_file = os.path.join(settings.BASE_DIR, csv_file)
        
        if not os.path.exists(csv_file):
            self.stdout.write(
                self.style.ERROR(f'❌ CSV file not found: {csv_file}')
            )
            return
        
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('⚠️  Resetting product data. This will delete existing products!')
            )
            response = input('Are you sure? Type "yes" to continue: ')
            if response != 'yes':
                self.stdout.write('Cancelled.')
                return
            
            Product.objects.all().delete()
            self.stdout.write('✅ Existing products deleted.')
        
        with transaction.atomic():
            self.stdout.write(f'📊 Loading products from {csv_file}...')
            self.load_products_from_csv(csv_file)
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully loaded product data!')
            )
    
    def load_products_from_csv(self, csv_file):
        """Load products from CSV file with full hierarchical structure"""
        
        # Track statistics
        created_products = 0
        existing_products = 0
        created_categories = 0
        created_main_categories = 0 
        created_sub_categories = 0
        
        # Cache for created objects to avoid duplicate queries
        category_cache = {}
        main_category_cache = {}
        sub_category_cache = {}
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                name = row['Name'].strip()
                category_name = row['Category'].strip()  # Fresh Fruit or Fresh Veg
                main_category_name = row['Main Cat.'].strip()  # Fruit N Vegetable
                sub_category_name = row['Sub Cat'].strip()  # Apple N Pear, Bananas, etc.
                
                # 1. Create or get Category (Fresh Fruit/Fresh Veg)
                if category_name not in category_cache:
                    # Map category names to standardized versions
                    if category_name == 'Fresh Fruit':
                        std_name, std_code = 'Fruits', 'FRUITS'
                    elif category_name == 'Fresh Veg':
                        std_name, std_code = 'Vegetables', 'VEGETABLES'
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Unknown category: {category_name} for {name}')
                        )
                        continue
                    
                    category, created = ProductCategory.objects.get_or_create(
                        code=std_code,
                        defaults={'name': std_name}
                    )
                    category_cache[category_name] = category
                    if created:
                        created_categories += 1
                        self.stdout.write(f'  ✅ Created category: {std_name}')
                else:
                    category = category_cache[category_name]
                
                # 2. Create or get MainCategory
                main_cat_key = main_category_name
                if main_cat_key not in main_category_cache:
                    main_cat_code = main_category_name.upper().replace(' ', '_').replace('&', 'N')
                    main_category, created = MainCategory.objects.get_or_create(
                        code=main_cat_code,
                        defaults={'name': main_category_name}
                    )
                    main_category_cache[main_cat_key] = main_category
                    if created:
                        created_main_categories += 1
                        self.stdout.write(f'  ✅ Created main category: {main_category_name}')
                else:
                    main_category = main_category_cache[main_cat_key]
                
                # 3. Create or get SubCategory
                sub_cat_key = f"{category_name}:{sub_category_name}"
                if sub_cat_key not in sub_category_cache:
                    sub_cat_code = sub_category_name.upper().replace(' ', '_').replace('&', 'N')
                    sub_category, created = SubCategory.objects.get_or_create(
                        code=sub_cat_code,
                        defaults={
                            'name': sub_category_name,
                            'category': category,
                            'main_category': main_category
                        }
                    )
                    sub_category_cache[sub_cat_key] = sub_category
                    if created:
                        created_sub_categories += 1
                        self.stdout.write(f'  ✅ Created sub category: {sub_category_name} ({category.name})')
                else:
                    sub_category = sub_category_cache[sub_cat_key]
                
                # 4. Create or get Product
                product, created = Product.objects.get_or_create(
                    name=name,
                    defaults={
                        'category': category,
                        'main_category': main_category,
                        'sub_category': sub_category
                    }
                )
                
                if created:
                    created_products += 1
                    self.stdout.write(f'  ✅ Created product: {name} ({sub_category.name})')
                else:
                    # Update existing product with hierarchical information
                    product.category = category
                    product.main_category = main_category
                    product.sub_category = sub_category
                    product.save()
                    existing_products += 1
                    self.stdout.write(f'  🔄 Updated product: {name} ({sub_category.name})')
        
        # Report statistics
        self.stdout.write('\n📈 Import Summary:')
        self.stdout.write(f'  • Categories created: {created_categories}')
        self.stdout.write(f'  • Main categories created: {created_main_categories}')
        self.stdout.write(f'  • Sub categories created: {created_sub_categories}')
        self.stdout.write(f'  • Products created: {created_products}')
        self.stdout.write(f'  • Products updated: {existing_products}')
        
        # Show hierarchy structure
        self.stdout.write('\n�️  Hierarchical Structure Created:')
        for category in ProductCategory.objects.all():
            self.stdout.write(f'  📁 {category.name}')
            for main_cat in MainCategory.objects.filter(subcategories__category=category).distinct():
                self.stdout.write(f'    � {main_cat.name}')
                for sub_cat in category.subcategories.filter(main_category=main_cat):
                    product_count = sub_cat.products.count()
                    self.stdout.write(f'      📄 {sub_cat.name} ({product_count} products)')
        
        # Success message
        self.stdout.write('\n🎉 Hierarchical product structure successfully created!')
        self.stdout.write('   Structure: Category → Main Category → Sub Category → Product')