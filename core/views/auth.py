"""Splash / onboarding, sign up, sign in, forgot / reset password, logout."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_http_methods

from ..forms import ForgotPasswordForm, ResetPasswordForm, SignInForm, SignUpForm
from ..models import User
from ..utils import notify, rate_limited


def _next_step(user):
    if not user.profile_completed:
        return redirect("complete_profile")
    return redirect("home")


def landing(request):
    """Splash screen + 3 onboarding slides."""
    if request.user.is_authenticated:
        return _next_step(request.user)
    return render(request, "auth/onboarding.html")


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return _next_step(request.user)
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            full_name=form.cleaned_data["full_name"].strip(),
        )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Welcome to Connectera, {user.first_name_display}! Let's set up your profile.")
        return redirect("complete_profile")
    return render(request, "auth/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def signin(request):
    if request.user.is_authenticated:
        return _next_step(request.user)
    form = SignInForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if rate_limited(request, "login", limit=8, window=600, key_extra=email):
            messages.error(request, "Too many attempts. Please wait a few minutes and try again.")
            return render(request, "auth/login.html", {"form": form}, status=429)
        user = authenticate(request, username=email, password=form.cleaned_data["password"])
        if user is None:
            messages.error(request, "Incorrect e-mail or password.")
        else:
            login(request, user)
            if not form.cleaned_data.get("remember"):
                request.session.set_expiry(0)  # expires when the browser closes
            messages.success(request, f"Welcome back, {user.first_name_display}! 👋")
            nxt = request.GET.get("next")
            if nxt and nxt.startswith("/") and not nxt.startswith("//") and user.profile_completed:
                return redirect(nxt)
            return _next_step(user)
    return render(request, "auth/login.html", {"form": form})


@require_http_methods(["GET", "POST"])
def forgot_password(request):
    """Sends a secure, single-use reset link (valid 1 hour) by e-mail."""
    form = ForgotPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].lower()
        if rate_limited(request, "forgot", limit=5, window=900, key_extra=email):
            messages.error(request, "Too many requests. Please try again later.")
            return redirect("forgot_password")
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = request.build_absolute_uri(reverse("reset_password", args=[uid, token]))
            send_mail(
                "Reset your Connectera password",
                f"Hi {user.first_name_display},\n\nClick the link below to choose a new password "
                f"(valid for 1 hour):\n{link}\n\nIf you did not request it, simply ignore this e-mail.\n\n"
                "— The Connectera team",
                settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True,
            )
        # Same message whether the account exists or not (no account enumeration).
        return render(request, "auth/forgot_password.html", {"form": ForgotPasswordForm(), "sent_to": email})
    return render(request, "auth/forgot_password.html", {"form": form})


@require_http_methods(["GET", "POST"])
def reset_password(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        messages.error(request, "This reset link is invalid or has expired. Please request a new one.")
        return redirect("forgot_password")
    form = ResetPasswordForm(request.POST or None, user=user)
    if request.method == "POST" and form.is_valid():
        user.set_password(form.cleaned_data["password"])
        user.save()  # changing the password invalidates the link
        notify(user, "system", "Your password was changed",
               "If this wasn't you, contact support immediately.", "/settings/account/")
        messages.success(request, "Password updated. You can now sign in. 🔐")
        return redirect("login")
    return render(request, "auth/reset_password.html", {"form": form, "email": user.email})


@login_required
def logout_view(request):
    """GET: confirmation screen — POST: actually log out."""
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been logged out. See you soon!")
        return redirect("login")
    return render(request, "auth/logout.html")
