from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from .models import Comment, Community, Event, Interest, Post, Report, User

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def validate_image(file):
    """Uploads: check type and size (spec §11)."""
    if not file:
        return file
    if file.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Image too large (max {settings.MAX_UPLOAD_SIZE_MB} MB).")
    content_type = getattr(file, "content_type", None)
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError("Unsupported format. Use JPG, PNG, WEBP or GIF.")
    return file


COUNTRIES = [
    "India", "Cameroon", "Nigeria", "Kenya", "Ghana", "Senegal", "Ivory Coast", "DR Congo", "Gabon",
    "Morocco", "Egypt", "South Africa", "Ethiopia", "Rwanda", "Uganda", "Tanzania", "Zimbabwe",
    "France", "Germany", "United Kingdom", "Spain", "Italy", "Canada", "United States", "Brazil",
    "Nepal", "Bangladesh", "Sri Lanka", "Afghanistan", "Bhutan", "Vietnam", "Thailand", "Indonesia",
    "Malaysia", "Japan", "South Korea", "China", "UAE", "Saudi Arabia", "Iran", "Iraq", "Australia",
]
COUNTRY_CHOICES = [("", "Select a country")] + [(c, c) for c in sorted(COUNTRIES)]


# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
class SignUpForm(forms.Form):
    full_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={"placeholder": "Your full name",
                                                                             "autocomplete": "name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@university.edu",
                                                            "autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "At least 8 characters",
                                                                 "autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password",
                                widget=forms.PasswordInput(attrs={"placeholder": "Repeat your password",
                                                                  "autocomplete": "new-password"}))
    terms = forms.BooleanField(label="I agree to the Terms & Privacy Policy",
                               error_messages={"required": "Please accept the terms to continue."})

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this e-mail already exists. Try signing in.")
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        if p1:
            try:
                password_validation.validate_password(p1, User(email=data.get("email", ""),
                                                               full_name=data.get("full_name", "")))
            except ValidationError as e:
                self.add_error("password", e)
        return data


class SignInForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@university.edu",
                                                            "autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder": "Your password",
                                                                 "autocomplete": "current-password"}))
    remember = forms.BooleanField(required=False, initial=True, label="Remember me")


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@university.edu"}))


class ResetPasswordForm(forms.Form):
    password = forms.CharField(label="New password", widget=forms.PasswordInput(attrs={"placeholder": "New password"}))
    password2 = forms.CharField(label="Confirm password",
                                widget=forms.PasswordInput(attrs={"placeholder": "Repeat new password"}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if data.get("password") and data.get("password") != data.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        elif data.get("password"):
            try:
                password_validation.validate_password(data["password"], self.user)
            except ValidationError as e:
                self.add_error("password", e)
        return data


# --------------------------------------------------------------------------
# Profile
# --------------------------------------------------------------------------
class ProfileForm(forms.ModelForm):
    country = forms.ChoiceField(choices=COUNTRY_CHOICES, label="Current country")
    destination_country = forms.ChoiceField(choices=COUNTRY_CHOICES, label="Country of study")
    avatar = forms.ImageField(required=False, validators=[validate_image])
    cover = forms.ImageField(required=False, validators=[validate_image])

    class Meta:
        model = User
        fields = ["avatar", "cover", "full_name", "headline", "country", "destination_country", "university",
                  "course", "year", "bio"]
        widgets = {
            "full_name": forms.TextInput(attrs={"placeholder": "Your full name"}),
            "headline": forms.TextInput(attrs={"placeholder": "e.g. Aspiring software engineer ✨"}),
            "university": forms.TextInput(attrs={"placeholder": "e.g. Chandigarh University", "list": "universities"}),
            "course": forms.TextInput(attrs={"placeholder": "e.g. BCA", "list": "courses"}),
            "bio": forms.Textarea(attrs={"rows": 4, "placeholder": "Tell other students about yourself…"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ["country", "destination_country", "university", "course", "year"]:
            self.fields[name].required = True
        self.fields["year"].choices = [("", "Select your year")] + list(User.YEAR_CHOICES)


class InterestsForm(forms.Form):
    interests = forms.ModelMultipleChoiceField(
        queryset=Interest.objects.all(), widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Pick at least 3 interests."},
    )

    def clean_interests(self):
        chosen = self.cleaned_data["interests"]
        if len(chosen) < 3:
            raise ValidationError("Pick at least 3 interests so we can find your people.")
        return chosen


# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------
class PostForm(forms.ModelForm):
    image = forms.ImageField(required=False, validators=[validate_image])

    class Meta:
        model = Post
        fields = ["text", "image", "community"]
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Share something with your campus…"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["community"].required = False
        self.fields["community"].empty_label = "Public feed"
        if user is not None:
            self.fields["community"].queryset = user.communities.all()

    def clean(self):
        data = super().clean()
        if not (data.get("text") or "").strip() and not data.get("image"):
            raise ValidationError("Write something or add a photo.")
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {"text": forms.TextInput(attrs={"placeholder": "Write a comment…", "autocomplete": "off"})}


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["reason", "details"]
        widgets = {"details": forms.Textarea(attrs={"rows": 3, "placeholder": "Anything else we should know? (optional)"})}


class CommunityForm(forms.ModelForm):
    image = forms.ImageField(required=False, validators=[validate_image], label="Cover image")

    class Meta:
        model = Community
        fields = ["name", "icon", "tagline", "category", "description", "image", "interests"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "interests": forms.CheckboxSelectMultiple,
            "icon": forms.TextInput(attrs={"maxlength": 4}),
        }


class EventForm(forms.ModelForm):
    image = forms.ImageField(required=False, validators=[validate_image], label="Cover image")

    class Meta:
        model = Event
        fields = ["title", "category", "description", "image", "starts_at", "ends_at", "location", "is_online",
                  "capacity", "community"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["community"].required = False
        if user is not None:
            self.fields["community"].queryset = user.communities.all()

    def clean(self):
        data = super().clean()
        if data.get("starts_at") and data.get("ends_at") and data["ends_at"] <= data["starts_at"]:
            self.add_error("ends_at", "The end must be after the start.")
        return data


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------
class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This e-mail is already used by another account.")
        return email


class PrivacyForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["profile_visibility", "allow_messages_from", "show_email"]
        widgets = {"profile_visibility": forms.RadioSelect, "allow_messages_from": forms.RadioSelect}


class NotificationPrefsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["notify_connections", "notify_messages", "notify_posts", "notify_events"]
        labels = {
            "notify_connections": "Connection requests & acceptances",
            "notify_messages": "New messages",
            "notify_posts": "Likes & comments on my posts",
            "notify_events": "Communities, events & reminders",
        }


class AppearanceForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["theme", "language"]
        widgets = {"theme": forms.RadioSelect}


class SupportForm(forms.Form):
    TOPICS = [("account", "Account & login"), ("bug", "Report a bug"), ("safety", "Safety concern"),
              ("idea", "Suggest a feature"), ("other", "Other")]
    topic = forms.ChoiceField(choices=TOPICS)
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4, "placeholder": "How can we help?"}),
                              max_length=2000)
