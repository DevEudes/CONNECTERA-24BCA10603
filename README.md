# Connectera — *Connect • Share • Grow*

Réseau social et académique pour étudiants. Un étudiant crée son profil académique, recherche d'autres étudiants, envoie des demandes de connexion, discute en privé, rejoint des communautés et participe à des événements.

**Porteuse du projet :** NGIMBIS MARIE — UID 24BCA10603 — Chandigarh University (BCA)
**Stack :** Python 3.10+ · Django · MySQL (ou SQLite automatiquement) · HTML/CSS/JavaScript

---

## 1. Lancer le projet sur son ordinateur (Windows) — 3 étapes

> 🇬🇧 **Step-by-step guide in simple English: [GETTING_STARTED.md](GETTING_STARTED.md)**

### Prérequis (une seule fois)
1. **Python 3.10 ou plus récent** : https://www.python.org/downloads/
   ⚠️ Pendant l'installation, cochez **« Add python.exe to PATH »**.
2. **Git** : https://git-scm.com/download/win
3. **VS Code** : https://code.visualstudio.com/
4. *(Facultatif)* **MySQL**. S'il n'est pas installé, le projet utilise automatiquement **SQLite** : rien à installer, l'application fonctionne pareil.

### Étape 1 — Récupérer le projet
Dans VS Code : `Ctrl+Shift+P`, puis **Git: Clone**, collez l'adresse du dépôt GitHub, choisissez un dossier et ouvrez-le.
Ou dans un terminal :
```bash
git clone https://github.com/DevEudes/CONNECTERA-24BCA10603.git
cd CONNECTERA-24BCA10603
code .
```
VS Code propose d'installer les extensions recommandées (Python, Django) : acceptez.

### Étape 2 — Installer (une seule fois, 2 à 3 minutes)
Dans le terminal de VS Code (`Ctrl+ù` ou *Terminal → New Terminal*) :
```bash
.\setup.bat
```
*(Ou double-cliquez sur `setup.bat` dans l'explorateur Windows.)*

Le script fait tout tout seul :
- il crée l'environnement Python et installe les dépendances ;
- il génère le fichier de configuration `.env` ;
- il se connecte à MySQL, ou bascule sur SQLite si MySQL n'est pas installé (il suffit d'appuyer sur Entrée quand il le demande) ;
- il crée les tables et charge les données de démo.

### Étape 3 — Lancer l'application
```bash
.\run.bat
```
Le navigateur s'ouvre sur **http://127.0.0.1:8000** 🎉
Dans VS Code, on peut aussi simplement appuyer sur **F5** (configuration « ▶ Run Connectera »).
Pour arrêter le serveur : `Ctrl+C` dans le terminal.

### Raccourcis VS Code
*Terminal → Run Task…* propose :
- **Connectera: 1. Install** : installation
- **Connectera: 2. Run the app** : lancement
- **Connectera: Reset demo data** : remet les données de démo à zéro
- **Connectera: Run tests** : lance les tests

### Sur macOS / Linux
`./setup.sh`, puis `./run.sh`.

### Utiliser MySQL plutôt que SQLite
Ouvrez `.env` et renseignez `DB_USER` et `DB_PASSWORD`. Mettez un `#` devant la ligne `DB_ENGINE=sqlite` pour la désactiver, puis relancez `setup.bat`. La base `connectera` est créée automatiquement.

### En cas de problème
| Message | Solution |
|---|---|
| `Python is not installed` / `'py' n'est pas reconnu` | Réinstallez Python en cochant **Add python.exe to PATH**, puis fermez et rouvrez VS Code |
| `l'exécution de scripts est désactivée` (PowerShell) | Utilisez `.\setup.bat` (pas `.ps1`) ou ouvrez un terminal **Command Prompt** dans VS Code |
| `That port is already in use` | Un serveur tourne déjà : fermez l'autre terminal, ou lancez `.venv\Scripts\python manage.py runserver 8001` |
| Page sans style ou sans images | Vérifiez que le serveur a bien été lancé avec `run.bat` (mode développement) |

---

## 2. Comptes de démonstration

| Rôle | E-mail | Mot de passe |
|---|---|---|
| Étudiante (compte principal) | `marie@connectera.app` | `Demo@1234` |
| N'importe quel autre étudiant | ex. `aisha.bello@connectera.app`, `jean-paul.mbarga@connectera.app` | `Demo@1234` |
| Administrateur (`/admin/`) | `admin@connectera.app` | `Admin@1234` |

