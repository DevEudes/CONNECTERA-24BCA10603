# Getting started with Connectera (Windows + VS Code)

This guide takes you from **zero to the app running in your browser**.
It takes about **10 minutes**. You only do steps 1 to 5 **once**; after that, starting the app is just step 6.

---

## Step 1 — Check that Python is installed

1. Open **VS Code**.
2. In the top menu, click **Terminal → New Terminal**. A panel opens at the bottom of the window.
3. Type this and press **Enter**:
   ```
   py --version
   ```
   - ✅ You see something like `Python 3.12.4` → go to Step 2.
   - ❌ You see an error → install Python:
     1. Go to https://www.python.org/downloads/ and click **Download Python**.
     2. Run the installer. **Important:** on the first screen, tick the box **"Add python.exe to PATH"**, then click **Install Now**.
     3. **Close VS Code completely and open it again**, then repeat point 3 above.

## Step 2 — Check that Git is installed

In the same terminal, type and press **Enter**:
```
git --version
```
- ✅ You see something like `git version 2.45.1` → go to Step 3.
- ❌ You see an error → download Git from https://git-scm.com/download/win, install it (keep all the default options), then **close and reopen VS Code**.

## Step 3 — Download the project into VS Code

1. Press **Ctrl + Shift + P**. A search bar opens at the top.
2. Type **`Git: Clone`** and press **Enter**.
3. Paste this address and press **Enter**:
   ```
   https://github.com/DevEudes/CONNECTERA-24BCA10603.git
   ```
   (If VS Code asks you to sign in to GitHub, click **Allow** and sign in.)
4. Choose a folder where the project will be saved, for example **Documents**, and click **Select as Repository Destination**.
5. When the download is finished, click **Open** in the small window at the bottom right.
6. If VS Code asks *"Do you trust the authors of the files in this folder?"*, click **Yes, I trust the authors**.

👉 You now see the project files on the left side of VS Code.

## Step 4 — Install the recommended extensions

A small window appears at the bottom right: *"Do you want to install the recommended extensions?"*
Click **Install**. This installs the Python and Django tools for VS Code.

(If you missed it: press **Ctrl + Shift + X**, type `@recommended`, and click **Install** on each extension.)

## Step 5 — Install the project (only the first time)

1. Open a terminal: **Terminal → New Terminal**.
2. Type this and press **Enter**:
   ```
   .\setup.bat
   ```
3. Wait 2 to 3 minutes. The script installs everything automatically and fills the app with demo data.
4. If it asks for a **MySQL password**:
   - you **don't** have MySQL → just press **Enter** (the app will use a built-in database, nothing to install);
   - you **do** have MySQL → type your MySQL password and press **Enter**.
5. It's finished when you see:
   ```
   ✅ Installation complete!
   ```
   Then press any key to close the message.

## Step 6 — Start the app

In the terminal, type and press **Enter**:
```
.\run.bat
```
After a few seconds, your browser opens the app at **http://127.0.0.1:8000** 🎉

> Another way: press **F5** in VS Code, then open http://127.0.0.1:8000 in your browser.

**Log in with the demo account:**

| E-mail | Password |
|---|---|
| `marie@connectera.app` | `Demo@1234` |

You can also click **Create account** to make your own account.
Every demo student uses the password `Demo@1234`, for example `aisha.bello@connectera.app`. To test the chat, log in as Marie in a normal window and as Aisha in a private window.

## Step 7 — Stop the app

Click in the terminal and press **Ctrl + C**. If it asks *"Terminate batch job (Y/N)?"*, type **Y** and press **Enter**.

**Next time**, open the project in VS Code (**File → Open Recent**) and only do **Step 6**.

---

## Get the latest version of the project

When the project is updated on GitHub:
1. Click the **Source Control** icon on the left side of VS Code (it looks like a branch: ⑂).
2. Click the **⋯** menu, then **Pull**.
3. Start the app again with `.\run.bat`. If it does not start, run `.\setup.bat` once more.

---

## If something goes wrong

| What you see | What to do |
|---|---|
| `'py' is not recognized…` | Python is not installed or "Add to PATH" was not ticked. Redo Step 1, then close and reopen VS Code. |
| `'git' is not recognized…` | Install Git (Step 2), then close and reopen VS Code. |
| `setup.bat is not recognized` | Make sure you typed `.\setup.bat` with the `.\` at the start, and that VS Code opened the project folder (you should see `setup.bat` in the file list on the left). |
| `running scripts is disabled on this system` | Use the `.bat` files exactly as written above (not `.ps1`). |
| `Error: That port is already in use` | The app is already running in another terminal. Close that terminal, or open http://127.0.0.1:8000 directly. |
| The browser shows *"This site can't be reached"* | The server is not running: run `.\run.bat` and keep the terminal open while you use the app. |
| You want to reset the demo data | **Terminal → Run Task… → Connectera: Reset demo data** |

Still stuck? Copy the red error message from the terminal and send it to the project owner.
