"""
Migration to create Django Groups for role-based access control.
"""

from django.db import migrations
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def create_groups(apps, schema_editor):
    """Create Django groups for different user roles"""
    
    # Define role groups
    roles = [
        'BUYER',
        'CATEGORY_HEAD', 
        'BUSINESS_HEAD',
        'ADMIN'
    ]
    
    # Create groups
    for role in roles:
        group, created = Group.objects.get_or_create(name=role)
        if created:
            print(f"Created group: {role}")
    
    # Get content types
    PriceSubmission = apps.get_model('core', 'PriceSubmission')
    submission_ct = ContentType.objects.get_for_model(PriceSubmission)
    
    # Define permissions for each role
    buyer_permissions = [
        'add_pricesubmission',
        'view_pricesubmission', 
        'change_pricesubmission',  # Only their own
    ]
    
    category_head_permissions = [
        'view_pricesubmission',
        'approve_pricesubmission',  # Custom permission
    ]
    
    business_head_permissions = [
        'view_pricesubmission',
        'approve_pricesubmission',
        'view_reports',  # Custom permission
    ]
    
    admin_permissions = [
        'view_pricesubmission',
        'add_pricesubmission',
        'change_pricesubmission',
        'delete_pricesubmission',
        'approve_pricesubmission',
        'view_reports',
        'manage_users',  # Custom permission
    ]
    
    # Assign permissions to groups
    try:
        buyer_group = Group.objects.get(name='BUYER')
        for perm_code in buyer_permissions:
            try:
                permission = Permission.objects.get(codename=perm_code)
                buyer_group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"Permission {perm_code} not found")
                
        category_head_group = Group.objects.get(name='CATEGORY_HEAD')
        for perm_code in category_head_permissions:
            try:
                permission = Permission.objects.get(codename=perm_code)
                category_head_group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"Permission {perm_code} not found")
                
        business_head_group = Group.objects.get(name='BUSINESS_HEAD')
        for perm_code in business_head_permissions:
            try:
                permission = Permission.objects.get(codename=perm_code)
                business_head_group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"Permission {perm_code} not found")
                
        admin_group = Group.objects.get(name='ADMIN')
        for perm_code in admin_permissions:
            try:
                permission = Permission.objects.get(codename=perm_code)
                admin_group.permissions.add(permission)
            except Permission.DoesNotExist:
                print(f"Permission {perm_code} not found")
                
    except Group.DoesNotExist as e:
        print(f"Group not found: {e}")


def reverse_create_groups(apps, schema_editor):
    """Remove the created groups"""
    roles = ['BUYER', 'CATEGORY_HEAD', 'BUSINESS_HEAD', 'ADMIN']
    
    for role in roles:
        try:
            group = Group.objects.get(name=role)
            group.delete()
            print(f"Deleted group: {role}")
        except Group.DoesNotExist:
            print(f"Group {role} not found for deletion")


class Migration(migrations.Migration):
    
    dependencies = [
        ('core', '0001_initial'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    
    operations = [
        migrations.RunPython(create_groups, reverse_create_groups),
    ]