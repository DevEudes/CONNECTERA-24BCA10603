from django.urls import path

from .views import auth, chat, communities, events, feed, network, notifications, profile, settings

urlpatterns = [
    # --- Splash, onboarding & authentication
    path("", auth.landing, name="landing"),
    path("signup/", auth.signup, name="signup"),
    path("login/", auth.signin, name="login"),
    path("forgot-password/", auth.forgot_password, name="forgot_password"),
    path("reset-password/<str:uidb64>/<str:token>/", auth.reset_password, name="reset_password"),
    path("logout/", auth.logout_view, name="logout"),

    # --- Profile setup
    path("welcome/profile/", profile.complete_profile, name="complete_profile"),
    path("welcome/interests/", profile.select_interests, name="select_interests"),
    path("welcome/done/", profile.profile_done, name="profile_done"),

    # --- Home feed & posts
    path("home/", feed.home, name="home"),
    path("posts/new/", feed.create_post, name="create_post"),
    path("posts/<int:pk>/", feed.post_detail, name="post_detail"),
    path("posts/<int:pk>/delete/", feed.delete_post, name="delete_post"),
    path("posts/<int:pk>/like/", feed.toggle_like, name="toggle_like"),
    path("posts/<int:pk>/comment/", feed.add_comment, name="add_comment"),
    path("comments/<int:pk>/delete/", feed.delete_comment, name="delete_comment"),
    path("report/<str:target_type>/<int:target_id>/", feed.report, name="report"),

    # --- Profiles, search & connections
    path("me/", profile.my_profile, name="my_profile"),
    path("me/edit/", profile.edit_profile, name="edit_profile"),
    path("students/<int:pk>/", profile.profile_detail, name="profile_detail"),
    path("students/<int:pk>/connections/", profile.connections_of, name="connections_of"),
    path("search/", network.search, name="search"),
    path("connections/", network.connections, name="connections"),
    path("connections/send/<int:pk>/", network.send_request, name="send_request"),
    path("connections/<int:pk>/<str:action>/", network.respond_request, name="respond_request"),
    path("connections/cancel/<int:pk>/", network.cancel_request, name="cancel_request"),
    path("connections/remove/<int:pk>/", network.remove_connection, name="remove_connection"),
    path("block/<int:pk>/", network.block_user, name="block_user"),
    path("unblock/<int:pk>/", network.unblock_user, name="unblock_user"),

    # --- Messages
    path("messages/", chat.inbox, name="inbox"),
    path("messages/with/<int:user_id>/", chat.start_chat, name="start_chat"),
    path("messages/<int:pk>/", chat.conversation, name="conversation"),
    path("messages/<int:pk>/send/", chat.send_message, name="send_message"),
    path("messages/<int:pk>/poll/", chat.poll_messages, name="poll_messages"),

    # --- Communities
    path("communities/", communities.community_list, name="communities"),
    path("communities/new/", communities.create_community, name="create_community"),
    path("communities/<slug:slug>/", communities.community_detail, name="community_detail"),
    path("communities/<slug:slug>/join/", communities.toggle_membership, name="toggle_membership"),

    # --- Events
    path("events/", events.event_list, name="events"),
    path("events/new/", events.create_event, name="create_event"),
    path("events/<int:pk>/", events.event_detail, name="event_detail"),
    path("events/<int:pk>/register/", events.toggle_registration, name="toggle_registration"),

    # --- Notifications
    path("notifications/", notifications.notification_list, name="notifications"),
    path("notifications/<int:pk>/open/", notifications.open_notification, name="open_notification"),
    path("notifications/read-all/", notifications.mark_all_read, name="mark_all_read"),
    path("notifications/clear/", notifications.clear_notifications, name="clear_notifications"),
    path("api/counts/", notifications.counts, name="counts"),

    # --- Settings
    path("settings/", settings.settings_index, name="settings"),
    path("settings/account/", settings.account, name="settings_account"),
    path("settings/privacy/", settings.privacy, name="settings_privacy"),
    path("settings/notifications/", settings.notification_prefs, name="settings_notifications"),
    path("settings/appearance/", settings.appearance, name="settings_appearance"),
    path("settings/blocked/", settings.blocked_users, name="settings_blocked"),
    path("settings/help/", settings.help_support, name="settings_help"),
    path("settings/deactivate/", settings.deactivate_account, name="deactivate_account"),
]
