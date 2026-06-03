# StegChat — Implementation Guide

A single-page global chat with steganographic image messaging. Built as a student project: maximum simplicity, manual deploy, one FastAPI service on Cloud Run + Firestore + Cloud Storage.

---

## What it does

- One global chat room. Every whitelisted user sees the same conversation.
- Username + password login. Admin adds users on a hidden `/admin` page.
- Text messages and image messages.
- When sending an image, the user can press a key icon and type a passphrase + secret message. In the browser, the secret is XOR-encrypted with a SHA-256 of the passphrase, then bit-embedded into the image's pixels (LSB steganography). The image looks identical afterwards. **The passphrase and the plaintext never leave the browser.**
- Stego images render in the chat with **square** corners; plain images with **rounded** corners. Everyone sees the difference, but only someone who knows the passphrase can recover the secret.
- To decode: tap the image to open it full-screen, then tap the top-left corner and then the bottom-right corner within 5 seconds. A passphrase prompt appears; correct passphrase → secret shown; wrong → "wrong passphrase". Decoding is entirely client-side too.

---

## Architecture

```
                  ┌────────────────────────┐
   browser  ───── │  Cloud Run (FastAPI)   │ ───── Firestore (users, messages)
   stego.js       │  Jinja2 + Bootstrap    │ ───── Cloud Storage (PNG bytes)
   app.js         │  bcrypt + cookies      │
                  └────────────────────────┘
```

The server never touches pixel data or encryption keys. The browser does:
- image resize (canvas)
- PNG encoding (`canvas.toBlob`)
- SHA-256 of the passphrase (Web Crypto, built-in)
- XOR over a typed array (one `for` loop)
- LSB embedding/extraction (two `for` loops on `Uint8ClampedArray`)

No Firebase Auth, no Firebase JS SDK, no websockets. Real-time = the client polls `/api/messages?since=<ts>` every 2 seconds. For <50 users that's well within Firestore's free tier and removes a whole category of complexity.

---

## Tech stack

- **Backend:** Python 3.11, FastAPI, Jinja2, Uvicorn
- **Auth:** bcrypt (passwords), Starlette `SessionMiddleware` (signed cookies)
- **GCP:** Firestore (native mode), Cloud Storage, Cloud Run, Artifact Registry
- **Frontend:** Server-rendered Jinja, Bootstrap 5 via CDN, ~250 lines of vanilla JS split across two ES modules

No Pillow, no NumPy, no `cryptography` library. The server is literally just CRUD + a bcrypt check.

---

## Final file layout

```
stegchat/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app, route wiring
│   ├── auth.py            # login, sessions, password hashing, current_user dep
│   ├── db.py              # Firestore client + helpers
│   ├── storage.py         # Cloud Storage client + helpers
│   ├── routes/
│   │   ├── pages.py       # GET / (chat), GET /login, GET /admin, password change
│   │   ├── messages.py    # POST /api/messages/*, GET /api/messages
│   │   ├── images.py      # POST /api/images, GET /img/{id}
│   │   └── admin.py       # POST /admin/users, /admin/users/{u}/delete
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── chat.html
│   │   ├── admin.html
│   │   └── change_password.html
│   └── static/
│       ├── app.js         # UI, polling, send, paste/pick, overlay/gesture
│       ├── stego.js       # SHA-256, XOR, LSB embed/extract
│       └── app.css
├── scripts/
│   └── bootstrap_admin.py # one-shot: create the first admin user
├── requirements.txt
├── Dockerfile
├── .env.example
├── .gcloudignore
├── .gitignore
└── install.md
```

---

## Prerequisites (one-time)

You need on your machine:

- Python 3.11+
- `gcloud` CLI (`https://cloud.google.com/sdk/docs/install`) and run `gcloud init`
- A Google account with billing enabled (Cloud Run free tier covers this project)
- `docker` (optional — Cloud Run can build from source without it)

GCP-side, do this once:

1. Create a GCP project: `gcloud projects create stegchat-XXXX` (pick something unique). Set as default: `gcloud config set project stegchat-XXXX`.
2. Enable APIs:
   ```bash
   gcloud services enable run.googleapis.com \
       firestore.googleapis.com \
       storage.googleapis.com \
       artifactregistry.googleapis.com \
       cloudbuild.googleapis.com
   ```