**Données générées automatiquement par l'installation :** 47 étudiants de 22 pays avec photos, 14 communautés, 18 événements (à venir et passés), 32 publications avec images, likes et commentaires, 300+ connexions, des conversations et des notifications.
Le compte de Marie a déjà des connexions, des demandes reçues, des messages non lus et des notifications, ce qui permet de tester tout de suite.

La tâche *Reset demo data* (ou `python manage.py seed`) **réinitialise** les données de démo à tout moment. Les images sont stockées dans `core/seed_assets/`, donc la commande fonctionne même hors-ligne.

### Tester l'inscription
1. Cliquez sur *Create account* et remplissez le formulaire.
2. Vous arrivez directement sur *Complete your profile* (pas de code de vérification).
3. Complétez le profil, choisissez au moins 3 centres d'intérêt, et c'est terminé.

**Mot de passe oublié :** un lien sécurisé, valable 1 heure et utilisable une seule fois, est envoyé par e-mail. En local, l'e-mail s'affiche dans le terminal où tourne `runserver` ; pour envoyer de vrais e-mails, configurez la section SMTP de `.env`.

### Tester le chat en temps réel
Ouvrez deux navigateurs (ou une fenêtre privée), connectez-vous avec `marie@connectera.app` d'un côté et `aisha.bello@connectera.app` de l'autre, puis ouvrez leur conversation. Les messages apparaissent automatiquement en moins de 3 secondes.

---

## 3. Fonctionnalités (MVP du cahier des charges)

| Module | Implémenté |
|---|---|
| **Onboarding** | Splash screen animé, 3 écrans (*Connect with Amazing People*, *Share your Moments*, *Get Inspired Every Day*), swipe sur mobile |
| **Authentification** | Inscription (sans OTP : accès direct au profil), connexion (« remember me »), mot de passe oublié avec lien sécurisé par e-mail (valable 1 h, à usage unique), confirmation de déconnexion, rate limiting |
| **Profil** | Photo, couverture, nom, titre, pays actuel et pays d'études, université, filière, année, bio, centres d'intérêt, jauge de complétude, modification |
| **Découverte** | Recherche par nom, université, filière et intérêts ; 5 filtres ; cartes de profil ; **recommandations par score** (intérêts communs, même université, même filière…) |
| **Connexions** | Envoyer, accepter, refuser, annuler, retirer ; doublons impossibles ; blocage et déblocage ; connexions en commun |
| **Feed** | Publications texte et image, likes (AJAX), commentaires (AJAX), suppression, signalement, onglets *For you* / *My network*, chargement progressif |
| **Messagerie** | Liste des conversations, recherche, chat individuel, lu/non lu (« Seen »), statut en ligne, envoi avec Entrée, rafraîchissement automatique |
| **Communautés** | Recommandées, mes communautés, recherche, catégories, rejoindre/quitter, page détail (membres, événements, discussion), création |
| **Événements** | À venir, mes événements, passés, détail (date, heure, lieu, organisateur, participants, amis inscrits), inscription et annulation, capacité, création |
| **Notifications** | Demande et acceptation de connexion, message, like, commentaire, nouvelle communauté, nouvel événement, rappel d'événement (24 h avant) ; regroupées par jour ; tout marquer comme lu ; badges mis à jour automatiquement |
| **Paramètres** | Compte et mot de passe, confidentialité (visibilité du profil, qui peut m'écrire, afficher l'e-mail), préférences de notifications, apparence (**mode sombre**) et langue, utilisateurs bloqués, aide et FAQ, formulaire de support, désactivation et suppression du compte |
| **Administration** | Django Admin : utilisateurs (suspendre/réactiver), communautés, événements, publications, **signalements** (revu/rejeté), statistiques par liste |

### Règles et sécurité (§11 et §13 du cahier des charges)
- Un seul compte par e-mail (insensible à la casse).
- Mots de passe hachés (PBKDF2-SHA256), jamais stockés en clair.
- Toutes les routes privées sont protégées : connexion, e-mail vérifié et profil complété sont exigés.
- Un utilisateur ne peut modifier que son propre profil, et ne peut supprimer que ses propres contenus.
- Un utilisateur bloqué ne peut ni voir le profil, ni envoyer de demande, ni écrire.
- Rate limiting sur la connexion et la demande de réinitialisation du mot de passe.
- Protection CSRF sur tous les formulaires ; ORM Django (pas d'injection SQL) ; échappement automatique des templates (pas de XSS) ; redirections `next` vérifiées (pas d'open redirect).
- Uploads limités aux images JPG, PNG, WEBP et GIF de 5 Mo maximum.
- Secrets dans `.env`, qui est exclu de Git par `.gitignore`.

