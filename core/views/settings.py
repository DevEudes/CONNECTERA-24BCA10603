"""Settings: account, password, privacy, notifications, appearance, help, blocked users, deactivate / delete."""
from django.conf import settings as conf
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.mail import mail_admins
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..forms import AccountForm, AppearanceForm, NotificationPrefsForm, PrivacyForm, SupportForm
from ..models import User
from ..utils import member_required, notify

FAQ = [
    ("How do I connect with another student?",
     "Open their profile or find them in Search, then tap “Connect”. They will receive a request and you will be "
     "notified when they accept."),
    ("Who can see my profile?",
     "You decide! Go to Settings → Privacy & Security and choose Everyone, My connections only, or Only me."),
    ("Can I message someone I'm not connected with?",
     "Yes, unless they restricted messages to their connections in their privacy settings."),
    ("How do I join a community or an event?",
     "Browse Communities or Events, open one and tap “Join” or “Register”. You can leave or cancel at any time."),
    ("Someone is bothering me. What can I do?",
     "Open their profile, tap the ••• menu and choose Block or Report. Blocked users can't see you or message you."),
    ("I forgot my password.",
     "On the Sign in screen tap “Forgot password?”. We'll e-mail you a 6-digit code to choose a new one."),
]


@member_required
def settings_index(request):
    return render(request, "settings/index.html")


@member_required
def account(request):
    user = request.user
    form = AccountForm(instance=user)
    pwd_form = PasswordChangeForm(user)
    if request.method == "POST":
        if "change_password" in request.POST:
            pwd_form = PasswordChangeForm(user, request.POST)
            if pwd_form.is_valid():
                pwd_form.save()
                update_session_auth_hash(request, pwd_form.user)  # stay logged in
                messages.success(request, "Password changed 🔐")
                return redirect("settings_account")
        else:
            form = AccountForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, "Account updated.")
                return redirect("settings_account")
    return render(request, "settings/account.html", {"form": form, "pwd_form": pwd_form})


def _simple_settings_page(request, form_class, template, success):
    form = form_class(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, success)
        return redirect(request.path)
    return render(request, template, {"form": form})


@member_required
def privacy(request):
    return _simple_settings_page(request, PrivacyForm, "settings/privacy.html", "Privacy settings saved 🛡️")


@member_required
def notification_prefs(request):
    return _simple_settings_page(request, NotificationPrefsForm, "settings/notifications.html",
                                 "Notification preferences saved.")


@member_required
def appearance(request):
    return _simple_settings_page(request, AppearanceForm, "settings/appearance.html", "Appearance updated ✨")


@member_required
def blocked_users(request):
    return render(request, "settings/blocked.html",
                  {"blocked": User.objects.filter(blocked_by__blocker=request.user)})


@member_required
def help_support(request):
    form = SupportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        topic = dict(SupportForm.TOPICS)[form.cleaned_data["topic"]]
        mail_admins(f"[Support] {topic} — {request.user.email}", form.cleaned_data["message"], fail_silently=True)
        notify(request.user, "system", "We received your message 💜",
               f"Topic: {topic}. Our team will get back to you by e-mail.", "/settings/help/")
        messages.success(request, "Message sent! We'll get back to you soon.")
        return redirect("settings_help")
    return render(request, "settings/help.html", {"form": form, "faq": FAQ,
                                                   "support_email": conf.DEFAULT_FROM_EMAIL})


@member_required
@require_POST
def deactivate_account(request):
    user = request.user
    if not user.check_password(request.POST.get("password", "")):
        messages.error(request, "Incorrect password.")
        return redirect("settings_privacy")
    if request.POST.get("action") == "delete":
        logout(request)
        user.delete()
        messages.success(request, "Your account and data have been deleted. Goodbye 👋")
    else:
        user.is_active = False
        user.save(update_fields=["is_active"])
        logout(request)
        messages.success(request, "Your account is deactivated. Contact support to reactivate it.")
    return redirect("login")
