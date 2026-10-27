"""Communities: discover, search, join / leave, details, create."""
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from ..forms import CommentForm, CommunityForm
from ..models import Community
from ..recommendations import suggested_communities
from ..utils import is_ajax, member_required, notify, safe_next
from .feed import posts_queryset


@member_required
def community_list(request):
    user = request.user
    tab = request.GET.get("tab", "discover")
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    qs = Community.objects.annotate(member_total=Count("members", distinct=True))
    if tab == "mine":
        qs = qs.filter(members=user)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(tagline__icontains=q))
    if category:
        qs = qs.filter(category=category)
    my_ids = set(user.communities.values_list("pk", flat=True))
    return render(request, "communities/list.html", {
        "communities": qs.order_by("-member_total", "name"),
        "recommended": [] if (q or category or tab == "mine") else suggested_communities(user, limit=3),
        "tab": tab, "q": q, "category": category, "categories": Community.CATEGORY_CHOICES, "my_ids": my_ids,
    })


@member_required
def community_detail(request, slug):
    community = get_object_or_404(Community, slug=slug)
    is_member = community.members.filter(pk=request.user.pk).exists()
    hidden = request.user.blocked_ids()
    return render(request, "communities/detail.html", {
        "community": community,
        "is_member": is_member,
        "posts": posts_queryset(request.user).filter(community=community)[:20],
        "members": community.members.exclude(pk__in=hidden).order_by("-last_seen")[:12],
        "member_total": community.members.count(),
        "events": community.events.filter(starts_at__gte=timezone.now()).order_by("starts_at")[:4],
        "comment_form": CommentForm(),
    })


@member_required
@require_POST
def toggle_membership(request, slug):
    community = get_object_or_404(Community, slug=slug)
    if community.members.filter(pk=request.user.pk).exists():
        community.members.remove(request.user)
        joined, text = False, f"You left {community.name}."
    else:
        community.members.add(request.user)
        joined, text = True, f"Welcome to {community.name}! 🎉"
        if community.creator and community.creator != request.user:
            notify(community.creator, "community", f"{request.user.full_name} joined {community.name}",
                   "", community.get_absolute_url(), actor=request.user)
    if is_ajax(request):
        return JsonResponse({"joined": joined, "count": community.members.count(), "message": text})
    messages.success(request, text)
    return safe_next(request, community.get_absolute_url())


@member_required
def create_community(request):
    form = CommunityForm(request.POST or None, request.FILES or None, initial={"icon": "👥"})
    if request.method == "POST" and form.is_valid():
        community = form.save(commit=False)
        community.creator = request.user
        community.save()
        form.save_m2m()
        community.members.add(request.user)
        # let students who share the community's interests know about it
        interested = (type(request.user).objects.filter(interests__in=community.interests.all(), is_active=True)
                      .exclude(pk=request.user.pk).distinct()[:50])
        for u in interested:
            notify(u, "community", f"New community: {community.name}", community.tagline,
                   community.get_absolute_url(), actor=request.user)
        messages.success(request, f"{community.name} has been created! 🚀")
        return redirect(community.get_absolute_url())
    return render(request, "communities/form.html", {"form": form})
