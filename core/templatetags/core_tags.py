from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def avatar(user, size=44, ring=False, online=False):
    """Profile photo, or coloured initials when the student has no photo."""
    if user is None:
        return ""
    classes = "avatar" + (" avatar-ring" if ring else "")
    dot = mark_safe('<span class="online-dot"></span>') if online and user.is_online else ""
    style = f"width:{size}px;height:{size}px;font-size:{max(int(size * 0.38), 10)}px"
    if user.avatar:
        return format_html('<span class="{}" style="{}"><img src="{}" alt="{}" loading="lazy">{}</span>',
                           classes, style, user.avatar.url, user.full_name, dot)
    return format_html('<span class="{} avatar-initials" style="{};background:{}" aria-label="{}">{}{}</span>',
                       classes, style, user.avatar_color, user.full_name, user.initials, dot)


@register.filter
def ago(value):
    """Compact relative time: now, 5m, 3h, Yesterday, Mon, 12 Oct."""
    if not value:
        return ""
    now = timezone.now()
    diff = now - value
    if diff < timedelta(minutes=1):
        return "now"
    if diff < timedelta(hours=1):
        return f"{int(diff.total_seconds() // 60)}m"
    if diff < timedelta(days=1):
        return f"{int(diff.total_seconds() // 3600)}h"
    local = timezone.localtime(value)
    if diff < timedelta(days=2):
        return "Yesterday"
    if diff < timedelta(days=7):
        return local.strftime("%a")
    if local.year == timezone.localtime(now).year:
        return local.strftime("%d %b")
    return local.strftime("%d %b %Y")


@register.filter
def in_set(value, collection):
    return value in collection


@register.filter
def get_item(mapping, key):
    return mapping.get(key) if mapping else None


@register.filter
def mod(value, n):
    try:
        return int(value) % int(n)
    except (TypeError, ValueError):
        return 0
