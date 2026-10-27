"""
Private messaging.

"Real-time" is implemented with lightweight polling (the chat page asks the
server for new messages every 3 seconds). It is simple, needs no extra
server (no Redis / WebSocket), and could later be replaced by Django Channels.
"""
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..models import Conversation, Message, Notification, User
from ..utils import is_ajax, member_required, notify


def _conversation_list(user, q=""):
    hidden = user.blocked_ids()
    convs = (Conversation.objects.filter(participants=user)
             .annotate(unread=Count("messages", filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=user)))
             .prefetch_related("participants")
             .order_by("-updated_at"))
    result = []
    for c in convs:
        other = c.other(user)
        if other.pk in hidden:
            continue
        if q and q.lower() not in other.full_name.lower():
            continue
        last = c.last_message
        if last is None:
            continue
        c.other_user, c.last = other, last
        result.append(c)
    return result


def _get_conversation(user, pk):
    conv = get_object_or_404(Conversation, pk=pk)
    if not conv.participants.filter(pk=user.pk).exists():  # only participants may read it
        raise Http404
    return conv


@member_required
def inbox(request):
    q = request.GET.get("q", "").strip()
    return render(request, "chat/inbox.html", {
        "conversations": _conversation_list(request.user, q), "q": q,
        "contacts": request.user.connections().filter(is_active=True).order_by("-last_seen")[:12],
    })


@member_required
def start_chat(request, user_id):
    other = get_object_or_404(User, pk=user_id, is_active=True)
    if other == request.user:
        return redirect("inbox")
    existing = Conversation.between(request.user, other, create=False)
    if existing:
        return redirect("conversation", pk=existing.pk)
    if not other.can_receive_message_from(request.user):
        messages.error(request, f"{other.first_name_display} only accepts messages from connections.")
        return redirect(other.get_absolute_url())
    conv = Conversation.between(request.user, other)
    return redirect("conversation", pk=conv.pk)


@member_required
def conversation(request, pk):
    user = request.user
    conv = _get_conversation(user, pk)
    other = conv.other(user)
    if other.has_blocked(user):
        raise Http404
    # mark as read
    conv.messages.filter(read_at__isnull=True).exclude(sender=user).update(read_at=timezone.now())
    Notification.objects.filter(user=user, type="message", actor=other, is_read=False).update(is_read=True)
    q = request.GET.get("q", "").strip()
    return render(request, "chat/conversation.html", {
        "conv": conv, "other": other,
        "chat_messages": conv.messages.select_related("sender"),
        "can_send": other.can_receive_message_from(user),
        "conversations": _conversation_list(user, q), "q": q,
    })


@member_required
@require_POST
def send_message(request, pk):
    user = request.user
    conv = _get_conversation(user, pk)
    other = conv.other(user)
    text = request.POST.get("text", "").strip()[:2000]
    if not other.can_receive_message_from(user):
        error = "You can't message this student."
        if is_ajax(request):
            return JsonResponse({"error": error}, status=403)
        messages.error(request, error)
        return redirect("conversation", pk=pk)
    if not text:
        if is_ajax(request):
            return JsonResponse({"error": "Empty message."}, status=400)
        return redirect("conversation", pk=pk)

    msg = Message.objects.create(conversation=conv, sender=user, text=text)
    conv.updated_at = msg.created_at
    conv.save(update_fields=["updated_at"])
    # one unread "message" notification per sender is enough
    if not Notification.objects.filter(user=other, actor=user, type="message", is_read=False).exists():
        notify(other, "message", f"New message from {user.full_name}", text[:120], f"/messages/{conv.pk}/", actor=user)
    if is_ajax(request):
        html = render_to_string("chat/_message.html", {"m": msg, "user": user}, request=request)
        return JsonResponse({"id": msg.pk, "html": html})
    return redirect("conversation", pk=pk)


@member_required
def poll_messages(request, pk):
    """Returns messages newer than ?after=<id> and marks them as read."""
    user = request.user
    conv = _get_conversation(user, pk)
    after = request.GET.get("after", "0")
    after = int(after) if after.isdigit() else 0
    new = list(conv.messages.filter(pk__gt=after).select_related("sender"))
    conv.messages.filter(pk__gt=after, read_at__isnull=True).exclude(sender=user).update(read_at=timezone.now())
    other = conv.other(user)
    if any(m.sender_id != user.pk for m in new):  # the chat is open: no need to notify
        Notification.objects.filter(user=user, type="message", actor=other, is_read=False).update(is_read=True)
    html = "".join(render_to_string("chat/_message.html", {"m": m, "user": user}, request=request)
                   for m in new if m.sender_id != user.pk)
    last_mine = conv.messages.filter(sender=user).order_by("-pk").first()
    return JsonResponse({
        "html": html,
        "last_id": new[-1].pk if new else after,
        "online": other.is_online,
        "seen": bool(last_mine and last_mine.read_at),
    })