3. Create a Firestore database in **native mode**:
   ```bash
   gcloud firestore databases create --location=europe-west3
   ```
4. Create a Cloud Storage bucket (name must be globally unique):
   ```bash
   gcloud storage buckets create gs://stegchat-XXXX-images --location=europe-west3
   ```
5. For local development, create a service account key:
   ```bash
   gcloud iam service-accounts create stegchat-dev
   gcloud projects add-iam-policy-binding stegchat-XXXX \
       --member="serviceAccount:stegchat-dev@stegchat-XXXX.iam.gserviceaccount.com" \
       --role="roles/datastore.user"
   gcloud projects add-iam-policy-binding stegchat-XXXX \
       --member="serviceAccount:stegchat-dev@stegchat-XXXX.iam.gserviceaccount.com" \
       --role="roles/storage.objectAdmin"
   gcloud iam service-accounts keys create ./sa-key.json \
       --iam-account=stegchat-dev@stegchat-XXXX.iam.gserviceaccount.com
   ```
   Keep `sa-key.json` out of git. Reference it in `.env` as `GOOGLE_APPLICATION_CREDENTIALS=/abs/path/to/sa-key.json`.

---

# Implementation steps

Each step ends with a **prompt for coding agent** — paste it into Claude Code / Cursor / etc. and it should produce that step's code. After each step the app should be runnable, just with fewer features than the next.

---

## Step 1 — Skeleton app that says hello

**Goal:** FastAPI app running locally on port 8080, renders a Jinja page that says "StegChat".

Files: `app/main.py`, `app/templates/base.html`, `app/templates/chat.html`, `requirements.txt`, `.env.example`, `.gitignore`.

`requirements.txt` (initial — and this is almost the full final list):
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
jinja2==3.1.*
python-multipart==0.0.*
itsdangerous==2.2.*
python-dotenv==1.0.*
```

Run locally:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

**Prompt for coding agent:**

> Create a minimal FastAPI app at `app/main.py` that:
> - mounts Jinja2 templates from `app/templates/` and a static dir at `app/static/`
> - serves `GET /` which renders `chat.html` extending `base.html`
> - loads `.env` via `python-dotenv` at startup
>
> Create `app/templates/base.html` with: HTML5 doctype, viewport meta, Bootstrap 5 CSS + JS from `cdn.jsdelivr.net`, a centered container, and `{% block content %}{% endblock %}`.
>
> Create `app/templates/chat.html` extending base with just an `<h1>StegChat</h1>` for now.
>
> Create `.gitignore` (ignore `.venv`, `__pycache__`, `*.pyc`, `.env`, `sa-key.json`, `*.egg-info`).
>
> Create `.env.example` with placeholder lines for: `SESSION_SECRET`, `GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT`, `GCS_BUCKET`.

---

## Step 2 — Firestore connection + bootstrap admin

**Goal:** A script `scripts/bootstrap_admin.py` that creates the first admin user in Firestore. Run it once per fresh install.

Firestore schema (final, for reference):
```
users/{username}        # doc id = username (lowercase)
  username: str
  email: str
  password_hash: str    # bcrypt
  is_admin: bool
  created_at: timestamp
  must_change_password: bool

messages/{auto_id}
  sender: str           # username
  created_at: timestamp # server-set
  kind: "text" | "image"
  text: str | null
  image_id: str | null  # GCS object name in the bucket
  has_secret: bool      # only meaningful when kind=="image", set by sender's request
