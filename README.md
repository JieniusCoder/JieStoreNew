# JieStore

Simple store-front web app built with Django.

## Tech stack

- **Language**: Python (project environment indicates **Python 3.12.x**)
- **Backend framework**: **Django 5.1.2**
- **Server-side rendering**: Django Templates (`JieStoreApp/templates/`)
- **Database (dev/default)**: **SQLite** (`db.sqlite3`)
- **Static assets**: Django staticfiles (CSS in `JieStoreApp/static/`)
- **Media uploads**: Django `MEDIA_ROOT`/`MEDIA_URL` (stored in `JieStore/media/`)
- **Images**: Django `ImageField` (requires **Pillow**)
- **Payments**: **Stripe Checkout** (card) + **PayPal JS SDK** (PayPal) (requires env config)

## Project structure

- `JieStore/manage.py`: Django entrypoint
- `JieStore/JieStore/`: Django project (settings/urls/wsgi)
- `JieStore/JieStoreApp/`: Main app (models/views/urls, templates, static)
- `JieStore/media/`: Uploaded media (served in dev when `DEBUG=True`)

## How to start (Windows / PowerShell)

### Prerequisites

- **Python 3.12+** installed

### Create & activate a virtual environment

From the repo root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If activation is blocked, run this once in the same PowerShell session and retry:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### Set up the database & run the server

```powershell
python .\JieStore\manage.py makemigrations JieStoreApp
python .\JieStore\manage.py migrate
python .\JieStore\manage.py createsuperuser
python .\JieStore\manage.py runserver
```

Open:

- **App**: `http://127.0.0.1:8000/`
- **Admin**: `http://127.0.0.1:8000/admin/`

## Key routes (current)

- `/` home page
- `/items/` item list
- `/items/cart/` cart page
- `/checkout/` checkout (Stripe + PayPal options; requires env config)
- `/accounts/` authentication (Google login via django-allauth)

## Google login (dev)

1) In Google Cloud Console, create OAuth credentials and set the **Authorized redirect URI** to:
   - `http://127.0.0.1:8000/accounts/google/login/callback/`

2) Put credentials in `.env`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

3) In Django admin (`/admin/`):
   - **Sites**: set the site domain to `127.0.0.1:8000`
   - **Social applications**: add a Google app using your client id/secret and attach it to that Site

## Payments configuration (dev)

Payments go to **the Stripe/PayPal accounts that own the API credentials you configure** (for example, the accounts registered to `jigglyjie@gmail.com`).

- **Option A (recommended): use a `.env` file**

1) Copy `.env.example` to `.env`
2) Fill in your real keys
3) Restart `runserver`

- **Option B: set environment variables in PowerShell**

- **Stripe**:

```powershell
$env:STRIPE_SECRET_KEY="sk_test_..."
# Optional (currently only used for display): 
$env:STRIPE_PUBLISHABLE_KEY="pk_test_..."
# Optional (only needed if you wire Stripe webhooks):
$env:STRIPE_WEBHOOK_SECRET="whsec_..."
```

- **PayPal**:

```powershell
$env:PAYPAL_CLIENT_ID="YOUR_PAYPAL_CLIENT_ID"
$env:PAYPAL_CLIENT_SECRET="YOUR_PAYPAL_CLIENT_SECRET"
# Optional: "sandbox" (default) or "live"
$env:PAYPAL_ENV="sandbox"
```

## Notes

- **Migrations**: `.gitignore` currently ignores `**/migrations/`. If you clone this repo fresh, you will likely need to generate migrations locally using `makemigrations` before `migrate`.
- **Security**: `DEBUG` is enabled and a Django `SECRET_KEY` is currently hard-coded in `settings.py`. Do not use these defaults for production.

