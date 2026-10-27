"""
Simple rule-based recommendations (spec §15: start with scoring rules, ML later).

Score of a candidate student for the current user:
    +2 per shared interest, +3 same university, +2 same course,
    +1 same year, +1 same home country, +1 same country of study.
"""
from django.db.models import Count, Q
from django.utils import timezone

from .models import Community, Connection, Event, User


def _excluded_ids(user):
    """Me, my blocked users, people I'm connected to or with a pending request."""
    ids = {user.pk} | user.blocked_ids()
    rows = Connection.objects.filter(Q(requester=user) | Q(receiver=user)).exclude(status=Connection.DECLINED)
    for a, b in rows.values_list("requester_id", "receiver_id"):
        ids.update((a, b))
    return ids


def score_student(user, candidate, my_interest_ids):
    reasons = []
    shared = my_interest_ids & {i.pk for i in candidate.interests.all()}
    score = 2 * len(shared)
    if shared:
        reasons.append(f"{len(shared)} shared interest{'s' if len(shared) > 1 else ''}")
    if user.university and candidate.university == user.university:
        score += 3
        reasons.append("Same university")
    if user.course and candidate.course == user.course:
        score += 2
        reasons.append("Same course")
    if user.year and candidate.year == user.year:
        score += 1
    if user.country and candidate.country == user.country:
        score += 1
        reasons.append(f"Also from {candidate.country}")
    if user.destination_country and candidate.destination_country == user.destination_country:
        score += 1
    return score, reasons


def suggested_students(user, limit=6):
    my_interests = set(user.interests.values_list("pk", flat=True))
    candidates = (User.objects.filter(is_active=True, profile_completed=True, is_staff=False)
                  .exclude(pk__in=_excluded_ids(user))
                  .exclude(profile_visibility="private")
                  .prefetch_related("interests")[:300])
    ranked = []
    for c in candidates:
        score, reasons = score_student(user, c, my_interests)
        c.match_reasons = reasons[:2]
        c.match_score = score
        ranked.append(c)
    ranked.sort(key=lambda c: (-c.match_score, c.full_name))
    return ranked[:limit]


def suggested_communities(user, limit=4):
    my_interests = user.interests.all()
    return (Community.objects.exclude(members=user)
            .annotate(match=Count("interests", filter=Q(interests__in=my_interests), distinct=True),
                      member_total=Count("members", distinct=True))
            .order_by("-match", "-member_total")[:limit])


def upcoming_events(user, limit=3):
    return (Event.objects.filter(starts_at__gte=timezone.now())
            .annotate(going=Count("participants", distinct=True))
            .order_by("starts_at")[:limit])
