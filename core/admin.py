from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (Block, Comment, Community, Connection, Conversation, Event, Interest, Message, Notification,
                     Post, Report, User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "full_name", "university", "course", "country", "is_active", "is_staff"]
    list_filter = ["is_active", "is_staff", "profile_completed", "country", "year"]
    search_fields = ["email", "full_name", "university", "course"]
    filter_horizontal = ["interests", "groups", "user_permissions"]
    actions = ["deactivate", "activate"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("full_name", "avatar", "cover", "headline", "country", "destination_country",
                                "university", "course", "year", "bio", "interests")}),
        ("State", {"fields": ("profile_completed", "is_active", "is_staff", "is_superuser")}),
        ("Privacy & preferences", {"fields": ("profile_visibility", "allow_messages_from", "show_email", "theme",
                                              "language", "notify_connections", "notify_messages", "notify_posts",
                                              "notify_events")}),
        ("Dates", {"fields": ("last_login", "date_joined", "last_seen")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2")}),)

    @admin.action(description="Suspend selected accounts")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Reactivate selected accounts")
    def activate(self, request, queryset):
        queryset.update(is_active=True)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["id", "target_type", "target_id", "reason", "reporter", "status", "created_at"]
    list_filter = ["status", "target_type", "reason"]
    list_editable = ["status"]
    actions = ["mark_reviewed", "dismiss"]

    @admin.action(description="Mark as reviewed")
    def mark_reviewed(self, request, queryset):
        queryset.update(status="reviewed")

    @admin.action(description="Dismiss")
    def dismiss(self, request, queryset):
        queryset.update(status="dismissed")


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "creator", "member_count", "created_at"]
    list_filter = ["category"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["members", "interests"]

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.members.count()


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "starts_at", "location", "organizer", "participant_count"]
    list_filter = ["category", "is_online"]
    search_fields = ["title", "location"]
    filter_horizontal = ["participants"]
    date_hierarchy = "starts_at"

    @admin.display(description="Participants")
    def participant_count(self, obj):
        return obj.participants.count()


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["id", "author", "short_text", "community", "created_at"]
    search_fields = ["text", "author__full_name"]
    inlines = [CommentInline]
    filter_horizontal = ["likes"]

    @admin.display(description="Text")
    def short_text(self, obj):
        return obj.text[:60]


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ["requester", "receiver", "status", "created_at"]
    list_filter = ["status"]


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "updated_at"]
    inlines = [MessageInline]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "title", "is_read", "created_at"]
    list_filter = ["type", "is_read"]


admin.site.register(Interest)
admin.site.register(Block)
admin.site.register(Comment)
admin.site.register(Message)

