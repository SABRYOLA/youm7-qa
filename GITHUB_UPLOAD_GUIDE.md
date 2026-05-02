# GitHub Upload Guide
## دليل رفع المشروع إلى GitHub

A beginner-friendly walkthrough for publishing this project to GitHub. If
you've never used Git before, follow every step in order — copy and paste
the commands exactly.

دليل خطوة بخطوة لرفع المشروع إلى GitHub. إذا كانت هذه أول مرة تستخدم
فيها Git، اتبع كل الخطوات بالترتيب وانسخ الأوامر كما هي.

---

## Step 1 — Create a GitHub Account (skip if you already have one)

1. Open <https://github.com/signup> in your browser.
2. Enter an email, password, and pick a username.
3. Verify your email.
4. Choose the **free plan** when prompted.

---

## Step 2 — Install Git

| OS | Where to download |
|----|-------------------|
| Windows | <https://git-scm.com/download/win> — accept all defaults during install. |
| macOS   | `brew install git` (if you have Homebrew) — or install Xcode Command Line Tools: `xcode-select --install`. |
| Linux   | `sudo apt install git` (Debian/Ubuntu) or `sudo dnf install git` (Fedora). |

Verify it installed:

```bash
git --version
```

You should see something like `git version 2.43.0`.

---

## Step 3 — Configure Git (run once, ever)

Tell Git who you are. Use the same email you used for your GitHub account.

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

---

## Step 4 — Create a New Repository on GitHub

1. Go to <https://github.com/new>.
2. **Repository name**: `youm7-qa`
3. **Description**: `Arabic QA system for اليوم السابع — Selenium + FAISS + FastAPI`
4. **Visibility**: **Public** (so others can see your work).
5. **Important**: do **NOT** tick *"Add a README file"*, *"Add .gitignore"*,
   or *"Choose a license"*. We already have all three.
6. Click **Create repository**.

You'll land on a page that says *"Quick setup"* — keep it open, you'll
copy the repo URL from it in Step 5.

---

## Step 5 — Initialize the Local Repo and Push

Open a terminal **inside your project folder** (the folder that contains
`README.md`, `youm7_scraper.py`, etc.). Run these commands one by one:

```bash
# 1. Initialize a new git repo locally
git init

# 2. Stage every file (except those ignored by .gitignore)
git add .

# 3. Make the first commit
git commit -m "Initial commit: Youm7 Arabic QA System"

# 4. Rename the default branch to "main" (GitHub's default)
git branch -M main

# 5. Connect this local repo to your GitHub repo.
#    Replace YOUR_USERNAME with your actual GitHub username.
git remote add origin https://github.com/YOUR_USERNAME/youm7-qa.git

# 6. Upload everything
git push -u origin main
```

The first push will ask you to authenticate — either with a browser pop-up
(GitHub's recommended flow) or with a **personal access token** (paste it
when prompted instead of your password). To create a token:
<https://github.com/settings/tokens> → *Generate new token (classic)* → tick
**`repo`** → copy the token.

---

## Step 6 — Verify the Upload

1. Open `https://github.com/YOUR_USERNAME/youm7-qa` in your browser.
2. You should see all the project files.
3. Click `README.md` — it should render with badges, the architecture
   diagram, and the tech-stack table.