```

Add to `requirements.txt`:
```
google-cloud-firestore==2.19.*
bcrypt==4.2.*
```

**Prompt for coding agent:**

> Create `app/db.py`:
> - `db = google.cloud.firestore.Client(project=os.environ["GCP_PROJECT"])` at module level
> - functions: `get_user(username) -> dict | None`, `create_user(username, email, password_hash, is_admin=False)`, `delete_user(username)`, `list_users() -> list[dict]`
> - `username` is always lowercased before use; doc id == username
>
> Create `app/auth.py` with `hash_password(plain: str) -> str` (bcrypt.hashpw with fresh salt, default cost) and `verify_password(plain, hashed) -> bool`. Store the hash as a UTF-8 string in Firestore.
>
> Create `scripts/bootstrap_admin.py` — a standalone script that:
> - reads `ADMIN_EMAIL` and `ADMIN_PASSWORD` from CLI args (or prompts via `input()` / `getpass`)
> - uses email's local part as the username (e.g. `alice@x.com` → `alice`)
> - aborts if the user already exists
> - creates the user with `is_admin=True`, `must_change_password=False`
>
> Run: `python scripts/bootstrap_admin.py alice@x.com 'temp-pw'`.

---

## Step 3 — Login form + session cookie

**Goal:** Users can log in. `GET /login` renders a form, `POST /login` checks credentials, sets a signed-cookie session, redirects to `/`. `GET /` redirects to `/login` if not logged in.

`SESSION_SECRET` is a random 32-byte string. Generate once with `python -c "import secrets; print(secrets.token_hex(32))"`. Put in `.env`.

**Prompt for coding agent:**

> Add `starlette.middleware.sessions.SessionMiddleware` to `app/main.py` using `os.environ["SESSION_SECRET"]`, `same_site="lax"`, `https_only=True` (we'll override that locally via env var).
>
> Create `app/templates/login.html`: a centered Bootstrap form with username, password, submit. Show a flash error if `?error=` is in the query string. Heading: "Sign in to StegChat".
>
> In `app/auth.py` add:
> - `def current_user(request: Request) -> dict`: reads `request.session["username"]`, looks up the user, raises `HTTPException(401)` if missing. Used as a FastAPI `Depends`.
> - `def require_admin(user = Depends(current_user)) -> dict`: raises `HTTPException(403)` if `not user["is_admin"]`.
>
> Create `app/routes/pages.py`:
> - `GET /login` → render `login.html`
> - `POST /login` → form data `username`, `password`; verify with bcrypt; on success `request.session["username"] = username` and `RedirectResponse("/", 303)`; on failure `RedirectResponse("/login?error=1", 303)`
> - `POST /logout` → clear session, redirect to `/login`
> - `GET /` → if no session, redirect to `/login`; else render `chat.html` passing `user` to the template
>
> Wire `pages.router` into `app/main.py`.

Test: bootstrap an admin, run `uvicorn`, log in, see `chat.html` with "Hello, alice".

---

## Step 4 — Admin page: add and remove users

**Goal:** `GET /admin` shows a list of users + a form to add one. Only admins can see it.

**Prompt for coding agent:**

> Create `app/templates/admin.html` extending base:
> - Bootstrap table of users (username, email, is_admin, created_at, delete button)
> - below it, a form `POST /admin/users` with fields `username`, `email`, `password`, `is_admin` (checkbox)
> - flash message if `?ok=1` or `?error=...` query param is present
>
> Create `app/routes/admin.py`:
> - `GET /admin` (admin-only) → render `admin.html` with `users = list_users()`
> - `POST /admin/users` (admin-only, form-encoded) → validate non-empty, normalize username to lowercase, check no duplicate, hash password, create user with `must_change_password=True`. Redirect `/admin?ok=1` or `/admin?error=<msg>`.
> - `POST /admin/users/{username}/delete` (admin-only) → delete user; never allow deleting yourself
>
> Wire `admin.router` into `main.py`.
>
> In `chat.html`, if `user.is_admin`, show a small "Admin" link in the top right. Also show a "Logout" button (form POST to `/logout`).

---

## Step 5 — User can change own password

**Goal:** A "Change password" page anyone can use, accessible from the chat header. Force a change on first login if `must_change_password=True`.

**Prompt for coding agent:**

> Create `app/templates/change_password.html`: form with `current_password`, `new_password`, `confirm_password`.
>
> Add to `app/routes/pages.py`:
> - `GET /change-password` (logged-in) → render the template
> - `POST /change-password` → verify current, ensure new == confirm and length ≥ 8, update `password_hash` and set `must_change_password=False`; redirect `/` with a flash.
>
> Add middleware (or a check at the top of `GET /`) that redirects to `/change-password` if `user["must_change_password"]` is true.
>
> In `chat.html`, add a "Change password" link in the header next to Logout.

---

## Step 6 — Text messages: send + poll

**Goal:** Logged-in user types text into the bottom input, presses send, message appears. Other open browsers see new messages within 2 seconds.

The chat shell is built here; subsequent steps add image features.

**Prompt for coding agent:**

> In `app/db.py`, add:
> - `add_text_message(sender: str, text: str) -> dict` → creates a doc with `created_at=firestore.SERVER_TIMESTAMP`, returns `{id, sender, text, kind: "text", created_at_iso}`
> - `get_messages_since(iso_ts: str | None, limit=100) -> list[dict]` → messages with `created_at > iso_ts` (or the most recent `limit` if `iso_ts is None`), ordered ascending. Each result includes `id`, `sender`, `kind`, `text`, `image_id`, `has_secret`, `created_at_iso`.
>
> Create `app/routes/messages.py`:
> - `POST /api/messages/text` (logged-in, JSON `{text: str}`) → strip, reject empty or >2000 chars, return the message dict
> - `GET /api/messages` (logged-in, `?since=<iso>`) → return `{messages: [...]}`
>
> Wire `messages.router` into `main.py`.
>
> Rewrite `app/templates/chat.html`:
> - Bootstrap flex column filling viewport: header (logo + username + Admin? + Change password + Logout) | scrollable messages area | input row
> - Messages area: `#messages` div the JS fills. Each message is a row with a bubble — right-aligned + colored if `sender == window.ME`, left-aligned + plain otherwise. Sender name above left-side bubbles.
> - Input row: text input `#text-input`, image button `#btn-image`, key button `#btn-key` (both disabled until later steps), send button `#btn-send`.
> - On send: POST to `/api/messages/text`, clear input on success.
> - On load and every 2s: poll `/api/messages?since=<lastTs>`, append new ones, scroll to bottom.
> - Expose `window.ME = "{{ user.username }}"` for JS.
>
> Create `app/static/app.js` with polling + send logic (~80 lines, vanilla JS, ES module). Use `textContent`, never `innerHTML`, to prevent XSS.
>
> Create `app/static/app.css` for bubble styling (border-radius, max-width 70%, mine vs theirs colors).
>
> Load app.js as `<script type="module" src="/static/app.js"></script>` in chat.html.