### Interface
- Identité violette et blanche, dégradés légers, composants arrondis, police *Plus Jakarta Sans*.
- **Mobile-first** : barre de navigation du bas (Home, Search, Create, Chats, Profile) sur mobile ; barre latérale et colonne de recommandations sur ordinateur.
- États vides, toasts de confirmation, confirmations avant les actions destructives, mode sombre, navigation au clavier.

---

## 4. Structure du projet

```
connectera/
├── GETTING_STARTED.md          ← guide pas à pas (anglais) pour lancer le projet
├── setup.bat / run.bat         ← installation et lancement (Windows)
├── setup.sh / run.sh           ← installation et lancement (macOS/Linux)
├── setup_project.py            ← script d'installation automatique
├── manage.py
├── requirements.txt
├── .vscode/                    ← F5 pour lancer, tâches, extensions recommandées
├── .env.example                 ← variables d'environnement documentées
├── connectera/                  ← configuration Django (settings, urls)
├── core/                        ← l'application (une seule, pour rester simple)
│   ├── models.py                ← User, Interest, Connection, Block, Post, Comment,
│   │                              Conversation, Message, Community, Event, Notification, Report
│   ├── forms.py                 ← formulaires et validations
│   ├── urls.py                  ← toutes les routes
│   ├── views/                   ← une vue par module
│   │   ├── auth.py              (onboarding, inscription, connexion, mot de passe oublié)
│   │   ├── profile.py           (complete profile, intérêts, profils)
│   │   ├── feed.py              (home, posts, likes, commentaires, signalements)
│   │   ├── network.py           (recherche, connexions, blocage)
│   │   ├── chat.py              (messagerie)
│   │   ├── communities.py · events.py · notifications.py · settings.py
│   ├── recommendations.py       ← moteur de recommandations par score
│   ├── utils.py                 ← contrôle d'accès, notifications, rate limit
│   ├── admin.py                 ← dashboard administrateur
│   ├── tests.py                 ← 33 tests fonctionnels (§14)
│   ├── management/commands/seed.py ← données de démonstration
│   └── seed_assets/             ← images de démo en cache
├── templates/                   ← pages HTML (Django templates)
└── static/                      ← css/app.css, js/app.js, icônes
```

---

## 5. Tests

```bash
python manage.py test core
```
Les 33 tests couvrent le tableau §14 du cahier des charges : inscription valide et e-mail existant, login, mot de passe oublié (lien e-mail, lien invalide, usage unique), profil, recherche, demande de connexion (statut *pending*, doublons), acceptation, chat, permissions de messagerie, blocage, communauté, événement (y compris complet), notifications, accès refusé sans authentification, et protection des données d'autrui.

---

## 6. Choix techniques et écarts avec le cahier des charges

| Cahier des charges | Choix retenu | Pourquoi |
|---|---|---|
| React, Node/Express, MongoDB | **Django + templates HTML + MySQL** | Demande explicite du projet : Python, Django, MySQL, structure simple |
| JWT | Sessions Django sécurisées (cookie HttpOnly) | Standard et plus sûr pour une application web rendue côté serveur |
| Socket.IO | Rafraîchissement automatique toutes les 3 s (*polling*) | Aucun serveur supplémentaire (Redis, WebSocket) ; évolutif plus tard vers Django Channels |
| Cloudinary/S3 | Stockage local `media/` | Suffisant pour le MVP ; il suffit de changer le `STORAGE` Django pour passer au cloud |
| Argon2 | PBKDF2-SHA256 (Django par défaut) | Aucune dépendance supplémentaire ; Argon2 peut être activé avec `pip install argon2-cffi` |

**Retiré à la demande de la porteuse du projet :** la vérification OTP par code à 6 chiffres.

**Prévu pour une version future (hors MVP) :** connexion Google et Apple, 2FA, images et fichiers dans le chat, notifications push, fonctionnalités IA (§15). Le moteur `recommendations.py` constitue déjà la première étape « scoring/règles » recommandée par le cahier des charges.

---

*CONNECTERA | NGIMBIS MARIE | 24BCA10603*
