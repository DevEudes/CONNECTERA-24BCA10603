"""
Connectera data model (see section 9 of the specification).

User, Interest, Connection, Block, Post, Comment, Conversation,
Message, Community, Event, Notification, Report.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------
class UserManager(BaseUserManager):
    """Users log in with their e-mail address (no username)."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("An e-mail address is required.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True, profile_completed=True)
        extra.setdefault("full_name", "Administrator")
        return self._create_user(email, password, **extra)


class Interest(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=10, default="✨", help_text="An emoji")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.icon} {self.name}"


class User(AbstractUser):
    YEAR_CHOICES = [(1, "1st year"), (2, "2nd year"), (3, "3rd year"), (4, "4th year"), (5, "5th year"),
                    (6, "Master's"), (7, "PhD")]
    VISIBILITY_CHOICES = [("public", "Everyone"), ("connections", "My connections only"), ("private", "Only me")]
    MESSAGE_CHOICES = [("everyone", "Everyone"), ("connections", "My connections only")]
    THEME_CHOICES = [("light", "Light"), ("dark", "Dark")]
    LANGUAGE_CHOICES = [("en", "English"), ("fr", "Français"), ("hi", "हिन्दी")]

    username = None
    email = models.EmailField("e-mail address", unique=True)
    full_name = models.CharField(max_length=120)
    avatar = models.ImageField(upload_to="avatars/", blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True)
    headline = models.CharField(max_length=120, blank=True, help_text="Short tagline, e.g. 'Future data scientist'")
    country = models.CharField("current country", max_length=80, blank=True)
    destination_country = models.CharField("country of study", max_length=80, blank=True)
    university = models.CharField(max_length=150, blank=True)
    course = models.CharField(max_length=120, blank=True)
    year = models.PositiveSmallIntegerField(choices=YEAR_CHOICES, null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    interests = models.ManyToManyField(Interest, blank=True, related_name="users")

    # account state
    profile_completed = models.BooleanField(default=False)

    # privacy settings
    profile_visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default="public")
    allow_messages_from = models.CharField(max_length=20, choices=MESSAGE_CHOICES, default="everyone")
    show_email = models.BooleanField(default=False)

    # notification preferences
    notify_connections = models.BooleanField(default=True)
    notify_messages = models.BooleanField(default=True)
    notify_posts = models.BooleanField(default=True)
    notify_events = models.BooleanField(default=True)

    # appearance
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default="light")
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")

    last_seen = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name or self.email

    def get_absolute_url(self):
        return reverse("profile_detail", args=[self.pk])

    # ---- display helpers ----
    @property
    def first_name_display(self):
        return (self.full_name or self.email).split()[0]

    @property
    def initials(self):
        parts = (self.full_name or self.email).split()
        return "".join(p[0] for p in parts[:2]).upper()

    @property
    def avatar_color(self):
        palette = ["#7C3AED", "#A855F7", "#EC4899", "#6366F1", "#0EA5E9", "#14B8A6", "#F59E0B", "#EF4444"]
        return palette[(self.pk or 0) % len(palette)]

    @property
    def is_online(self):
        return bool(self.last_seen and timezone.now() - self.last_seen < timedelta(minutes=5))

    @property
    def year_label(self):
        return self.get_year_display() if self.year else ""

    @property
    def profile_strength(self):
        fields = [self.avatar, self.headline, self.country, self.destination_country, self.university,
                  self.course, self.year, self.bio]
        score = sum(1 for f in fields if f) + (2 if self.pk and self.interests.exists() else 0)
        return int(score / 10 * 100)

    # ---- social graph helpers ----
    def connection_ids(self):
        rows = Connection.objects.filter(
            Q(requester=self) | Q(receiver=self), status=Connection.ACCEPTED
        ).values_list("requester_id", "receiver_id")
        return {b if a == self.pk else a for a, b in rows}

    def connections(self):
        return User.objects.filter(pk__in=self.connection_ids())

    def blocked_ids(self):
        """Users hidden from me: those I blocked and those who blocked me."""
        rows = Block.objects.filter(Q(blocker=self) | Q(blocked=self)).values_list("blocker_id", "blocked_id")
        return {b if a == self.pk else a for a, b in rows}

    def connection_with(self, other):
        return Connection.objects.filter(
            Q(requester=self, receiver=other) | Q(requester=other, receiver=self)
        ).first()

    def is_connected_to(self, other):
        c = self.connection_with(other)
        return bool(c and c.status == Connection.ACCEPTED)

    def has_blocked(self, other):
        return Block.objects.filter(blocker=self, blocked=other).exists()

    def is_blocked_between(self, other):
        return Block.objects.filter(Q(blocker=self, blocked=other) | Q(blocker=other, blocked=self)).exists()

    def can_view_profile(self, viewer):
        if viewer == self or viewer.is_staff:
            return True
        if self.is_blocked_between(viewer):
            return False
        if self.profile_visibility == "public":
            return True
        if self.profile_visibility == "connections":
            return self.is_connected_to(viewer)
        return False

    def can_receive_message_from(self, sender):
        if sender == self or self.is_blocked_between(sender) or not self.is_active:
            return False
        if self.allow_messages_from == "connections":
            return self.is_connected_to(sender)
        return True


