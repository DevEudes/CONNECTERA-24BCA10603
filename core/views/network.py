"""Search students, connection requests (send / accept / decline / cancel / remove) and blocking."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ..models import Block, Connection, Interest, User
from ..recommendations import suggested_students
from ..utils import is_ajax, member_required, notify, safe_next


def _connection_states(user, people):
    """{user_id: 'connected' | 'sent' | 'received'} for buttons on profile cards."""
    ids = [p.pk for p in people]
    states = {}
    rows = Connection.objects.filter(
        Q(requester=user, receiver_id__in=ids) | Q(receiver=user, requester_id__in=ids)
    ).exclude(status=Connection.DECLINED)
    for c in rows:
        other = c.receiver_id if c.requester_id == user.pk else c.requester_id
        if c.status == Connection.ACCEPTED:
            states[other] = ("connected", c.pk)
        elif c.requester_id == user.pk:
            states[other] = ("sent", c.pk)
        else:
            states[other] = ("received", c.pk)
    for p in people:
        p.conn_state, p.conn_id = states.get(p.pk, ("none", None))
    return people


@member_required
def search(request):
    user = request.user
    q = request.GET.get("q", "").strip()
    filters = {k: request.GET.get(k, "").strip() for k in ["university", "course", "interest", "country", "year"]}

    people = (User.objects.filter(is_active=True, profile_completed=True, is_staff=False)
              .exclude(pk=user.pk).exclude(pk__in=user.blocked_ids())
              .exclude(Q(profile_visibility="private"))
              .prefetch_related("interests"))
    if q:
        people = people.filter(Q(full_name__icontains=q) | Q(university__icontains=q) | Q(course__icontains=q)
                               | Q(headline__icontains=q) | Q(interests__name__icontains=q)).distinct()
    if filters["university"]:
        people = people.filter(university=filters["university"])
    if filters["course"]:
        people = people.filter(course=filters["course"])
    if filters["country"]:
        people = people.filter(Q(country=filters["country"]) | Q(destination_country=filters["country"]))
    if filters["interest"]:
        people = people.filter(interests__pk=filters["interest"])
    if filters["year"].isdigit():
        people = people.filter(year=int(filters["year"]))

    searching = bool(q or any(filters.values()))
    page = Paginator(people.order_by("full_name"), 12).get_page(request.GET.get("page"))
    _connection_states(user, page.object_list)

    suggestions = [] if searching else _connection_states(user, suggested_students(user, limit=6))
    base = User.objects.filter(is_active=True, profile_completed=True, is_staff=False)
    query_string = request.GET.copy()
    query_string.pop("page", None)
    return render(request, "network/search.html", {
        "q": q, "filters": filters, "page": page, "searching": searching, "suggestions": suggestions,
        "universities": base.exclude(university="").values_list("university", flat=True).distinct().order_by("university"),
        "courses": base.exclude(course="").values_list("course", flat=True).distinct().order_by("course"),
        "countries": base.exclude(country="").values_list("country", flat=True).distinct().order_by("country"),
        "interests": Interest.objects.all(),
        "years": User.YEAR_CHOICES,
        "query_string": query_string.urlencode(),
    })


@member_required
def connections(request):
    user = request.user
    tab = request.GET.get("tab", "connections")
    received = Connection.objects.filter(receiver=user, status=Connection.PENDING).select_related("requester")
    sent = Connection.objects.filter(requester=user, status=Connection.PENDING).select_related("receiver")
    q = request.GET.get("q", "").strip()
    people = user.connections().filter(is_active=True)
    if q:
        people = people.filter(Q(full_name__icontains=q) | Q(university__icontains=q) | Q(course__icontains=q))
    return render(request, "network/connections.html", {
        "tab": tab, "received": received, "sent": sent, "people": people, "q": q,
        "blocked": User.objects.filter(blocked_by__blocker=user),
    })


def _respond(request, ok, text, state=None, status=200):
    if is_ajax(request):
        return JsonResponse({"ok": ok, "message": text, "state": state}, status=status)
    (messages.success if ok else messages.error)(request, text)
    return safe_next(request, "connections")


@member_required
@require_POST
def send_request(request, pk):
    me = request.user
    other = get_object_or_404(User, pk=pk, is_active=True)
    if other == me:
        return _respond(request, False, "You cannot connect with yourself.", status=400)
    if me.is_blocked_between(other):
        return _respond(request, False, "You cannot connect with this student.", status=403)

    existing = me.connection_with(other)
    if existing:
        if existing.status == Connection.ACCEPTED:
            return _respond(request, False, "You are already connected.", "connected")
        if existing.status == Connection.PENDING and existing.requester_id == me.pk:
            return _respond(request, False, "Request already sent.", "sent")  # no duplicates
        if existing.status == Connection.PENDING:  # they already asked me → accept
            existing.status = Connection.ACCEPTED
            existing.save()
            notify(other, "connection_accepted", f"{me.full_name} accepted your request",
                   "You can now message each other.", f"/students/{me.pk}/", actor=me)
            return _respond(request, True, f"You are now connected with {other.first_name_display}! 🎉", "connected")
        # previously declined → re-open the same row (unique pair)
        existing.requester, existing.receiver, existing.status = me, other, Connection.PENDING
        existing.save()
    else:
        Connection.objects.create(requester=me, receiver=other)
    notify(other, "connection_request", f"{me.full_name} wants to connect",
           f"{me.course} · {me.university}", "/connections/?tab=received", actor=me)
    return _respond(request, True, f"Request sent to {other.first_name_display}.", "sent")


@member_required
@require_POST
def respond_request(request, pk, action):
    if action not in ("accept", "decline"):
        raise Http404
    conn = get_object_or_404(Connection, pk=pk, receiver=request.user, status=Connection.PENDING)
    if action == "accept":
        conn.status = Connection.ACCEPTED
        conn.save()
        notify(conn.requester, "connection_accepted", f"{request.user.full_name} accepted your request",
               "Say hi 👋", f"/students/{request.user.pk}/", actor=request.user)
        return _respond(request, True, f"You are now connected with {conn.requester.first_name_display}! 🎉",
                        "connected")
    conn.status = Connection.DECLINED
    conn.save()
    return _respond(request, True, "Request declined.", "none")


@member_required
@require_POST
def cancel_request(request, pk):
    conn = get_object_or_404(Connection, pk=pk, requester=request.user, status=Connection.PENDING)
    conn.delete()
    return _respond(request, True, "Request cancelled.", "none")


@member_required
@require_POST
def remove_connection(request, pk):
    other = get_object_or_404(User, pk=pk)
    conn = request.user.connection_with(other)
    if conn and conn.status == Connection.ACCEPTED:
        conn.delete()
        return _respond(request, True, f"{other.full_name} was removed from your connections.", "none")
    return _respond(request, False, "You are not connected.", status=400)


@member_required
@require_POST
def block_user(request, pk):
    other = get_object_or_404(User, pk=pk)
    if other == request.user:
        return _respond(request, False, "You cannot block yourself.", status=400)
    Block.objects.get_or_create(blocker=request.user, blocked=other)
    Connection.objects.filter(Q(requester=request.user, receiver=other) | Q(requester=other, receiver=request.user)).delete()
    return _respond(request, True, f"{other.full_name} has been blocked.", "blocked")


@member_required
@require_POST
def unblock_user(request, pk):
    Block.objects.filter(blocker=request.user, blocked_id=pk).delete()
    return _respond(request, True, "User unblocked.", "none")
