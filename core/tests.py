"""
Functional tests — they follow the validation table of the specification (§14).

    python manage.py test core
"""
from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

import re

from django.core import mail

from .models import (Block, Community, Connection, Conversation, Event, Interest, Message, Notification, Post,
                     User)


def make_student(email, name="Student Test", **extra):
    defaults = dict(full_name=name, profile_completed=True, university="Chandigarh University",
                    course="BCA", country="Cameroon", destination_country="India", year=2)
    defaults.update(extra)
    return User.objects.create_user(email=email, password="Str0ng!Pass", **defaults)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthTests(TestCase):
    def setUp(self):
        cache.clear()

    def signup(self, email="new@test.com"):
        return self.client.post(reverse("signup"), {
            "full_name": "New Student", "email": email, "password": "Str0ng!Pass", "password2": "Str0ng!Pass",
            "terms": "on"})

    def test_signup_with_valid_data_creates_account(self):
        r = self.signup()
        self.assertRedirects(r, reverse("complete_profile"))  # no OTP step: straight to the profile
        user = User.objects.get(email="new@test.com")
        self.assertNotEqual(user.password, "Str0ng!Pass")  # never stored in clear text
        self.assertTrue(user.password.startswith("pbkdf2_"))

    def test_signup_with_existing_email_shows_clear_error(self):
        make_student("taken@test.com")
        r = self.signup("TAKEN@test.com")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "already exists")
        self.assertEqual(User.objects.filter(email__iexact="taken@test.com").count(), 1)

    def test_login_with_valid_credentials(self):
        make_student("ok@test.com")
        r = self.client.post(reverse("login"), {"email": "ok@test.com", "password": "Str0ng!Pass"})
        self.assertRedirects(r, reverse("home"))

    def test_login_with_wrong_password(self):
        make_student("ok@test.com")
        r = self.client.post(reverse("login"), {"email": "ok@test.com", "password": "wrong"})
        self.assertContains(r, "Incorrect e-mail or password")

    def test_login_is_rate_limited(self):
        make_student("ok@test.com")
        for _ in range(8):
            self.client.post(reverse("login"), {"email": "ok@test.com", "password": "wrong"})
        r = self.client.post(reverse("login"), {"email": "ok@test.com", "password": "Str0ng!Pass"})
        self.assertEqual(r.status_code, 429)

    def test_forgot_and_reset_password_with_email_link(self):
        make_student("forgot@test.com")
        self.client.post(reverse("forgot_password"), {"email": "forgot@test.com"})
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
        path = link.split("testserver", 1)[1]
        r = self.client.post(path, {"password": "N3w!Password", "password2": "N3w!Password"})
        self.assertRedirects(r, reverse("login"))
        self.assertTrue(self.client.login(username="forgot@test.com", password="N3w!Password"))
        # the link is single-use
        self.assertRedirects(self.client.get(path), reverse("forgot_password"))

    def test_forgot_password_unknown_email_reveals_nothing(self):
        r = self.client.post(reverse("forgot_password"), {"email": "nobody@test.com"})
        self.assertContains(r, "If an account exists")
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_reset_link_is_refused(self):
        u = make_student("x@test.com")
        from django.utils.http import urlsafe_base64_encode
        r = self.client.get(reverse("reset_password", args=[urlsafe_base64_encode(str(u.pk).encode()), "bad-token"]))
        self.assertRedirects(r, reverse("forgot_password"))

    def test_new_user_must_complete_profile(self):
        make_student("new2@test.com", profile_completed=False)
        self.client.login(username="new2@test.com", password="Str0ng!Pass")
        self.assertRedirects(self.client.get(reverse("home")), reverse("complete_profile"))

    def test_logout(self):
        make_student("ok@test.com")
        self.client.login(username="ok@test.com", password="Str0ng!Pass")
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("home")).status_code, 302)