Test: two browsers, two users. Send text from one, see it on the other within 2s.

---

## Step 7 — Images: client-side prep + upload (no stego yet)

**Goal:** User pastes or picks an image. Browser resizes it to ≤1280px on the longest side, encodes as PNG, uploads. Server stores the bytes in GCS, creates a `kind: "image"` message. Image appears in chat (rounded corners) for everyone.

**The server never decodes the PNG.** It just accepts bytes, size-caps them, and stores. All pixel work happens in the browser. Add to `requirements.txt`:

```
google-cloud-storage==2.18.*
```

(No Pillow. No NumPy.)

**Prompt for coding agent:**

> Create `app/storage.py`:
> - `bucket = storage.Client(project=...).bucket(os.environ["GCS_BUCKET"])` at module level
> - `upload_png(image_id: str, data: bytes)` → upload to `images/{image_id}.png`, content-type `image/png`
> - `download_png(image_id: str) -> bytes | None` → return bytes or None if missing
>
> In `app/db.py`, add `add_image_message(sender: str, image_id: str, has_secret: bool) -> dict`.
>
> Create `app/routes/images.py`:
> - `POST /api/images` (logged-in, multipart: `file`, form field `has_secret`: "0" or "1") — read bytes, reject if >5 MB or content-type isn't `image/png`, generate `image_id = uuid4().hex`, call `upload_png`, `add_image_message(...)`, return the message dict
> - `GET /img/{image_id}` (logged-in) → stream PNG bytes from `download_png`. 404 if missing. `Cache-Control: private, max-age=3600`.
>
> Wire `images.router` into `main.py`.
>
> Update `app/static/app.js` to add image handling. Image button → hidden `<input type="file" accept="image/*">`. Also listen for `paste` events containing an image. When an image is acquired:
> 1. `const bitmap = await createImageBitmap(blob);`
> 2. Compute target size: scale so longest side is ≤1280, never upscale
> 3. Draw into a fresh `<canvas>` of those dimensions
> 4. Hold the canvas as the "pending image" state; show a thumbnail preview above the input row with an "x" button to discard. Enable the 🔑 key button.
>
> On send with a pending image (and no passphrase from later steps yet):
> 1. `canvas.toBlob(resolve, "image/png")` → blob
> 2. POST multipart to `/api/images` with `file` = blob, `has_secret=0`
> 3. Clear pending state on success
>
> When rendering an image message: `<img src="/img/{image_id}" class="{{rounded|square}}">` inside the bubble. `has_secret==false` → class `rounded`. `has_secret==true` → class `square`.
>
> Update `app/static/app.css`:
> - `.bubble img.rounded { border-radius: 16px; }`
> - `.bubble img.square { border-radius: 0; }`
> - max-width on images so they don't overflow the bubble

