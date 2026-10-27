"""
Fill the database with realistic demo data.

    python manage.py seed            # wipe app data and re-create everything
    python manage.py seed --no-download   # never hit the network (gradient placeholders)

Pictures are cached in core/seed_assets/ so the command works offline after
the first run (avatars from randomuser.me, photos from picsum.photos).
"""
import io
import os
import random
import shutil
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (Block, Comment, Community, Connection, Conversation, Event, Interest, Message, Notification,
                         Post, Report, User)

ASSETS = Path(__file__).resolve().parents[2] / "seed_assets"
PASSWORD = "Demo@1234"

INTERESTS = [
    ("Coding", "💻"), ("AI & ML", "🤖"), ("Music", "🎵"), ("Photography", "📷"), ("Travel", "✈️"),
    ("Football", "⚽"), ("Basketball", "🏀"), ("Cricket", "🏏"), ("Dance", "💃"), ("Movies", "🎬"),
    ("Reading", "📚"), ("Gaming", "🎮"), ("Fashion", "👗"), ("Cooking", "🍳"), ("Fitness", "💪"),
    ("Art & Design", "🎨"), ("Entrepreneurship", "🚀"), ("Volunteering", "🤝"), ("Languages", "🗣️"),
    ("Anime", "🍥"), ("Writing", "✍️"), ("Finance", "💹"), ("Science", "🔬"), ("Nature", "🌿"),
]

# full name, gender, home country, university, course, year
STUDENTS = [
    ("Aarav Sharma", "m", "India", "Chandigarh University", "B.Tech CSE", 3),
    ("Priya Patel", "f", "India", "Chandigarh University", "BCA", 2),
    ("Rohan Mehta", "m", "India", "Chandigarh University", "BBA", 2),
    ("Ananya Gupta", "f", "India", "Panjab University", "B.Sc Data Science", 3),
    ("Arjun Singh", "m", "India", "Chandigarh University", "B.Tech AI & ML", 4),
    ("Ishita Verma", "f", "India", "Chandigarh University", "B.Des Fashion", 1),
    ("Karan Malhotra", "m", "India", "Lovely Professional University", "MBA", 6),
    ("Sneha Reddy", "f", "India", "Chandigarh University", "BCA", 3),
    ("Vikram Rao", "m", "India", "IIT Delhi", "B.Tech CSE", 2),
    ("Meera Iyer", "f", "India", "Christ University", "BA Journalism", 2),
    ("Aditya Kapoor", "m", "India", "Chandigarh University", "MCA", 6),
    ("Kavya Nair", "f", "India", "Manipal University", "MBBS", 3),
    ("Rahul Joshi", "m", "India", "Chandigarh University", "BCA", 3),
    ("Neha Chauhan", "f", "India", "Chandigarh University", "B.Pharm", 2),
    ("Siddharth Bansal", "m", "India", "Amity University", "B.Com", 1),
    ("Pooja Thakur", "f", "India", "Chandigarh University", "Hotel Management", 2),
    ("Harpreet Kaur", "f", "India", "Chandigarh University", "B.Tech CSE", 3),
    ("Gurpreet Gill", "m", "India", "Panjab University", "LLB", 4),
    ("Aisha Bello", "f", "Nigeria", "Chandigarh University", "BCA", 3),
    ("Chinedu Okafor", "m", "Nigeria", "Chandigarh University", "B.Tech CSE", 2),
    ("Fatou Diop", "f", "Senegal", "Chandigarh University", "BBA", 2),
    ("Moussa Traoré", "m", "Ivory Coast", "Chandigarh University", "MCA", 6),
    ("Grace Wanjiku", "f", "Kenya", "Lovely Professional University", "B.Sc Biotechnology", 3),
    ("Brian Otieno", "m", "Kenya", "Chandigarh University", "B.Tech AI & ML", 2),
    ("Kwame Mensah", "m", "Ghana", "Chandigarh University", "MBA", 6),
    ("Ama Owusu", "f", "Ghana", "Sharda University", "BA Journalism", 1),
    ("Jean-Paul Mbarga", "m", "Cameroon", "Chandigarh University", "BCA", 3),
    ("Larissa Fotso", "f", "Cameroon", "Chandigarh University", "BCA", 3),
    ("Yannick Ndzana", "m", "Cameroon", "Chandigarh University", "B.Tech CSE", 4),
    ("Divine Nkeng", "f", "Cameroon", "Galgotias University", "B.Pharm", 2),
    ("Tendai Moyo", "m", "Zimbabwe", "Chandigarh University", "B.Com", 3),
    ("Aline Uwase", "f", "Rwanda", "Chandigarh University", "B.Sc Data Science", 2),
    ("Patrick Kabila", "m", "DR Congo", "Chandigarh University", "BBA", 3),
    ("Ruth Tesfaye", "f", "Ethiopia", "Sharda University", "MBBS", 2),
    ("Ibrahim Sow", "m", "Senegal", "Chandigarh University", "B.Tech CSE", 1),
    ("Nadia El Amrani", "f", "Morocco", "Chandigarh University", "B.Arch", 3),
    ("Sujan Shrestha", "m", "Nepal", "Chandigarh University", "BCA", 2),
    ("Anjali Thapa", "f", "Nepal", "Chandigarh University", "B.Des Fashion", 2),
    ("Tashi Dorji", "m", "Bhutan", "Lovely Professional University", "B.Tech CSE", 3),
    ("Nimal Perera", "m", "Sri Lanka", "Chandigarh University", "Hotel Management", 2),
    ("Farhana Rahman", "f", "Bangladesh", "Chandigarh University", "MCA", 6),
    ("Ahmad Rahimi", "m", "Afghanistan", "Chandigarh University", "BBA", 3),
    ("Linh Nguyen", "f", "Vietnam", "Chandigarh University", "B.Sc Data Science", 3),
    ("Ali Hassan", "m", "Iraq", "Chandigarh University", "MBA", 6),
    ("Sara Karimi", "f", "Iran", "Panjab University", "B.Arch", 4),
    ("Lucas Martin", "m", "France", "Chandigarh University", "BBA", 2),
    ("Emma Schneider", "f", "Germany", "Chandigarh University", "BA Journalism", 2),
]