class SecurityTests(TestCase):
    def test_private_routes_require_authentication(self):
        for name in ["home", "search", "inbox", "communities", "events", "notifications", "settings", "my_profile"]:
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn(reverse("login"), r.url)

    def test_cannot_read_someone_elses_conversation(self):
        a, b, c = make_student("a@t.com"), make_student("b@t.com"), make_student("c@t.com")
        conv = Conversation.between(a, b)
        Message.objects.create(conversation=conv, sender=a, text="secret")
        self.client.login(username="c@t.com", password="Str0ng!Pass")
        self.assertEqual(self.client.get(reverse("conversation", args=[conv.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("send_message", args=[conv.pk]), {"text": "hi"}).status_code, 404)

    def test_cannot_delete_someone_elses_post(self):
        a, b = make_student("a@t.com"), make_student("b@t.com")
        post = Post.objects.create(author=a, text="mine")
        self.client.login(username="b@t.com", password="Str0ng!Pass")
        self.client.post(reverse("delete_post", args=[post.pk]))
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_edit_profile_only_changes_my_profile(self):
        me, other = make_student("me@t.com", "Me"), make_student("o@t.com", "Other")
        self.client.login(username="me@t.com", password="Str0ng!Pass")
        self.client.post(reverse("edit_profile"), {
            "full_name": "Me Edited", "country": "India", "destination_country": "India",
            "university": "CU", "course": "BCA", "year": 1})
        me.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(me.full_name, "Me Edited")
        self.assertEqual(other.full_name, "Other")

    def test_open_redirect_is_blocked(self):
        a, b = make_student("a@t.com"), make_student("b@t.com")
        post = Post.objects.create(author=b, text="hello")
        self.client.login(username="a@t.com", password="Str0ng!Pass")
        r = self.client.post(reverse("toggle_like", args=[post.pk]), {"next": "https://evil.example.com/"})
        self.assertFalse(r.url.startswith("https://evil"))


class ProfileAndSearchTests(TestCase):
    def setUp(self):
        self.me = make_student("me@t.com", "Marie N", profile_completed=False)
        self.client.login(username="me@t.com", password="Str0ng!Pass")
        self.interests = [Interest.objects.create(name=n) for n in ["Coding", "Music", "Dance", "Travel"]]

    def test_complete_profile_and_interests(self):
        r = self.client.post(reverse("complete_profile"), {
            "full_name": "Marie N", "country": "Cameroon", "destination_country": "India",
            "university": "Chandigarh University", "course": "BCA", "year": 3, "bio": "Hello"})
        self.assertRedirects(r, reverse("select_interests"))
        r = self.client.post(reverse("select_interests"), {"interests": [i.pk for i in self.interests[:3]]})
        self.assertRedirects(r, reverse("profile_done"))
        self.me.refresh_from_db()
        self.assertTrue(self.me.profile_completed)
        self.assertEqual(self.me.interests.count(), 3)

    def test_less_than_three_interests_is_refused(self):
        self.client.post(reverse("select_interests"), {"interests": [self.interests[0].pk]})
        self.me.refresh_from_db()
        self.assertFalse(self.me.profile_completed)

    def test_search_by_name_university_and_course(self):
        self.me.profile_completed = True
        self.me.save()
        make_student("aisha@t.com", "Aisha Bello", university="Panjab University", course="MBA")
        make_student("rahul@t.com", "Rahul Joshi")
        self.assertContains(self.client.get(reverse("search"), {"q": "aisha"}), "Aisha Bello")
        r = self.client.get(reverse("search"), {"university": "Panjab University"})
        self.assertContains(r, "Aisha Bello")
        self.assertNotContains(r, "Rahul Joshi")
        self.assertContains(self.client.get(reverse("search"), {"q": "MBA"}), "Aisha Bello")


class SocialTests(TestCase):
    def setUp(self):
        self.a = make_student("a@t.com", "Alice A")
        self.b = make_student("b@t.com", "Bob B")
        self.client.login(username="a@t.com", password="Str0ng!Pass")

    def test_send_request_creates_pending_connection_and_notification(self):
        self.client.post(reverse("send_request", args=[self.b.pk]))
        c = Connection.objects.get(requester=self.a, receiver=self.b)
        self.assertEqual(c.status, Connection.PENDING)
        self.assertTrue(Notification.objects.filter(user=self.b, type="connection_request").exists())

    def test_duplicate_requests_are_prevented(self):
        self.client.post(reverse("send_request", args=[self.b.pk]))
        self.client.post(reverse("send_request", args=[self.b.pk]))
        self.assertEqual(Connection.objects.count(), 1)

    def test_reverse_request_accepts_instead_of_duplicating(self):
        Connection.objects.create(requester=self.b, receiver=self.a)
        self.client.post(reverse("send_request", args=[self.b.pk]))
        self.assertEqual(Connection.objects.count(), 1)
        self.assertEqual(Connection.objects.get().status, Connection.ACCEPTED)

    def test_accept_and_decline(self):
        c = Connection.objects.create(requester=self.b, receiver=self.a)
        self.client.post(reverse("respond_request", args=[c.pk, "accept"]))
        c.refresh_from_db()
        self.assertEqual(c.status, Connection.ACCEPTED)
        self.assertTrue(Notification.objects.filter(user=self.b, type="connection_accepted").exists())
        self.assertTrue(self.a.is_connected_to(self.b))

    def test_only_receiver_can_accept(self):
        c = Connection.objects.create(requester=self.a, receiver=self.b)
        r = self.client.post(reverse("respond_request", args=[c.pk, "accept"]))
        self.assertEqual(r.status_code, 404)

    def test_message_between_connected_students(self):
        Connection.objects.create(requester=self.a, receiver=self.b, status=Connection.ACCEPTED)
        r = self.client.get(reverse("start_chat", args=[self.b.pk]))
        conv = Conversation.between(self.a, self.b, create=False)
        self.assertRedirects(r, reverse("conversation", args=[conv.pk]))
        self.client.post(reverse("send_message", args=[conv.pk]), {"text": "Hi Bob 👋"})
        self.assertEqual(conv.messages.get().text, "Hi Bob 👋")
        self.assertTrue(Notification.objects.filter(user=self.b, type="message").exists())
        # Bob sees it and it gets marked as read
        self.client.login(username="b@t.com", password="Str0ng!Pass")
        self.assertContains(self.client.get(reverse("conversation", args=[conv.pk])), "Hi Bob")
        self.assertIsNotNone(conv.messages.get().read_at)

    def test_messages_restricted_to_connections(self):
        self.b.allow_messages_from = "connections"
        self.b.save()
        self.client.get(reverse("start_chat", args=[self.b.pk]))
        self.assertIsNone(Conversation.between(self.a, self.b, create=False))

    def test_blocked_user_cannot_interact(self):
        Block.objects.create(blocker=self.b, blocked=self.a)
        self.client.post(reverse("send_request", args=[self.b.pk]))
        self.assertEqual(Connection.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("profile_detail", args=[self.b.pk])).status_code, 404)
        conv = Conversation.between(self.a, self.b)
        self.client.post(reverse("send_message", args=[conv.pk]), {"text": "hey"})
        self.assertEqual(conv.messages.count(), 0)

    def test_like_and_comment_generate_notifications(self):
        post = Post.objects.create(author=self.b, text="Hello campus")
        self.client.post(reverse("toggle_like", args=[post.pk]))
        self.client.post(reverse("add_comment", args=[post.pk]), {"text": "Nice!"})
        self.assertEqual(post.likes.count(), 1)
        self.assertEqual(post.comments.count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.b, type__in=["like", "comment"]).count(), 2)

    def test_create_post(self):
        self.client.post(reverse("create_post"), {"text": "My first post"})
        self.assertTrue(Post.objects.filter(author=self.a, text="My first post").exists())

    def test_join_community(self):
        c = Community.objects.create(name="AI Club", description="AI")
        self.client.post(reverse("toggle_membership", args=[c.slug]))
        self.assertTrue(c.members.filter(pk=self.a.pk).exists())
        self.client.post(reverse("toggle_membership", args=[c.slug]))
        self.assertFalse(c.members.filter(pk=self.a.pk).exists())

    def test_register_to_event(self):
        e = Event.objects.create(title="Hackathon", description="24h", location="Lab",
                                 starts_at=timezone.now() + timedelta(days=2), organizer=self.b)
        self.client.post(reverse("toggle_registration", args=[e.pk]))
        self.assertTrue(e.participants.filter(pk=self.a.pk).exists())
        self.assertTrue(Notification.objects.filter(user=self.b, type="event").exists())

    def test_full_event_refuses_registration(self):
        e = Event.objects.create(title="Small", description="x", location="Lab", capacity=1,
                                 starts_at=timezone.now() + timedelta(days=2))
        e.participants.add(self.b)
        self.client.post(reverse("toggle_registration", args=[e.pk]))
        self.assertFalse(e.participants.filter(pk=self.a.pk).exists())

    def test_mark_notifications_as_read(self):
        Notification.objects.create(user=self.a, type="system", title="Hi")
        self.client.post(reverse("mark_all_read"))
        self.assertFalse(self.a.notifications.filter(is_read=False).exists())

    def test_disabled_notification_preference_is_respected(self):
        self.b.notify_posts = False
        self.b.save()
        post = Post.objects.create(author=self.b, text="x")
        self.client.post(reverse("toggle_like", args=[post.pk]))
        self.assertFalse(Notification.objects.filter(user=self.b, type="like").exists())