Test: paste an image, see it appear in other browsers. Use the file picker. Refresh: image persists.

---

## Step 8 — Steganography in the browser: XOR + SHA-256 + LSB

**Goal:** The 🔑 button opens a modal asking for a passphrase + secret message. When the user confirms and sends, the browser encrypts the secret with XOR-against-SHA256(passphrase), bit-embeds it into the canvas pixels, exports the new PNG, and uploads with `has_secret=1`.

The wire format embedded into the LSBs:

```
[4 bytes big-endian: length N][N bytes ciphertext]
ciphertext = XOR(plaintext, SHA256(passphrase))     # key cycles every 32 bytes
plaintext  = b"STEG" + UTF-8(secret_message)        # magic prefix for wrong-passphrase detection
```

LSB layout in the canvas pixel array: walk `Uint8ClampedArray` in order, skip every 4th byte (alpha), set bit 0 of each non-alpha byte to the next bit of the blob. 1280×720 → ~2 M usable bytes → ~258 KB of payload capacity, vastly more than any reasonable secret.

**Prompt for coding agent:**

> Create `app/static/stego.js` as an ES module exporting `encodeSecret(canvas, secret, passphrase)` and `decodeSecret(canvas, passphrase)`. Use this exact layout:
>
> ```js
> // app/static/stego.js
> const MAGIC = new Uint8Array([0x53, 0x54, 0x45, 0x47]); // "STEG"
>
> async function passKey(passphrase) {
>   const buf = await crypto.subtle.digest(
>     "SHA-256",
>     new TextEncoder().encode(passphrase)
>   );
>   return new Uint8Array(buf); // 32 bytes
> }
>
> function xorInPlace(data, key) {
>   for (let i = 0; i < data.length; i++) data[i] ^= key[i % key.length];
> }
>
> function embedBlob(pixels, blob) {
>   const totalBits = blob.length * 8;
>   let bitIdx = 0;
>   for (let i = 0; i < pixels.length && bitIdx < totalBits; i++) {
>     if ((i & 3) === 3) continue;                       // skip alpha
>     const bit = (blob[bitIdx >> 3] >> (7 - (bitIdx & 7))) & 1;
>     pixels[i] = (pixels[i] & 0xFE) | bit;
>     bitIdx++;
>   }
>   if (bitIdx < totalBits) throw new Error("Image too small for payload");
> }
>
> function extractBlob(pixels) {
>   // first 32 LSBs = length
>   let len = 0, bitsRead = 0, i = 0;
>   while (bitsRead < 32 && i < pixels.length) {
>     if ((i & 3) !== 3) { len = (len << 1) | (pixels[i] & 1); bitsRead++; }
>     i++;
>   }
>   if (len <= 0 || len > 200000) throw new Error("no payload");
>   const out = new Uint8Array(len);
>   let outBit = 0;
>   const totalBits = len * 8;
>   while (outBit < totalBits && i < pixels.length) {
>     if ((i & 3) !== 3) {
>       out[outBit >> 3] |= (pixels[i] & 1) << (7 - (outBit & 7));
>       outBit++;
>     }
>     i++;
>   }
>   if (outBit < totalBits) throw new Error("truncated");
>   return out;
> }
>
> export async function encodeSecret(canvas, secret, passphrase) {
>   const secretBytes = new TextEncoder().encode(secret);
>   const plain = new Uint8Array(MAGIC.length + secretBytes.length);
>   plain.set(MAGIC, 0);
>   plain.set(secretBytes, MAGIC.length);
>   const key = await passKey(passphrase);
>   xorInPlace(plain, key);                              // plain is now ciphertext
>   const blob = new Uint8Array(4 + plain.length);
>   new DataView(blob.buffer).setUint32(0, plain.length, false); // big-endian length
>   blob.set(plain, 4);
>   const ctx = canvas.getContext("2d");
>   const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
>   embedBlob(imgData.data, blob);
>   ctx.putImageData(imgData, 0, 0);
> }
>
> export async function decodeSecret(canvas, passphrase) {
>   const ctx = canvas.getContext("2d");
>   const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
>   const ct = extractBlob(imgData.data);
>   const key = await passKey(passphrase);
>   xorInPlace(ct, key);                                 // ct is now plaintext
>   for (let i = 0; i < MAGIC.length; i++) {
>     if (ct[i] !== MAGIC[i]) throw new Error("wrong passphrase");
>   }
>   return new TextDecoder().decode(ct.subarray(MAGIC.length));
> }
> ```
>
> In `app/static/app.js`:
> - `import { encodeSecret } from "./stego.js";`
> - Track `pendingSecret = { passphrase, secret } | null` alongside `pendingCanvas`.
> - 🔑 button (enabled when a pending image exists): open a Bootstrap modal with two fields (passphrase, secret). On confirm, store into `pendingSecret`. Do not send yet.
> - On send with a pending image: if `pendingSecret` exists, call `await encodeSecret(pendingCanvas, pendingSecret.secret, pendingSecret.passphrase)` first. Then `canvas.toBlob` and upload with `has_secret = pendingSecret ? "1" : "0"`. Clear pending state on success.

