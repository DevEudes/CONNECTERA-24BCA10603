"""Home feed, posts, likes, comments and reports."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from ..forms import CommentForm, PostForm, ReportForm
from ..models import Comment, Community, Post, Report, User
from ..recommendations import suggested_communities, suggested_students, upcoming_events
from ..utils import is_ajax, member_required, notify, safe_next

PAGE_SIZE = 8


def posts_queryset(viewer):
    """Posts the viewer is allowed to see, with counters pre-computed."""
    hidden = viewer.blocked_ids()
    my_connections = viewer.connection_ids()
    liked = Post.likes.through.objects.filter(post_id=OuterRef("pk"), user_id=viewer.pk)
    return (
        Post.objects.filter(author__is_active=True)
        .exclude(author_id__in=hidden)
        # respect the author's profile visibility
        .filter(Q(author=viewer) | Q(author__profile_visibility="public")
                | Q(author__profile_visibility="connections", author_id__in=my_connections))
        .select_related("author", "community")
        .annotate(like_count=Count("likes", distinct=True), comment_count=Count("comments", distinct=True),
                  liked=Exists(liked))
        .prefetch_related(Prefetch("comments", queryset=Comment.objects.select_related("author")
                                   .exclude(author_id__in=hidden)))
        .order_by("-created_at")
    )


@member_required
def home(request):
    user = request.user
    tab = request.GET.get("tab", "for-you")
    posts = posts_queryset(user)
    if tab == "network":
        posts = posts.filter(Q(author_id__in=user.connection_ids() | {user.pk}))
    page = Paginator(posts, PAGE_SIZE).get_page(request.GET.get("page"))

    if is_ajax(request):  # progressive loading ("Load more")
        html = render_to_string("feed/_post_list.html", {"posts": page, "request": request, "user": user},
                                request=request)
        return JsonResponse({"html": html, "has_next": page.has_next(),
                             "next": page.next_page_number() if page.has_next() else None})

    stories = User.objects.filter(pk__in=user.connection_ids(), is_active=True).order_by("-last_seen")[:12]
    return render(request, "feed/home.html", {
        "posts": page,
        "tab": tab,
        "form": PostForm(user=user),
        "stories": stories,
        "suggestions": suggested_students(user, limit=4),
        "communities": suggested_communities(user, limit=3),
        "events": upcoming_events(user, limit=3),
    })


@member_required
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, "Your post is live! 🎉")
            if post.community:
                return redirect(post.community.get_absolute_url())
            return redirect("home")
        messages.error(request, " ".join(form.non_field_errors()) or "Please check your post.")
    initial_community = request.GET.get("community")
    if initial_community and request.method == "GET":
        form = PostForm(user=request.user, initial={"community": initial_community})
    return render(request, "feed/create_post.html", {"form": form})


@member_required
def post_detail(request, pk):
    post = get_object_or_404(posts_queryset(request.user), pk=pk)
    return render(request, "feed/post_detail.html", {"post": post, "comment_form": CommentForm(), "expanded": True})


@member_required
@require_POST
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author != request.user and not request.user.is_staff:
        raise Http404
    post.delete()
    messages.success(request, "Post deleted.")
    return safe_next(request, "home")


@member_required
@require_POST
def toggle_like(request, pk):
    post = get_object_or_404(posts_queryset(request.user), pk=pk)
    if post.likes.filter(pk=request.user.pk).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        notify(post.author, "like", f"{request.user.full_name} liked your post",
               post.text[:80], f"/posts/{post.pk}/", actor=request.user)
    if is_ajax(request):
        return JsonResponse({"liked": liked, "count": post.likes.count()})
    return safe_next(request, "home")


@member_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(posts_queryset(request.user), pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid() and form.cleaned_data["text"].strip():
        comment = form.save(commit=False)
        comment.post, comment.author = post, request.user
        comment.save()
        notify(post.author, "comment", f"{request.user.full_name} commented on your post",
               comment.text[:120], f"/posts/{post.pk}/", actor=request.user)
        if is_ajax(request):
            html = render_to_string("feed/_comment.html", {"c": comment, "user": request.user}, request=request)
            return JsonResponse({"html": html, "count": post.comments.count()})
    elif is_ajax(request):
        return JsonResponse({"error": "Comment cannot be empty."}, status=400)
    return safe_next(request, f"/posts/{post.pk}/")


@member_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user not in (comment.author, comment.post.author) and not request.user.is_staff:
        raise Http404
    post_pk = comment.post_id
    comment.delete()
    messages.success(request, "Comment deleted.")
    return safe_next(request, f"/posts/{post_pk}/")


TARGETS = {"user": User, "post": Post, "comment": Comment, "community": Community}


@member_required
def report(request, target_type, target_id):
    model = TARGETS.get(target_type)
    if model is None:
        raise Http404
    target = get_object_or_404(model, pk=target_id)
    form = ReportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if Report.objects.filter(reporter=request.user, target_type=target_type, target_id=target_id,
                                 status="open").exists():
            messages.info(request, "You already reported this. Our team is reviewing it.")
        else:
            r = form.save(commit=False)
            r.reporter, r.target_type, r.target_id = request.user, target_type, target_id
            r.save()
            messages.success(request, "Thanks for keeping Connectera safe. Our moderators will review it. 🛡️")
        return safe_next(request, "home")
    return render(request, "feed/report.html", {"form": form, "target": target, "target_type": target_type,
                                                "next": request.GET.get("next", "/")})
