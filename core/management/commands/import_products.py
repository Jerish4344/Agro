"""
Django management command to import products from CSV file.
Usage: python manage.py import_products path/to/products.csv
"""

import csv
import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Product, ProductCategory, MainCategory, SubCategory


class Command(BaseCommand):
    help = 'Import products from CSV file with hierarchical categories'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing products data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be imported without making changes'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing products before importing (CAUTION: This will delete all products!)'
        )
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Validate CSV headers
                expected_headers = ['Name', 'Category', 'Main Cat.', 'Sub Cat']
                if not all(header in reader.fieldnames for header in expected_headers):
                    raise CommandError(
                        f"CSV file must contain headers: {', '.join(expected_headers)}\n"
                        f"Found headers: {', '.join(reader.fieldnames or [])}"
                    )
                
                products_data = list(reader)
                
        except FileNotFoundError:
            raise CommandError(f"CSV file '{csv_file}' not found.")
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {str(e)}")
        
        if not products_data:
            raise CommandError("CSV file is empty or has no data rows.")
        
        self.stdout.write(f"Found {len(products_data)} products in CSV file.")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        if clear_existing and not dry_run:
            confirm = input("Are you sure you want to delete all existing products? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write("Import cancelled.")
                return
        
        # Statistics
        stats = {
            'categories_created': 0,
            'main_categories_created': 0,
            'sub_categories_created': 0,
            'products_created': 0,
            'products_updated': 0,
            'errors': []
        }
        
        try:
            with transaction.atomic():
                if clear_existing and not dry_run:
                    self.stdout.write("Clearing existing products...")
                    Product.objects.all().delete()
                    # Note: Categories are not deleted as they might be referenced elsewhere
                
                # Process each product
                for row_num, row in enumerate(products_data, start=2):  # Start at 2 for Excel row numbering
                    try:
                        name = row['Name'].strip()
                        category_name = row['Category'].strip()
                        main_cat_name = row['Main Cat.'].strip()
                        sub_cat_name = row['Sub Cat'].strip()
                        
                        if not all([name, category_name, main_cat_name, sub_cat_name]):
                            stats['errors'].append(f"Row {row_num}: Missing required fields")
                            continue
                        
                        if dry_run:
                            self.stdout.write(f"Would process: {name} ({category_name} > {main_cat_name} > {sub_cat_name})")
                            continue
                        
                        # Get or create Category
                        category, created = ProductCategory.objects.get_or_create(
                            name=category_name,
                            defaults={'code': category_name.replace(' ', '_').lower()}
                        )
                        if created:
                            stats['categories_created'] += 1
                            self.stdout.write(f"Created category: {category_name}")
                        
                        # Get or create Main Category
                        main_category, created = MainCategory.objects.get_or_create(
                            name=main_cat_name,
                            defaults={
                                'code': main_cat_name.replace(' ', '_').lower(),
                                'description': f'{main_cat_name} in {category_name}'
                            }
                        )
                        if created:
                            stats['main_categories_created'] += 1
                            self.stdout.write(f"Created main category: {main_cat_name}")
                        
                        # Get or create Sub Category
                        sub_category, created = SubCategory.objects.get_or_create(
                            name=sub_cat_name,
                            category=category,
                            main_category=main_category,
                            defaults={
                                'code': sub_cat_name.replace(' ', '_').lower(),
                                'description': f'{sub_cat_name} in {main_cat_name}'
                            }
                        )
                        if created:
                            stats['sub_categories_created'] += 1
                            self.stdout.write(f"Created sub category: {sub_cat_name}")
                        
                        # Create or update Product
                        product, created = Product.objects.get_or_create(
                            name=name,
                            defaults={
                                'category': category,
                                'main_category': main_category,
                                'sub_category': sub_category
                            }
                        )
                        
                        if created:
                            stats['products_created'] += 1
                            self.stdout.write(f"Created product: {name}")
                        else:
                            # Update existing product with new category structure
                            product.category = category
                            product.main_category = main_category
                            product.sub_category = sub_category
                            product.save()
                            stats['products_updated'] += 1
                            self.stdout.write(f"Updated product: {name}")
                        
                    except Exception as e:
                        error_msg = f"Row {row_num}: Error processing '{row.get('Name', 'Unknown')}' - {str(e)}"
                        stats['errors'].append(error_msg)
                        self.stdout.write(self.style.ERROR(error_msg))
                        continue
                
                if dry_run:
                    self.stdout.write(self.style.SUCCESS(f"DRY RUN COMPLETE - Would process {len(products_data)} products"))
                    return
        
        except Exception as e:
            raise CommandError(f"Database error: {str(e)}")
        
        # Print summary
        self.stdout.write(self.style.SUCCESS("\n=== IMPORT SUMMARY ==="))
        self.stdout.write(f"Categories created: {stats['categories_created']}")
        self.stdout.write(f"Main categories created: {stats['main_categories_created']}")
        self.stdout.write(f"Sub categories created: {stats['sub_categories_created']}")
        self.stdout.write(f"Products created: {stats['products_created']}")
        self.stdout.write(f"Products updated: {stats['products_updated']}")
        
        if stats['errors']:
            self.stdout.write(self.style.ERROR(f"\nErrors encountered: {len(stats['errors'])}"))
            for error in stats['errors'][:10]:  # Show first 10 errors
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            if len(stats['errors']) > 10:
                self.stdout.write(self.style.ERROR(f"  ... and {len(stats['errors']) - 10} more errors"))
        
        total_processed = stats['products_created'] + stats['products_updated']
        self.stdout.write(self.style.SUCCESS(f"\n✅ Successfully processed {total_processed} products!"))