Test: send a plain image (rounded corners), then send an image with a secret (square corners). They should be visually indistinguishable as images; only the bubble corners differ.

---

## Step 9 — Decode UI: full-screen overlay + UL→BR tap

**Goal:** Tap any image in chat → opens full-screen overlay. Tap top-left ~15% region, then bottom-right ~15% region within 5 seconds → passphrase prompt → on correct passphrase show the secret, on wrong passphrase show "Wrong passphrase". All decoding client-side.

**Prompt for coding agent:**

> Add a fullscreen overlay to `chat.html`:
> ```html
> <div id="overlay" hidden>
>   <img id="overlay-img" alt="">
>   <button id="overlay-close" aria-label="close">×</button>
> </div>
> ```
> CSS: `#overlay { position: fixed; inset: 0; background: #000; display: flex; align-items: center; justify-content: center; z-index: 1050; }` `#overlay img { max-width: 100%; max-height: 100%; }` Close button top-right.
>
> In `app.js`:
> - Click handler on any `.bubble img`: set `#overlay-img.src` to the same `src`, unhide overlay.
> - Gesture state machine: `idle → ul_tapped (timer 5s) → idle`. UL region = `(x/w < 0.15 && y/h < 0.15)`. BR region = `(x/w > 0.85 && y/h > 0.85)`. Compute click coords from `getBoundingClientRect()` of the overlay image. Both `click` and `touchstart` drive the state machine.
> - When UL→BR happens within the window: prompt for passphrase (a Bootstrap modal with one input, or `window.prompt()` for simplicity). On submit:
>   1. Draw the overlay image into an offscreen `<canvas>` at its natural width/height
>   2. `import { decodeSecret } from "./stego.js"` and call `decodeSecret(canvas, passphrase)`
>   3. Show the returned secret in another modal (or alert). On `Error("wrong passphrase")` or extraction errors, show "Wrong passphrase or no message".
> - Close button or Escape closes the overlay and resets the gesture state.

Test on desktop and on a phone. The gesture should feel like a hidden affordance — natural once you know it exists. Wrong passphrase reliably says wrong passphrase (the magic-prefix check earns its keep here).

---

## Step 10 — Local dev: tying it together