HEADLINES = [
    "Aspiring software engineer ✨", "Future data scientist 📊", "Full-stack dev in the making",
    "Coffee, code & cricket ☕", "Design lover • Dreamer • Doer", "Building my first startup 🚀",
    "Student ambassador 🌍", "Learning something new every day", "Music is my second language 🎶",
    "Tech enthusiast & hackathon addict", "Exploring India one city at a time 🇮🇳", "Photographer by passion 📸",
    "Volunteer & community builder 🤝", "Bookworm & storyteller 📚", "Gym, grind & good vibes 💪",
]
BIO_TEMPLATES = [
    "Hi! I'm {first}, a {year} {course} student at {uni}. I love {i1} and {i2}. Always happy to meet new people, "
    "study together or grab a chai after class ☕",
    "{course} student from {country} 🌍. Passionate about {i1}, {i2} and {i3}. Let's connect and grow together!",
    "Originally from {country}, now studying {course} at {uni}. Into {i1} & {i2}. Ask me anything about student life "
    "in India 😊",
    "{year} {course} • {i1} lover • {i2} on weekends. Currently looking for teammates for the next hackathon!",
]

POSTS = [
    ("Just finished my first full-stack project with Django and React! 🎉 It took 3 weeks of late nights but it was "
     "so worth it. Big thanks to everyone who helped me debug at 2am 😅", True),
    ("Who's going to the Tech Career Fair this Friday? Let's go together and prepare our CVs before! 💼", False),
    ("Sunset from the hostel rooftop never disappoints 🌅 #CampusLife", True),
    ("Exam season survival kit: coffee ☕, lo-fi playlist 🎧 and the best study group ever. We got this!", False),
    ("Our team won 2nd place at the 24h hackathon 🏆 We built an app that helps international students find "
     "accommodation near campus. So proud of this squad!", True),
    ("Missing home food so much today 🥺 Any Cameroonian or Nigerian restaurant recommendations near Mohali?", False),
    ("First time trying a Punjabi thali and wow… I understand now why everyone loves it 😍🍛", True),
    ("Reminder: the library is open 24/7 during exam weeks. See you on the 3rd floor 📚", False),
    ("Started learning Hindi this semester! Main thoda thoda Hindi bolti hoon 😄 Any tips?", False),
    ("Weekend trip to Shimla with the international students club ⛰️ Best decision ever!", True),
    ("Looking for 2 teammates (frontend + design) for the Smart India Hackathon. DM me if interested! 🚀", False),
    ("Football final tonight at the main ground ⚽ Come support the CU Lions!", True),
    ("Grateful for this community. Moving to a new country alone was scary, but you all made it feel like home 💜",
     False),
    ("Can someone explain recursion to me like I'm five? Asking for a friend… the friend is me 😭", False),
    ("Diwali celebrations on campus were magical ✨🪔 Thank you to everyone who invited us to celebrate!", True),
    ("Just got my first internship offer as a data analyst intern!!! 🥳 Hard work pays off.", False),
    ("Photography walk around Sukhna Lake this Sunday morning 📷 Join us, all levels welcome!", True),
    ("Pro tip for freshers: join at least one club in your first semester. Best way to make friends 🙌", False),
    ("Morning workout done 💪 Who wants to join the 6am running group?", True),
    ("My notes for Database Management Systems are now in the BCA community. Hope it helps for the mid-sems 📝",
     False),
    ("Cultural night rehearsals in full swing 💃 Can't wait for you all to see the African dance performance!", True),
    ("Anyone else obsessed with the new canteen momos? 🥟", False),
    ("Book of the month: 'Atomic Habits'. Small changes, remarkable results. Highly recommend 📖", True),
    ("Finally deployed my portfolio website 🌐 Feedback welcome!", False),
    ("Throwback to orientation week. Look how far we've come 🥹", True),
    ("Fun fact: there are students from more than 40 countries on our campus 🌍 How cool is that?", False),
    ("Late-night coding session with the squad. Bugs: 47. Fixed: 46. 😂", True),
    ("Holi was the most colourful day of my life 🌈 Literally.", True),
    ("Started a small podcast about international student life 🎙️ Episode 1 is out!", False),
    ("Just a reminder that it's okay to take breaks. Your mental health matters 💜", False),
]

