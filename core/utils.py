"""Small helpers shared by the views."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect
from django.utils import timezone

from .models import Notification


# --------------------------------------------------------------------------
# Access control
# --------------------------------------------------------------------------
def member_required(view):
    """Logged in + profile completed (onboarding finished)."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.profile_completed:
            return redirect("complete_profile")
        # update "last seen" at most once a minute
        now = timezone.now()
        if not user.last_seen or (now - user.last_seen).total_seconds() > 60:
            user.last_seen = now
            user.save(update_fields=["last_seen"])
        return view(request, *args, **kwargs)

    return wrapper


# --------------------------------------------------------------------------
# Rate limiting (login and password reset)
# --------------------------------------------------------------------------
def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "unknown")


def rate_limited(request, scope, limit=5, window=600, key_extra=""):
    """Return True when the caller exceeded `limit` hits in `window` seconds."""
    key = f"rl:{scope}:{client_ip(request)}:{key_extra.lower()}"
    hits = cache.get(key, 0)
    if hits >= limit:
        return True
    cache.set(key, hits + 1, window)
    return False


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
PREFERENCE_FOR_TYPE = {
    "connection_request": "notify_connections",
    "connection_accepted": "notify_connections",
    "message": "notify_messages",
    "like": "notify_posts",
    "comment": "notify_posts",
    "event": "notify_events",
    "event_reminder": "notify_events",
    "community": "notify_events",
}


def notify(user, type, title, body="", link="", actor=None):
    """Create a notification unless the user disabled this category."""
    if actor is not None and actor.pk == user.pk:
        return None
    pref = PREFERENCE_FOR_TYPE.get(type)
    if pref and not getattr(user, pref, True):
        return None
    return Notification.objects.create(user=user, actor=actor, type=type, title=title, body=body[:255], link=link)


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def safe_next(request, default="home"):
    """Redirect to ?next / POST next only if it is a local URL (no open redirect)."""
    from django.utils.http import url_has_allowed_host_and_scheme

    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(default)
