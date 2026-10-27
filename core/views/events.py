"""Events: upcoming / mine / past, details, register / cancel, create."""
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import EventForm
from ..models import Event, Notification
from ..utils import is_ajax, member_required, notify, safe_next


def create_event_reminders(user):
    """Event reminder notifications for events starting in the next 24 hours."""
    now = timezone.now()
    for event in user.events.filter(starts_at__gt=now, starts_at__lte=now + timedelta(hours=24)):
        link = event.get_absolute_url()
        if not Notification.objects.filter(user=user, type="event_reminder", link=link).exists():
            when = timezone.localtime(event.starts_at).strftime("%a %d %b at %H:%M")
            notify(user, "event_reminder", f"Reminder: {event.title} is coming up", f"{when} · {event.location}", link)


@member_required
def event_list(request):
    user = request.user
    tab = request.GET.get("tab", "upcoming")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    now = timezone.now()
    qs = Event.objects.select_related("organizer", "community").annotate(going=Count("participants", distinct=True))
    if tab == "mine":
        qs = qs.filter(Q(participants=user) | Q(organizer=user)).distinct().filter(starts_at__gte=now)
    elif tab == "past":
        qs = qs.filter(starts_at__lt=now).order_by("-starts_at")
    else:
        qs = qs.filter(starts_at__gte=now)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))
    if category:
        qs = qs.filter(category=category)
    if tab != "past":
        qs = qs.order_by("starts_at")
    events = list(qs)
    featured = events[0] if events and tab == "upcoming" and not (q or category) else None
    return render(request, "events/list.html", {
        "events": events[1:] if featured else events, "featured": featured,
        "tab": tab, "q": q, "category": category, "categories": Event.CATEGORY_CHOICES,
        "my_ids": set(user.events.values_list("pk", flat=True)),
    })


@member_required
def event_detail(request, pk):
    event = get_object_or_404(Event.objects.select_related("organizer", "community"), pk=pk)
    hidden = request.user.blocked_ids()
    participants = event.participants.exclude(pk__in=hidden)
    connections = request.user.connection_ids()
    return render(request, "events/detail.html", {
        "event": event,
        "is_registered": event.participants.filter(pk=request.user.pk).exists(),
        "participants": participants[:12],
        "participant_total": event.participants.count(),
        "friends_going": participants.filter(pk__in=connections)[:5],
    })


@member_required
@require_POST
def toggle_registration(request, pk):
    event = get_object_or_404(Event, pk=pk)
    user = request.user
    if event.participants.filter(pk=user.pk).exists():
        event.participants.remove(user)
        registered, ok, text = False, True, "Your registration was cancelled."
    elif event.is_past:
        registered, ok, text = False, False, "This event has already taken place."
    elif event.is_full:
        registered, ok, text = False, False, "Sorry, this event is full."
    else:
        event.participants.add(user)
        registered, ok, text = True, True, f"You're going to {event.title}! 🎟️"
        if event.organizer and event.organizer != user:
            notify(event.organizer, "event", f"{user.full_name} registered for {event.title}", "",
                   event.get_absolute_url(), actor=user)
    if is_ajax(request):
        return JsonResponse({"ok": ok, "registered": registered, "count": event.participants.count(),
                             "message": text}, status=200 if ok else 400)
    (messages.success if ok else messages.error)(request, text)
    return safe_next(request, event.get_absolute_url())


@member_required
def create_event(request):
    form = EventForm(request.POST or None, request.FILES or None, user=request.user,
                     initial={"community": request.GET.get("community")})
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.organizer = request.user
        event.save()
        event.participants.add(request.user)
        if event.community:  # tell community members about the new event
            for member in event.community.members.exclude(pk=request.user.pk)[:200]:
                notify(member, "event", f"New event in {event.community.name}", event.title,
                       event.get_absolute_url(), actor=request.user)
        messages.success(request, "Your event has been published! 📅")
        return redirect(event.get_absolute_url())
    return render(request, "events/form.html", {"form": form})
