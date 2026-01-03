# gestion_stock/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='sub')
def sub(value, arg):
    """Soustrait arg de value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='subtract')
def subtract(value, arg):
    """Alias pour sub"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='abs')
def absolute(value):
    """Valeur absolue"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplie value par arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='divide')
def divide(value, arg):
    """Divise value par arg"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='timeuntil')
def timeuntil_filter(value, now=None):
    """Filtre pour calculer le temps restant"""
    from django.utils.timesince import timesince
    if now is None:
        from django.utils import timezone
        now = timezone.now()
    try:
        return timesince(value, now).split(',')[0]  # Prend seulement la première partie
    except:
        return ""

@register.filter(name='add')
def add(value, arg):
    """Additionne value et arg"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return int(value) + int(arg)
        except:
            return value