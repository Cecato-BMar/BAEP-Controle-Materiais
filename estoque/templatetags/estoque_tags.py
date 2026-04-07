from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    try:
        return value - arg
    except (ValueError, TypeError):
        return 0

@register.filter
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()
