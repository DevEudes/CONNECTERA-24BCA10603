from django.db.models import Q

from .models import Connection, Message


def global_counts(request):
    """Badges shown in the navigation (notifications, messages, requests)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {
        "unread_notifications": user.notifications.filter(is_read=False).count(),
        "unread_messages": Message.objects.filter(conversation__participants=user, read_at__isnull=True)
        .filter(~Q(sender=user)).count(),
        "pending_requests": Connection.objects.filter(receiver=user, status=Connection.PENDING).count(),
    }