COMMENTS = [
    "This is amazing! 🔥", "Congrats!! So proud of you 🎉", "Count me in!", "Love this 😍", "Where is this? 🤩",
    "So true 😂", "Let's do it together!", "Great job 👏", "Can you share more details?", "Wow, beautiful shot 📸",
    "I need this energy today 💪", "Same here haha", "DM me!", "Thanks for sharing 🙏", "Can't wait! 🙌",
    "You deserve it!", "Following for updates 👀", "Haha relatable", "Let's meet at the library?", "🔥🔥🔥",
]

COMMUNITIES = [
    ("Coders of CU", "💻", "tech", "Code, collaborate, ship.",
     "A community for every student who loves to code — from first 'Hello World' to production apps. Weekly "
     "coding challenges, peer reviews and project showcases.", ["Coding", "AI & ML", "Gaming"]),
    ("AI & ML Club", "🤖", "tech", "Learning machines, learning together.",
     "Workshops on Python, data science, machine learning and generative AI. We read papers, build projects and "
     "participate in Kaggle competitions as a team.", ["AI & ML", "Coding", "Science"]),
    ("African Students Union", "🌍", "international", "Ubuntu — I am because we are.",
     "The home of African students in Chandigarh. Cultural nights, food festivals, mentoring for newcomers and "
     "support for administrative procedures.", ["Travel", "Music", "Dance", "Cooking"]),
    ("International Students Hub", "✈️", "international", "40+ countries, one campus.",
     "Tips for visas, FRRO registration, accommodation, travel and student life in India. Ask anything, help "
     "everyone.", ["Travel", "Languages", "Volunteering"]),
    ("Photography Circle", "📸", "arts", "Capture the campus.",
     "Photo walks, editing workshops and monthly photo challenges. All cameras welcome, phones included!",
     ["Photography", "Art & Design", "Nature", "Travel"]),
    ("CU Football League", "⚽", "sports", "Play hard, play fair.",
     "Inter-department football league, weekend friendly matches and training sessions every Tuesday & Thursday.",
     ["Football", "Fitness"]),
    ("Bollywood Dance Crew", "💃", "arts", "Nachle, dance like nobody's watching!",
     "From Bhangra to Afrobeats, we dance everything. Beginners welcome — rehearsals 3 times a week.",
     ["Dance", "Music", "Movies"]),
    ("Startup Garage", "🚀", "career", "From idea to MVP.",
     "For future founders: pitch nights, mentor sessions with alumni, and a space to find co-founders.",
     ["Entrepreneurship", "Finance", "Coding"]),
    ("Book Lovers Society", "📚", "culture", "One chapter at a time.",
     "Monthly book club, writing circles and a book exchange shelf in Block B.", ["Reading", "Writing"]),
    ("Francophone Corner", "🥐", "culture", "On parle français ici !",
     "Pour tous les étudiants francophones et ceux qui veulent pratiquer le français. Soirées ciné, cafés "
     "conversation et entraide.", ["Languages", "Movies", "Travel"]),
    ("Fitness & Wellness", "💪", "lifestyle", "Healthy body, healthy mind.",
     "Morning runs, yoga sessions, gym buddies and mental-health check-ins.", ["Fitness", "Nature", "Cooking"]),
    ("BCA Batch 2024", "🎓", "academic", "Notes, doubts & memes.",
     "The official space for BCA students who joined in 2024: share notes, assignments deadlines and help each "
     "other before exams.", ["Coding", "Reading"]),
    ("Placement Prep", "💼", "career", "Crack your dream job.",
     "Mock interviews, aptitude practice, resume reviews and company-specific preparation.",
     ["Coding", "Finance", "Entrepreneurship"]),
    ("Foodies of Punjab", "🍛", "lifestyle", "Eat. Review. Repeat.",
     "Discover the best dhabas, cafés and street food around Chandigarh and Mohali.", ["Cooking", "Travel"]),
]

