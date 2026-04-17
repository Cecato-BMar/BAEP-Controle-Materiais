from django import template

register = template.Library()

@register.filter
def get_attribute(obj, attr):
    """Obtém um atributo de um objeto dinamicamente."""
    return bool(getattr(obj, attr, False))

@register.filter
def split_string(value, arg):
    """Divide uma string por um delimitador."""
    return value.split(arg)