At this point you have a fully working app locally. Run loop:

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
uvicorn app.main:app --reload --port 8080
```

In `.env` for local dev, set `SESSION_HTTPS_ONLY=0` so the cookie works on `http://localhost`. The `SessionMiddleware` init in `main.py` should read this env var (default 1).

Open two browsers (or one normal + one incognito), log in as two different users, chat. Test pasting screenshots. Test the full stego flow end-to-end. Try a wrong passphrase to confirm the magic-prefix check kicks in.

---

## Step 11 — Containerize

**Goal:** A `Dockerfile` that builds the app into an image suitable for Cloud Run.

**Prompt for coding agent:**

> Create `Dockerfile`:
> ```dockerfile
> FROM python:3.11-slim
> WORKDIR /app
> ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
> COPY requirements.txt .
> RUN pip install --no-cache-dir -r requirements.txt
> COPY app/ ./app/
> ENV PORT=8080
> CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers
> ```
>
> Create `.gcloudignore`:
> ```
> .git
> .venv
> __pycache__
> *.pyc
> .env
> sa-key.json
> scripts/
> install.md
> ```

Test locally:
```bash
docker build -t stegchat .
docker run -p 8080:8080 \
  -e SESSION_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))') \
  -e GCP_PROJECT=stegchat-XXXX \
  -e GCS_BUCKET=stegchat-XXXX-images \
  -v $PWD/sa-key.json:/sa-key.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/sa-key.json \
  stegchat
```

---

## Step 12 — Deploy to Cloud Run

**Goal:** Live URL.

1. Create a runtime service account:
   ```bash
   gcloud iam service-accounts create stegchat-run
   gcloud projects add-iam-policy-binding stegchat-XXXX \
       --member="serviceAccount:stegchat-run@stegchat-XXXX.iam.gserviceaccount.com" \
       --role="roles/datastore.user"
   gcloud projects add-iam-policy-binding stegchat-XXXX \
       --member="serviceAccount:stegchat-run@stegchat-XXXX.iam.gserviceaccount.com" \
       --role="roles/storage.objectAdmin"
   ```

2. Put `SESSION_SECRET` in Secret Manager:
   ```bash
   echo -n "$(python -c 'import secrets;print(secrets.token_hex(32))')" \
     | gcloud secrets create session-secret --data-file=-
   gcloud secrets add-iam-policy-binding session-secret \
     --member="serviceAccount:stegchat-run@stegchat-XXXX.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

3. Deploy from source (Cloud Build does the Docker work):
   ```bash
   gcloud run deploy stegchat \
     --source . \
     --region europe-west3 \
     --service-account stegchat-run@stegchat-XXXX.iam.gserviceaccount.com \
     --allow-unauthenticated \
     --set-env-vars "GCP_PROJECT=stegchat-XXXX,GCS_BUCKET=stegchat-XXXX-images,SESSION_HTTPS_ONLY=1" \
     --set-secrets "SESSION_SECRET=session-secret:latest"
   ```

4. Cloud Run prints a URL like `https://stegchat-xxxxx.europe-west3.run.app`. Open it.

5. Bootstrap the first admin against the **deployed** Firestore (run locally with the same `GCP_PROJECT`):
   ```bash
   python scripts/bootstrap_admin.py you@example.com 'your-strong-pw'
   ```

6. Visit the URL, log in, add other users from `/admin`.

To redeploy after code changes, re-run the same `gcloud run deploy` command. That's the whole CI/CD.

---

## Step 13 (optional) — Gmail SMTP invitation emails

Until this step, the admin types each new user's temporary password into the form and tells the user out-of-band. If you want auto-emailed invitations:

1. Gmail owner: enable 2-Step Verification → generate App Password at `https://myaccount.google.com/apppasswords` → copy the 16-char string.
2. Store as secrets:
   ```bash
   echo -n "you@gmail.com"        | gcloud secrets create smtp-user --data-file=-
   echo -n "abcdefghijklmnop"     | gcloud secrets create smtp-pass --data-file=-
   gcloud secrets add-iam-policy-binding smtp-user --member=... --role=roles/secretmanager.secretAccessor
   gcloud secrets add-iam-policy-binding smtp-pass --member=... --role=roles/secretmanager.secretAccessor
   ```