# title, category, community index, days from now, hour, duration h, location, online, capacity
EVENTS = [
    ("Tech Career Fair 2026", "career", 12, 3, 10, 6, "CU Main Auditorium, Block A", False, 300),
    ("24h Hackathon: Build for Students", "hackathon", 0, 9, 9, 24, "Innovation Lab, Block C", False, 120),
    ("Intro to Generative AI Workshop", "workshop", 1, 2, 15, 2, "Online — Google Meet", True, None),
    ("Africa Day Cultural Night", "cultural", 2, 16, 18, 4, "Open Air Theatre", False, 500),
    ("Newcomers Welcome Meetup", "meetup", 3, 1, 17, 2, "International Lounge, Block D", False, 80),
    ("Sukhna Lake Photo Walk", "meetup", 4, 5, 6, 3, "Sukhna Lake, Chandigarh", False, 30),
    ("Inter-Department Football Final", "sports", 5, 4, 16, 2, "CU Main Ground", False, None),
    ("Bhangra x Afrobeats Dance Battle", "party", 6, 11, 19, 3, "Student Activity Centre", False, 250),
    ("Startup Pitch Night", "conference", 7, 7, 18, 3, "Incubation Centre", False, 100),
    ("Book Club: Atomic Habits", "meetup", 8, 6, 17, 1, "Central Library, Room 204", False, 25),
    ("Ciné-club : Intouchables", "cultural", 9, 8, 19, 2, "Seminar Hall 3", False, 60),
    ("Sunrise Yoga Session", "sports", 10, 2, 6, 1, "University Lawn", False, 40),
    ("DBMS Mid-Sem Revision Marathon", "workshop", 11, 3, 14, 4, "Block B, Lab 12", False, 70),
    ("Mock Interview Day", "career", 12, 13, 10, 5, "Placement Cell, Block A", False, 90),
    ("Street Food Tour: Sector 17", "party", 13, 10, 17, 3, "Sector 17 Plaza, Chandigarh", False, 20),
    ("Diwali Mela on Campus", "cultural", 3, -6, 17, 5, "CU Main Ground", False, None),
    ("Python for Beginners Bootcamp", "workshop", 0, -12, 10, 6, "Innovation Lab, Block C", False, 80),
    ("Freshers' Night 2026", "party", None, -20, 19, 4, "Open Air Theatre", False, 600),
]

CHATS = [  # (student index, messages: (from_me, text)) — "me" is the demo user
    (26, [(False, "Salut Marie ! Tu as compris le devoir de DBMS ?"), (True, "Salut Jean-Paul ! Oui à peu près 😅"),
          (True, "On peut réviser ensemble à la bibliothèque demain ?"), (False, "Parfait, 16h au 3e étage ?"),
          (True, "Ça marche 👍"), (False, "J'apporte mes notes sur la normalisation 📚")]),
    (18, [(False, "Hey Marie! Are you coming to the Africa Day rehearsal tonight?"),
          (True, "Yes!! I'll be there at 7 💃"), (False, "Amazing, bring your friend Larissa too!"),
          (False, "We need more dancers for the final number 😄")]),
    (1, [(True, "Hi Priya, thanks for accepting my request 😊"), (False, "Of course! We're in the same batch haha"),
         (False, "Did you join the BCA Batch 2024 community? All the notes are there"),
         (True, "Just joined, thank you so much 🙏")]),
    (0, [(False, "Hey! Saw your post about the hackathon. Do you have a team yet?"),
         (True, "Not yet! I'm good at frontend and UI design"), (False, "Perfect, we need exactly that 🔥"),
         (False, "Let's meet tomorrow after class to discuss the idea?")]),
    (27, [(False, "Marie tu viens au ciné-club vendredi ?"), (True, "Oui bien sûr ! C'est quel film ?"),
          (False, "Intouchables 🎬"), (True, "Trop bien, je l'adore ❤️")]),
    (42, [(True, "Hi Linh! Can you share the data science resources you mentioned?"),
          (False, "Sure! I'll send the links tonight 📊")]),
]