4. Confirm the `output/` folder is present and only contains `.gitkeep`.
   (The actual `.json` / `.faiss` outputs are gitignored — that's correct.)

---

## Step 7 — Add Repository Topics (helps discoverability)

1. On your repo page, click the **⚙️ gear icon** next to the *About* box
   on the right side.
2. In **Topics**, add these tags one at a time:
   ```
   arabic-nlp
   question-answering
   faiss
   fastapi
   selenium
   python
   nlp
   arabic
   sentence-transformers
   information-retrieval
   ```
3. Optionally, set the **Website** field to `http://localhost:8000/docs`
   (or your deployed URL once you have one).
4. Click **Save changes**.

Topics help your repo show up in GitHub's search and "Explore" sections.

---

## Step 8 — Pin the Repo to Your Profile

1. Go to your GitHub profile page (`https://github.com/YOUR_USERNAME`).
2. Click **Customize your pins** under your bio.
3. Tick **`youm7-qa`** and any other showcase repos.
4. Click **Save pins**.

This makes the project the first thing recruiters and classmates see when
they visit your profile.

---

## Day-to-Day Workflow

After you make changes, the loop is:

```bash
git status                    # see what changed
git add .                     # stage everything
git commit -m "Fix: typo in README"
git push                      # upload
```

For larger features, work on a branch:

```bash
git checkout -b feature/redis-cache    # create + switch to branch
# ... edit, commit, push ...
git push -u origin feature/redis-cache
# Then on GitHub, click "Compare & pull request"
```

---

## Common Errors and Fixes

### ❌ `remote origin already exists`

You ran `git remote add origin ...` more than once. To replace the existing
URL:

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/youm7-qa.git
```

Or to start fresh:

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/youm7-qa.git
```

---

### ❌ `failed to push — rejected (non-fast-forward)`

GitHub has commits your local copy doesn't (often because you ticked
*"Add a README"* during repo creation — see Step 4). Pull first, then push:

```bash
git pull origin main --rebase
git push
```

If you get a merge conflict, open the conflicted file, resolve it manually,
then:

```bash
git add <file>
git rebase --continue
git push
```

---

### ❌ `file too large` (over 100 MB)

GitHub rejects files over 100 MB. The most likely culprits are
`output/youm7_index.faiss` or a model cache. The repo's `.gitignore`
already excludes `*.faiss`, but if you accidentally committed it before
the `.gitignore` was in place:

```bash
git rm --cached output/youm7_index.faiss
git rm --cached -r .venv/         # if you committed your virtualenv
git rm --cached -r __pycache__/   # if you committed bytecode
git commit -m "Remove large files from tracking"
git push
```

If a single commit pushed a huge file and now the whole push is blocked,
you may need to rewrite history with `git filter-repo` — see
<https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>.

---

### ❌ `Authentication failed`

GitHub stopped accepting passwords for git operations in 2021. You must
use either:

- A **personal access token** (PAT) — generate one at
  <https://github.com/settings/tokens> with the **`repo`** scope, then
  paste it in place of your password when git asks.
- The **GitHub CLI**: `gh auth login` (download from <https://cli.github.com/>).
- An **SSH key**: see
  <https://docs.github.com/en/authentication/connecting-to-github-with-ssh>.

---

### ❌ `bad credentials` on subsequent pushes

Windows Git Credential Manager may have cached a stale token. Clear it:

```bash
# Windows
git credential-manager-core erase
# (then start a fresh push, it will re-prompt)

# macOS
git credential-osxkeychain erase
host=github.com
protocol=https
# (press Ctrl+D)

# Linux
git config --global --unset credential.helper
```

---

## Optional — Add a Description with Emoji

A nice-looking *About* section helps your repo stand out. On the repo page:

1. Click the gear icon next to *About*.
2. Description: `🇪🇬 Arabic QA system over اليوم السابع — Selenium + FAISS + FastAPI`
3. Tick **Use your GitHub Pages website** if you ever deploy a demo.

---

## Optional — Add a GitHub Pages Demo Link

If you screenshot or screen-record `index.html`, you can host the static
HTML on GitHub Pages:

1. In your repo, go to **Settings** → **Pages**.
2. Source: **Deploy from a branch**, branch **main**, folder **/ (root)**.
3. Click **Save**.
4. After ~1 minute, your `index.html` will be live at
   `https://YOUR_USERNAME.github.io/youm7-qa/`.

(Note: the live page only works as a demo if you also deploy the API
somewhere — local-only `index.html` will show *"غير متصل"* on GitHub Pages.)

---

## You're Done! 🎉

Your project is on GitHub, properly documented, and ready to share. Drop
the URL on your CV, in your portfolio, in the course submission form —
wherever it needs to go.

مبروك! المشروع الآن على GitHub، جاهز للمشاركة.