# --------------------------------------------------------------------------
# Connections & blocking
# --------------------------------------------------------------------------
class Connection(models.Model):
    PENDING, ACCEPTED, DECLINED = "pending", "accepted", "declined"
    STATUS_CHOICES = [(PENDING, "Pending"), (ACCEPTED, "Accepted"), (DECLINED, "Declined")]

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_requests")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["requester", "receiver"], name="unique_connection_pair")]

    def __str__(self):
        return f"{self.requester} → {self.receiver} ({self.status})"

    def other(self, user):
        return self.receiver if self.requester_id == user.pk else self.requester


class Block(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocking")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block_pair")]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"


# --------------------------------------------------------------------------
# Communities (defined before Post because posts can belong to one)
# --------------------------------------------------------------------------
class Community(models.Model):
    CATEGORY_CHOICES = [
        ("academic", "Academic"), ("tech", "Tech"), ("culture", "Culture"), ("sports", "Sports"),
        ("arts", "Arts"), ("career", "Career"), ("lifestyle", "Lifestyle"), ("international", "International"),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    tagline = models.CharField(max_length=140, blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to="communities/", blank=True)
    icon = models.CharField(max_length=10, default="👥")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="academic")
    interests = models.ManyToManyField(Interest, blank=True, related_name="communities")
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                related_name="created_communities")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="communities")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "communities"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:110] or "community"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("community_detail", args=[self.slug])


# --------------------------------------------------------------------------
# Feed
# --------------------------------------------------------------------------
class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    text = models.TextField(max_length=2000, blank=True)
    image = models.ImageField(upload_to="posts/", blank=True)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, null=True, blank=True, related_name="posts")
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="liked_posts")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.author}: {self.text[:40]}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} on #{self.post_id}: {self.text[:30]}"


# --------------------------------------------------------------------------
# Messaging
# --------------------------------------------------------------------------
class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation #{self.pk}"

    @classmethod
    def between(cls, a, b, create=True):
        conv = cls.objects.filter(participants=a).filter(participants=b).first()
        if conv is None and create:
            conv = cls.objects.create()
            conv.participants.add(a, b)
        return conv

    def other(self, user):
        return next((p for p in self.participants.all() if p.pk != user.pk), user)

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField(max_length=2000)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender}: {self.text[:30]}"


# --------------------------------------------------------------------------
# Events
# --------------------------------------------------------------------------
class Event(models.Model):
    CATEGORY_CHOICES = [
        ("workshop", "Workshop"), ("meetup", "Meetup"), ("conference", "Conference"), ("party", "Social"),
        ("sports", "Sports"), ("cultural", "Cultural"), ("career", "Career"), ("hackathon", "Hackathon"),
    ]

    title = models.CharField(max_length=150)
    description = models.TextField()
    image = models.ImageField(upload_to="events/", blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="meetup")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200)
    is_online = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Leave empty for unlimited")
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                  related_name="organized_events")
    community = models.ForeignKey(Community, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("event_detail", args=[self.pk])

    @property
    def is_past(self):
        return (self.ends_at or self.starts_at) < timezone.now()

    @property
    def spots_left(self):
        if self.capacity is None:
            return None
        return max(self.capacity - self.participants.count(), 0)

    @property
    def is_full(self):
        return self.capacity is not None and self.spots_left == 0


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------
class Notification(models.Model):
    TYPE_CHOICES = [
        ("connection_request", "Connection request"),
        ("connection_accepted", "Connection accepted"),
        ("message", "New message"),
        ("like", "Like"),
        ("comment", "Comment"),
        ("community", "Community"),
        ("event", "Event"),
        ("event_reminder", "Event reminder"),
        ("system", "System"),
    ]
    ICONS = {
        "connection_request": "bi-person-plus-fill", "connection_accepted": "bi-people-fill",
        "message": "bi-chat-dots-fill", "like": "bi-heart-fill", "comment": "bi-chat-left-text-fill",
        "community": "bi-collection-fill", "event": "bi-calendar-event-fill",
        "event_reminder": "bi-alarm-fill", "system": "bi-stars",
    }

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                              related_name="+")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=150)
    body = models.CharField(max_length=255, blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"→ {self.user}: {self.title}"

    @property
    def icon(self):
        return self.ICONS.get(self.type, "bi-bell-fill")


# --------------------------------------------------------------------------
# Reports (moderation)
# --------------------------------------------------------------------------
class Report(models.Model):
    TARGET_CHOICES = [("user", "User"), ("post", "Post"), ("comment", "Comment"), ("community", "Community")]
    REASON_CHOICES = [
        ("spam", "Spam"), ("harassment", "Harassment or bullying"), ("inappropriate", "Inappropriate content"),
        ("fake", "Fake profile"), ("other", "Other"),
    ]
    STATUS_CHOICES = [("open", "Open"), ("reviewed", "Reviewed"), ("dismissed", "Dismissed")]

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports")
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES)
    target_id = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.target_type} #{self.target_id} — {self.reason}"