class Command(BaseCommand):
    help = "Wipe the Connectera data and fill the database with realistic demo content."

    def add_arguments(self, parser):
        parser.add_argument("--no-download", action="store_true", help="Do not download pictures.")

    # ------------------------------------------------------------------ images
    def fetch(self, key, url):
        """Return image bytes from the local cache, the network, or None."""
        path = ASSETS / f"{key}.jpg"
        if path.exists():
            return path.read_bytes()
        if self.offline:
            return None
        data = b""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Connectera-seed"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = r.read()
        except Exception:  # noqa: BLE001 — network problems must never break seeding
            if shutil.which("curl"):  # fallback (e.g. Python SSL certificates missing on macOS)
                res = subprocess.run(["curl", "-sL", "-m", "20", "-A", "Mozilla/5.0", url], capture_output=True)
                data = res.stdout if res.returncode == 0 else b""
        if len(data) > 2000:
            ASSETS.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return data
        return None

    def placeholder(self, seed, size=(1200, 700)):
        """Purple gradient picture generated with Pillow (offline fallback)."""
        from PIL import Image, ImageDraw

        rnd = random.Random(seed)
        palette = [(124, 58, 237), (168, 85, 247), (236, 72, 153), (99, 102, 241), (14, 165, 233), (20, 184, 166)]
        c1, c2 = rnd.sample(palette, 2)
        w, h = size
        img = Image.new("RGB", size, c1)
        draw = ImageDraw.Draw(img)
        for y in range(h):
            t = y / h
            draw.line([(0, y), (w, y)], fill=tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3)))
        for _ in range(6):
            r = rnd.randint(60, 220)
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            draw.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255), width=3)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        return buf.getvalue()

    def prefetch(self, jobs):
        with ThreadPoolExecutor(max_workers=12) as pool:
            return dict(zip([k for k, _ in jobs], pool.map(lambda j: self.fetch(*j), jobs)))

    def attach(self, field, name, data, seed):
        field.save(name, ContentFile(data or self.placeholder(seed)), save=False)

    # ------------------------------------------------------------------ main
    def handle(self, *args, **opts):
        self.offline = opts["no_download"]
        random.seed(2026)
        now = timezone.now()

        self.stdout.write("🧹 Cleaning previous data…")
        with transaction.atomic():
            for model in [Notification, Report, Message, Conversation, Comment, Post, Event, Community, Block,
                          Connection]:
                model.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            Interest.objects.all().delete()
        for sub in ["avatars", "covers", "posts", "communities", "events"]:
            shutil.rmtree(Path(settings.MEDIA_ROOT) / sub, ignore_errors=True)

        # -------- download pictures in parallel (cached afterwards)
        self.stdout.write("🖼  Fetching pictures (cached in core/seed_assets)…")
        jobs, women, men = [], iter(range(10, 99)), iter(range(10, 99))
        avatar_urls = []
        for name, gender, *_ in STUDENTS + [("Marie Ngimbis", "f")]:
            n = next(women) if gender == "f" else next(men)
            folder = "women" if gender == "f" else "men"
            avatar_urls.append((f"avatar_{folder}_{n}", f"https://randomuser.me/api/portraits/{folder}/{n}.jpg"))
        jobs += avatar_urls
        jobs += [(f"post_{i}", f"https://picsum.photos/seed/connectera-post-{i}/1200/800") for i in range(len(POSTS))]
        jobs += [(f"community_{i}", f"https://picsum.photos/seed/connectera-community-{i}/1200/600")
                 for i in range(len(COMMUNITIES))]
        jobs += [(f"event_{i}", f"https://picsum.photos/seed/connectera-event-{i}/1200/700") for i in range(len(EVENTS))]
        jobs += [(f"cover_{i}", f"https://picsum.photos/seed/connectera-cover-{i}/1500/500") for i in range(12)]
        images = self.prefetch(jobs)
        downloaded = sum(1 for v in images.values() if v)
        self.stdout.write(f"   {downloaded}/{len(jobs)} pictures available")

        with transaction.atomic():
            # -------- interests
            interests = {n: Interest.objects.create(name=n, icon=i) for n, i in INTERESTS}
            all_interests = list(interests.values())

            # -------- users
            self.stdout.write("👩‍🎓 Creating students…")
            students = []
            for idx, (name, gender, country, uni, course, year) in enumerate(STUDENTS):
                first = name.split()[0]
                email = name.lower().replace(" ", ".").replace("é", "e").replace("'", "") + "@connectera.app"
                chosen = random.sample(all_interests, random.randint(4, 7))
                u = User(
                    email=email, full_name=name, country=country, destination_country="India", university=uni,
                    course=course, year=year, headline=random.choice(HEADLINES),
                    profile_completed=True,
                    date_joined=now - timedelta(days=random.randint(20, 400)),
                    last_seen=now - timedelta(minutes=random.choice([1, 2, 3, 20, 90, 300, 1440, 4000])),
                    profile_visibility=random.choices(["public", "connections"], weights=[9, 1])[0],
                )
                u.bio = random.choice(BIO_TEMPLATES).format(
                    first=first, year=dict(User.YEAR_CHOICES)[year], course=course, uni=uni, country=country,
                    i1=chosen[0].name.lower(), i2=chosen[1].name.lower(), i3=chosen[2].name.lower())
                u.set_password(PASSWORD)
                key = avatar_urls[idx][0]
                if idx % 9 != 4:  # a few students keep the coloured "initials" avatar
                    self.attach(u.avatar, f"{key}.jpg", images.get(key), idx)
                if idx < 12:
                    self.attach(u.cover, f"cover_{idx}.jpg", images.get(f"cover_{idx}"), idx + 100)
                u.save()
                u.interests.set(chosen)
                students.append(u)

            # Demo account = project owner
            marie = User(
                email="marie@connectera.app", full_name="Marie Ngimbis", country="Cameroon",
                destination_country="India", university="Chandigarh University", course="BCA", year=3,
                headline="BCA student • Founder of Connectera 💜",
                bio="Hi, I'm Marie from Cameroon 🇨🇲, BCA student at Chandigarh University. I created Connectera so "
                    "that every student can easily connect, share and grow. I love design, coding, dance and "
                    "discovering new cultures ✨",
                profile_completed=True, last_seen=now,
                date_joined=now - timedelta(days=420),
            )
            marie.set_password(PASSWORD)
            self.attach(marie.avatar, "marie.jpg", images.get(avatar_urls[-1][0]), 999)
            self.attach(marie.cover, "marie_cover.jpg", images.get("cover_11"), 998)
            marie.save()
            marie.interests.set([interests[n] for n in
                                 ["Coding", "Art & Design", "Dance", "Travel", "Languages", "Entrepreneurship"]])

            admin, created = User.objects.get_or_create(
                email="admin@connectera.app",
                defaults={"full_name": "Connectera Admin", "is_staff": True, "is_superuser": True,
                          "profile_completed": True, "country": "India",
                          "university": "Chandigarh University", "course": "Administration"})
            admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@1234")
            if created:
                admin.set_password(admin_password)
                admin.save()

            everyone = students + [marie]

            # -------- connections
            self.stdout.write("🤝 Building the social graph…")
            marie_friends = [students[i] for i in [26, 18, 1, 0, 27, 42, 7, 12, 28, 19, 36, 20, 4, 21]]
            for f in marie_friends:
                Connection.objects.create(requester=f, receiver=marie, status=Connection.ACCEPTED)
            pending_in = [students[i] for i in [31, 23, 45, 9, 34]]
            for p in pending_in:
                Connection.objects.create(requester=p, receiver=marie)
            for p in [students[i] for i in [2, 16]]:
                Connection.objects.create(requester=marie, receiver=p)
            linked = {(c.requester_id, c.receiver_id) for c in Connection.objects.all()}
            for u in students:
                for v in random.sample(students, 7):
                    if u == v or (u.pk, v.pk) in linked or (v.pk, u.pk) in linked:
                        continue
                    linked.add((u.pk, v.pk))
                    Connection.objects.create(requester=u, receiver=v, status=random.choices(
                        [Connection.ACCEPTED, Connection.PENDING], weights=[5, 1])[0])

            # -------- communities
            self.stdout.write("🏘  Creating communities…")
            communities = []
            for i, (name, icon, cat, tagline, desc, ints) in enumerate(COMMUNITIES):
                c = Community(name=name, icon=icon, category=cat, tagline=tagline, description=desc,
                              creator=random.choice(students))
                self.attach(c.image, f"community_{i}.jpg", images.get(f"community_{i}"), 200 + i)
                c.save()
                c.interests.set([interests[n] for n in ints])
                members = [u for u in students if set(u.interests.all()) & set(c.interests.all())]
                c.members.set(random.sample(members, min(len(members), random.randint(12, 30))) + [c.creator])
                communities.append(c)
            by_name = {c.name: c for c in communities}
            for n in ["Coders of CU", "African Students Union", "International Students Hub", "Francophone Corner",
                      "Bollywood Dance Crew", "BCA Batch 2024"]:
                by_name[n].members.add(marie)
            by_name["African Students Union"].members.add(*[u for u in students if u.country not in
                                                            ("India", "Nepal", "Bhutan", "Sri Lanka", "Bangladesh",
                                                             "Afghanistan", "Vietnam", "Iraq", "Iran", "France",
                                                             "Germany")])
            by_name["BCA Batch 2024"].members.add(*[u for u in students if u.course == "BCA"])
            by_name["Francophone Corner"].members.add(*[u for u in students if u.country in
                                                        ("Cameroon", "Senegal", "Ivory Coast", "DR Congo", "Rwanda",
                                                         "Morocco", "France")])

            # -------- events
            self.stdout.write("📅 Creating events…")
            for i, (title, cat, ci, days, hour, dur, loc, online, cap) in enumerate(EVENTS):
                start = timezone.localtime(now + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
                community = communities[ci] if ci is not None else None
                organizer = community.creator if community else random.choice(students)
                e = Event(title=title, category=cat, community=community, organizer=organizer, starts_at=start,
                          ends_at=start + timedelta(hours=dur), location=loc, is_online=online, capacity=cap,
                          description=self.event_description(title, community))
                self.attach(e.image, f"event_{i}.jpg", images.get(f"event_{i}"), 300 + i)
                e.save()
                pool = list(community.members.all()) if community else students
                n = min(len(pool), random.randint(8, 40), cap or 999)
                e.participants.set(random.sample(pool, n))
            for e in Event.objects.filter(title__in=["Newcomers Welcome Meetup", "Tech Career Fair 2026",
                                                     "Africa Day Cultural Night", "Ciné-club : Intouchables",
                                                     "Diwali Mela on Campus"]):
                e.participants.add(marie)

            # -------- posts, likes, comments
            self.stdout.write("📝 Writing posts…")
            for i, (text, with_image) in enumerate(POSTS):
                author = random.choice(everyone[:-1])
                community = None
                if i % 4 == 0:
                    community = random.choice([c for c in communities if c.members.filter(pk=author.pk).exists()]
                                              or [None])
                p = Post(author=author, text=text, community=community,
                         created_at=now - timedelta(hours=i * random.uniform(3, 9) + random.random() * 3))
                if with_image:
                    self.attach(p.image, f"post_{i}.jpg", images.get(f"post_{i}"), 400 + i)
                p.save()
                p.likes.set(random.sample(everyone, random.randint(3, 28)))
                for k in range(random.randint(0, 5)):
                    Comment.objects.create(post=p, author=random.choice(everyone), text=random.choice(COMMENTS),
                                           created_at=p.created_at + timedelta(minutes=random.randint(5, 600)))
            # Marie's own posts
            for text, hours, img in [
                ("Super excited to launch Connectera, a social network made by students for students 💜 "
                 "Connect • Share • Grow. Tell me what you think!", 30, "cover_11"),
                ("Africa Day rehearsals are going so well 💃🏾 Can't wait to show you our choreography!", 80, None),
            ]:
                p = Post(author=marie, text=text, created_at=now - timedelta(hours=hours))
                if img:
                    self.attach(p.image, "marie_post.jpg", images.get(img), 777)
                p.save()
                p.likes.set(random.sample(students, random.randint(15, 30)))
                for c in random.sample(COMMENTS, 4):
                    Comment.objects.create(post=p, author=random.choice(marie_friends), text=c,
                                           created_at=p.created_at + timedelta(minutes=random.randint(5, 300)))

            # -------- conversations
            self.stdout.write("💬 Writing conversations…")
            for idx, msgs in CHATS:
                other = students[idx]
                conv = Conversation.objects.create()
                conv.participants.add(marie, other)
                t = now - timedelta(hours=random.randint(1, 60))
                for j, (mine, text) in enumerate(msgs):
                    t += timedelta(minutes=random.randint(1, 25))
                    last_two_unread = (not mine) and j >= len(msgs) - 2 and idx in (18, 0)
                    Message.objects.create(conversation=conv, sender=marie if mine else other, text=text,
                                           created_at=t, read_at=None if last_two_unread else t)
                conv.updated_at = t
                conv.save()
            for _ in range(25):  # conversations between other students
                a, b = random.sample(students, 2)
                if Conversation.between(a, b, create=False):
                    continue
                conv = Conversation.between(a, b)
                t = now - timedelta(hours=random.randint(1, 200))
                for text in ["Hey! How are you?", "All good, you?", "Ready for the exams?", "Not at all 😂"]:
                    t += timedelta(minutes=random.randint(1, 30))
                    Message.objects.create(conversation=conv, sender=random.choice([a, b]), text=text, created_at=t,
                                           read_at=t)
                conv.updated_at = t
                conv.save()

            # -------- notifications for the demo user
            self.stdout.write("🔔 Generating notifications…")
            marie_post = Post.objects.filter(author=marie).first()

            def note(type_, actor, title, body, link, hours, read):
                Notification.objects.create(user=marie, actor=actor, type=type_, title=title, body=body, link=link,
                                            is_read=read, created_at=now - timedelta(hours=hours))

            for k, p in enumerate(pending_in):
                note("connection_request", p, f"{p.full_name} wants to connect", f"{p.course} · {p.university}",
                     "/connections/?tab=received", 1 + k * 3, k > 2)
            note("message", students[18], f"New message from {students[18].full_name}",
                 "We need more dancers for the final number 😄", "/messages/", 0.5, False)
            note("like", students[0], f"{students[0].full_name} liked your post", marie_post.text[:80],
                 f"/posts/{marie_post.pk}/", 2, False)
            note("comment", students[26], f"{students[26].full_name} commented on your post", "This is amazing! 🔥",
                 f"/posts/{marie_post.pk}/", 4, False)
            note("connection_accepted", students[42], f"{students[42].full_name} accepted your request",
                 "You can now message each other.", f"/students/{students[42].pk}/", 9, True)
            ev = Event.objects.get(title="Newcomers Welcome Meetup")
            note("event_reminder", None, f"Reminder: {ev.title} is coming up",
                 f"{timezone.localtime(ev.starts_at):%a %d %b at %H:%M} · {ev.location}", ev.get_absolute_url(), 3, False)
            ev = Event.objects.get(title="Ciné-club : Intouchables")
            note("event", ev.organizer, f"New event in {ev.community.name}", ev.title, ev.get_absolute_url(), 26, True)
            note("community", None, "New community: Placement Prep", "Crack your dream job.",
                 by_name["Placement Prep"].get_absolute_url(), 50, True)
            note("like", students[1], f"{students[1].full_name} liked your post", marie_post.text[:80],
                 f"/posts/{marie_post.pk}/", 70, True)
            note("system", None, "Welcome to Connectera 💜", "Complete your profile and connect with students.",
                 "/me/", 400, True)

            # a report waiting for moderators
            Report.objects.create(reporter=students[3], target_type="post",
                                  target_id=Post.objects.exclude(author=marie).first().pk,
                                  reason="spam", details="Looks like an advertisement.")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Done! {User.objects.count()} users, {Post.objects.count()} posts, "
            f"{Community.objects.count()} communities, {Event.objects.count()} events, "
            f"{Message.objects.count()} messages, {Connection.objects.count()} connections.\n"
            f"   Demo student : marie@connectera.app / {PASSWORD}\n"
            f"   (every student uses the same password, e.g. aisha.bello@connectera.app)\n"
            f"   Admin        : admin@connectera.app / {admin_password if created else '(unchanged)'}  →  /admin/"))

    @staticmethod
    def event_description(title, community):
        host = f"the {community.name} community" if community else "the Student Council"
        return (f"Join {host} for “{title}”! 🎉\n\n"
                "What to expect:\n• Meet students from different courses and countries\n"
                "• Interactive activities and great vibes\n• Snacks and refreshments\n\n"
                "Free for all Connectera members. Seats are limited — register now to secure your spot!")