3. Redeploy with `--set-secrets "SMTP_USER=smtp-user:latest,SMTP_PASS=smtp-pass:latest"` appended.

**Prompt for coding agent:**

> Create `app/email_invite.py`:
> ```python
> import os, smtplib, ssl
> from email.message import EmailMessage
>
> def send_invite(to_email: str, username: str, temp_password: str, app_url: str) -> None:
>     user = os.environ.get("SMTP_USER")
>     pw = os.environ.get("SMTP_PASS")
>     if not user or not pw:
>         return  # silently no-op when SMTP isn't configured
>     msg = EmailMessage()
>     msg["Subject"] = "You're invited to StegChat"
>     msg["From"] = user
>     msg["To"] = to_email
>     msg.set_content(
>         f"Username: {username}\n"
>         f"Temporary password: {temp_password}\n"
>         f"Sign in: {app_url}\n"
>         f"You'll be asked to change the password on first login.\n"
>     )
>     with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
>         s.login(user, pw)
>         s.send_message(msg)
> ```
>
> In `POST /admin/users`, after a successful user creation, call `send_invite(email, username, password, str(request.base_url))`. Wrap in try/except so SMTP failures don't break the response — show a flash like `?ok=1&email=failed`.

That's it. Everything else stays the same.

---

## Notes, gotchas, things future-you will thank you for

- **Cookie on Cloud Run:** Cloud Run terminates TLS for you; the app sees `http` internally but the browser sees `https`. The Dockerfile passes `--proxy-headers` to uvicorn so `Secure` cookies work. Without it you'd bounce to `/login` forever.
- **Why client-side stego:** the passphrase and the plaintext literally never leave the browser. The server stores an opaque PNG and has no way to recover the secret even if it wanted to. That's the steganography premise made honest.
- **Why XOR and not AES-GCM:** for a student project the simplicity is worth it — no library install, no IV/nonce management, ~40 lines of crypto-relevant JS. The cost is the "two-time-pad" weakness: if the same passphrase encrypts two different secrets, an attacker who grabs both ciphertexts can XOR them together to cancel the key and recover both messages via crib-dragging. Real attack, not theoretical. Acceptable for classroom use; flag it in your writeup so the grader knows you know.
- **Magic prefix "STEG":** without it, a wrong passphrase would still "succeed" and return random bytes. With it, the four-byte check at the start of the plaintext catches all but a 1-in-4-billion false positive. Cheap and effective.
- **Why PNG, not JPEG:** JPEG is lossy. DCT compression destroys LSBs. PNG is lossless — bytes you set are bytes that survive a round-trip through GCS and the browser cache. Use PNG always.
- **Stego capacity:** 1280×720 = ~921k pixels × 3 usable channels = ~2.76 M bits ≈ 345 KB of payload. You will never hit the limit with text.
- **Performance:** the LSB embed loop runs in ~5 ms on a phone for a 1 MP image. `getImageData`/`putImageData` cost more than the math. No need to worry about it.
- **Firestore costs:** ~zero for this app. Free tier covers ~50k reads/day; polling every 2s with 5 users open ≈ 22k reads/day.
- **Cloud Storage costs:** PNGs at ~500 KB each. Free tier covers 5 GB.
- **Backups:** `gcloud firestore export gs://stegchat-XXXX-images/backups/$(date +%F)` if you care.
- **Don't commit `sa-key.json` or `.env`.** Already in `.gitignore`, but verify with `git status` before the first commit.
- **Forgotten admin password:** `bootstrap_admin.py` aborts on existing user; either add a `--force` flag or delete and recreate the doc in the Firestore console.

---

## A reasonable order to actually do this in one weekend

- Friday evening: Prerequisites, Steps 1–3. You can log in by bedtime.
- Saturday morning: Steps 4–6. You can chat with yourself in two tabs.
- Saturday afternoon: Step 7. Plain images work.
- Saturday evening: Steps 8–9. The hidden-message magic happens, end-to-end in the browser.
- Sunday morning: Steps 11–12. It's live.
- Sunday afternoon: skip Step 13, demo to whoever, eat lunch.
