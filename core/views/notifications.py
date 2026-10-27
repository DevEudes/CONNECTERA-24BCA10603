"""Notification center."""
from datetime import timedelta

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Notification
from ..utils import is_ajax, member_required
from .events import create_event_reminders


@member_required
def notification_list(request):
    user = request.user
    create_event_reminders(user)
    tab = request.GET.get("tab", "all")
    qs = user.notifications.select_related("actor")
    if tab == "unread":
        qs = qs.filter(is_read=False)
    elif tab == "requests":
        qs = qs.filter(type__in=["connection_request", "connection_accepted"])
    notes = list(qs[:80])

    now = timezone.localtime()
    today = now.date()
    groups = {"Today": [], "Yesterday": [], "This week": [], "Earlier": []}
    for n in notes:
        d = timezone.localtime(n.created_at).date()
        if d == today:
            groups["Today"].append(n)
        elif d == today - timedelta(days=1):
            groups["Yesterday"].append(n)
        elif d > today - timedelta(days=7):
            groups["This week"].append(n)
        else:
            groups["Earlier"].append(n)
    return render(request, "notifications/list.html", {
        "groups": [(k, v) for k, v in groups.items() if v], "tab": tab, "empty": not notes,
    })


@member_required
def open_notification(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    link = n.link if n.link.startswith("/") and not n.link.startswith("//") else "/notifications/"
    return redirect(link)


@member_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    if is_ajax(request):
        return JsonResponse({"ok": True})
    return redirect("notifications")


@member_required
@require_POST
def clear_notifications(request):
    request.user.notifications.filter(is_read=True).delete()
    return redirect("notifications")


@member_required
def counts(request):
    """Small JSON endpoint used to refresh the badges in the navigation."""
    from ..context_processors import global_counts

    return JsonResponse(global_counts(request))
