"""
Template tags for core app formatting and utilities.
"""

from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def format_currency(value):
    """Format a value as currency with ₹ symbol"""
    if value is None:
        return "₹0.00"
    
    try:
        amount = Decimal(str(value))
        return f"₹{amount:,.2f}"
    except (ValueError, TypeError):
        return "₹0.00"


@register.filter
def format_quantity(value, unit=""):
    """Format quantity with optional unit"""
    if value is None:
        return "0"
    
    try:
        quantity = Decimal(str(value))
        formatted = f"{quantity:,.2f}"
        if unit:
            formatted += f" {unit}"
        return formatted
    except (ValueError, TypeError):
        return "0"


@register.filter
def status_badge_class(status):
    """Get CSS class for status badge"""
    status_classes = {
        'PENDING': 'bg-yellow-100 text-yellow-800',
        'APPROVED': 'bg-green-100 text-green-800',
        'CANCELLED': 'bg-red-100 text-red-800'
    }
    return status_classes.get(status, 'bg-gray-100 text-gray-800')


@register.filter
def role_badge_class(role):
    """Get CSS class for role badge"""
    role_classes = {
        'BUYER': 'bg-blue-100 text-blue-800',
        'CATEGORY_HEAD': 'bg-purple-100 text-purple-800',
        'BUSINESS_HEAD': 'bg-indigo-100 text-indigo-800',
        'ADMIN': 'bg-red-100 text-red-800'
    }
    return role_classes.get(role, 'bg-gray-100 text-gray-800')


@register.filter
def percentage(value, total):
    """Calculate percentage"""
    if not total or total == 0:
        return 0
    
    try:
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.simple_tag
def query_transform(request, **kwargs):
    """Transform query parameters for URL building"""
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value:
            query[key] = value
        elif key in query:
            del query[key]
    return query.urlencode()


@register.inclusion_tag('core/components/pagination.html', takes_context=True)
def render_pagination(context, page_obj):
    """Render pagination component"""
    return {
        'page_obj': page_obj,
        'request': context['request']
    }


@register.inclusion_tag('core/components/status_badge.html')
def status_badge(status):
    """Render status badge component"""
    return {
        'status': status,
        'badge_class': status_badge_class(status)
    }


@register.inclusion_tag('core/components/role_badge.html')
def role_badge(role):
    """Render role badge component"""
    return {
        'role': role,
        'badge_class': role_badge_class(role)
    }


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary in template"""
    return dictionary.get(key)


@register.filter
def multiply(value, arg):
    """Multiply two values"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def subtract(value, arg):
    """Subtract two values"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def add_class(field, css_class):
    """Add CSS class to form field"""
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    return field


@register.filter
def field_type(field):
    """Get form field type"""
    return field.field.widget.__class__.__name__.lower()


@register.simple_tag
def active_page(request, url_name):
    """Check if current page matches URL name"""
    try:
        from django.urls import resolve, reverse
        current_url = resolve(request.path_info).url_name
        return 'active' if current_url == url_name else ''
    except:
        return ''


@register.filter
def highlight_row_class(submission):
    """Get CSS class for highlighting min/max price rows"""
    classes = []
    
    if hasattr(submission, 'is_min_price') and submission.is_min_price:
        classes.append('highlight-min')
    
    if hasattr(submission, 'is_max_price') and submission.is_max_price:
        classes.append('highlight-max')
    
    return ' '.join(classes)


@register.simple_tag
def format_date_range(date_from, date_to):
    """Format date range for display"""
    if date_from and date_to:
        if date_from == date_to:
            return date_from.strftime('%B %d, %Y')
        else:
            return f"{date_from.strftime('%B %d, %Y')} - {date_to.strftime('%B %d, %Y')}"
    elif date_from:
        return f"From {date_from.strftime('%B %d, %Y')}"
    elif date_to:
        return f"Until {date_to.strftime('%B %d, %Y')}"
    else:
        return "All dates"


@register.filter
def truncate_words_smart(value, length):
    """Truncate text smartly at word boundaries"""
    if not value:
        return ""
    
    if len(value) <= length:
        return value
    
    truncated = value[:length]
    
    # Find the last space to avoid cutting words
    last_space = truncated.rfind(' ')
    if last_space > length * 0.7:  # Only if we don't lose too much text
        truncated = truncated[:last_space]
    
    return truncated + "..."