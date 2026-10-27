"""Complete profile → interests → success, my profile, student profile, edit profile."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import InterestsForm, ProfileForm
from ..models import Connection, Interest, User
from ..recommendations import suggested_students
from ..utils import member_required
from .feed import posts_queryset

UNIVERSITIES = ["Chandigarh University", "Panjab University", "Lovely Professional University", "Amity University",
                "Delhi University", "IIT Delhi", "IIT Bombay", "Manipal University", "Christ University",
                "VIT Vellore", "Sharda University", "Galgotias University", "University of Buea",
                "University of Lagos", "University of Nairobi"]
COURSES = ["BCA", "MCA", "B.Tech CSE", "B.Tech AI & ML", "BBA", "MBA", "B.Com", "B.Sc Data Science", "B.Pharm",
           "B.Arch", "BA Journalism", "B.Des Fashion", "LLB", "MBBS", "B.Sc Biotechnology", "Hotel Management"]


def _form_context(form, **extra):
    return {"form": form, "universities": UNIVERSITIES, "courses": COURSES, **extra}


@login_required
def complete_profile(request):
    user = request.user
    form = ProfileForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("select_interests")
    return render(request, "onboarding/complete_profile.html", _form_context(form, step=1))


@login_required
def select_interests(request):
    user = request.user
    if not (user.university and user.course):
        return redirect("complete_profile")
    form = InterestsForm(request.POST or None, initial={"interests": user.interests.all()})
    if request.method == "POST" and form.is_valid():
        user.interests.set(form.cleaned_data["interests"])
        first_time = not user.profile_completed
        user.profile_completed = True
        user.save(update_fields=["profile_completed"])
        if first_time:
            return redirect("profile_done")
        messages.success(request, "Your interests have been updated.")
        return redirect("my_profile")
    selected = set(user.interests.values_list("pk", flat=True))
    if request.method == "POST":
        selected = {int(x) for x in request.POST.getlist("interests") if x.isdigit()}
    return render(request, "onboarding/interests.html", {
        "form": form, "interests": Interest.objects.all(), "selected": selected,
        "step": 2, "editing": user.profile_completed,
    })


@login_required
def profile_done(request):
    if not request.user.profile_completed:
        return redirect("complete_profile")
    suggestions = suggested_students(request.user, limit=4)
    return render(request, "onboarding/done.html", {"suggestions": suggestions})


def _profile_context(viewer, profile):
    can_view = profile.can_view_profile(viewer)
    connection = viewer.connection_with(profile) if viewer != profile else None
    my_ids = viewer.connection_ids()
    their_ids = profile.connection_ids()
    mutual = User.objects.filter(pk__in=(my_ids & their_ids))
    ctx = {
        "profile": profile,
        "can_view": can_view,
        "connection": connection,
        "is_me": viewer == profile,
        "i_blocked": viewer != profile and viewer.has_blocked(profile),
        "connection_count": len(their_ids),
        "mutual": mutual[:6],
        "mutual_count": mutual.count(),
        "shared_interests": set(profile.interests.values_list("pk", flat=True))
        & set(viewer.interests.values_list("pk", flat=True)),
    }
    if can_view:
        ctx["posts"] = posts_queryset(viewer).filter(author=profile)[:20]
        ctx["communities"] = profile.communities.all()[:6]
        ctx["post_count"] = profile.posts.count()
        ctx["upcoming_events"] = profile.events.order_by("starts_at")[:3]
    return ctx


@member_required
def my_profile(request):
    return render(request, "profile/profile.html", _profile_context(request.user, request.user))


@member_required
def profile_detail(request, pk):
    profile = get_object_or_404(User, pk=pk, is_active=True, profile_completed=True)
    if profile == request.user:
        return redirect("my_profile")
    # If this student blocked me, their profile does not exist for me.
    # (I can still open the profile of someone *I* blocked, in order to unblock them.)
    if profile.has_blocked(request.user):
        raise Http404
    return render(request, "profile/profile.html", _profile_context(request.user, profile))


@member_required
def edit_profile(request):
    user = request.user
    form = ProfileForm(request.POST or None, request.FILES or None, instance=user)
    if request.method == "POST":
        if request.POST.get("remove_avatar"):
            user.avatar.delete(save=True)
            messages.success(request, "Profile photo removed.")
            return redirect("edit_profile")
        if form.is_valid():
            form.save()
            messages.success(request, "Profile saved ✨")
            return redirect("my_profile")
        messages.error(request, "Please fix the errors below.")
    return render(request, "profile/edit.html", _form_context(form))


@member_required
def connections_of(request, pk):
    """Public list of someone's connections (respects privacy)."""
    profile = get_object_or_404(User, pk=pk, is_active=True)
    if not profile.can_view_profile(request.user):
        raise Http404
    blocked = request.user.blocked_ids()
    people = profile.connections().exclude(pk__in=blocked)
    return render(request, "network/connections_of.html", {"profile": profile, "people": people,
                                                           "pending_ids": _pending_ids(request.user)})


def _pending_ids(user):
    return set(Connection.objects.filter(requester=user, status=Connection.PENDING)
               .values_list("receiver_id", flat=True))
