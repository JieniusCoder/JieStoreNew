# Deploy JieStore to Render

Follow these steps to deploy your Django app to Render.

---

## Prerequisites

- A [Render](https://render.com) account (free)
- Your code in a Git repository (GitHub, GitLab, or Bitbucket)
- Your `.env` values ready (see Environment Variables below)

---

## Step 1: Push Your Code to GitHub

If not already done:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

---

## Step 2: Create a PostgreSQL Database on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **PostgreSQL**
3. Name it (e.g. `jiestore-db`)
4. Choose **Free** plan
5. Select your region
6. Click **Create Database**
7. Wait for it to provision, then copy the **Internal Database URL** (you’ll use this in Step 4)

---

## Step 3: Create a Web Service

1. In the Render dashboard, click **New +** → **Web Service**
2. Connect your GitHub repo (authorize Render if needed)
3. Configure:
   - **Name:** `jiestore` (or any name)
   - **Region:** Same as your database
   - **Branch:** `main` (or your default branch)
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     ./build.sh
     ```
   - **Start Command:**
     ```bash
     cd JieStore && gunicorn JieStore.wsgi --log-file -
     ```

---

## Step 4: Add Environment Variables

In your Web Service → **Environment** tab, add:

| Key | Value | Notes |
|-----|-------|-------|
| `SECRET_KEY` | (generate a random string) | Use `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` | Must be false in production |
| `ALLOWED_HOSTS` | `jiestore.onrender.com` | Replace with your actual Render URL |
| `DATABASE_URL` | (from Step 2) | Internal Database URL from your PostgreSQL instance |
| `GOOGLE_CLIENT_ID` | (your value) | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | (your value) | From Google Cloud Console |
| `STRIPE_SECRET_KEY` | (your value) | From Stripe Dashboard |
| `STRIPE_PUBLISHABLE_KEY` | (your value) | From Stripe Dashboard |
| `PAYPAL_CLIENT_ID` | (your value) | From PayPal Developer |
| `PAYPAL_CLIENT_SECRET` | (your value) | From PayPal Developer |
| `PAYPAL_ENV` | `sandbox` or `live` | Use `live` for production payments |

**Important:** After the first deploy, Render will give you a URL like `https://jiestore-xxxx.onrender.com`. Update `ALLOWED_HOSTS` to include that host (e.g. `jiestore-xxxx.onrender.com`).

---

## Step 5: Update Google OAuth Redirect URIs

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Edit your OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs:**
   ```
   https://YOUR-RENDER-URL.onrender.com/accounts/google/login/callback/
   ```
4. Add to **Authorized JavaScript origins:**
   ```
   https://YOUR-RENDER-URL.onrender.com
   ```

---

## Step 6: Update PayPal / Stripe (if needed)

- **PayPal:** In [PayPal Developer Dashboard](https://developer.paypal.com), add your Render URL to allowed return/cancel URLs if required.
- **Stripe:** Stripe uses your configured domain; update webhook URLs if you use webhooks.

---

## Step 7: Create Superuser (Optional)

After the first deploy, open the **Shell** tab in your Render Web Service and run:

```bash
cd JieStore
python manage.py createsuperuser
```

---

## Step 8: Deploy

1. Click **Create Web Service**
2. Render will build and deploy
3. When it’s live, open your URL (e.g. `https://jiestore-xxxx.onrender.com`)

---

## Media Files (Product Images)

Render’s disk is ephemeral. Uploaded images will be lost on redeploy. For production:

- Use [Render Disk](https://render.com/docs/disks) for persistent storage, or
- Use cloud storage (e.g. AWS S3) and configure `DEFAULT_FILE_STORAGE`

---

## Troubleshooting 500 Errors

If you get 500 errors (e.g. on admin add forms):

1. **Check Render logs** (Dashboard → your service → **Logs**). The app now logs full tracebacks; look for `Unhandled exception:` or Python tracebacks.

2. **Verify DATABASE_URL is set:**
   - Go to your Web Service → **Environment**
   - Ensure `DATABASE_URL` exists (from your PostgreSQL service)
   - If missing: go to your PostgreSQL service → **Connect** → copy **Internal Database URL** → add as `DATABASE_URL` in the Web Service
   - Or **link** the database: PostgreSQL service → **Connect** → **Add to Web Service** → select your web service

3. **Database permissions:** Render PostgreSQL has full read/write. If you see `permission denied` or `read-only` in logs, the app may be using SQLite (no `DATABASE_URL`). Fix by adding `DATABASE_URL`.

4. **Temporarily enable DEBUG** to see the traceback on the error page:
   - Add `DEBUG` = `True` in Environment, redeploy, reproduce, copy the traceback, then set back to `False`.

5. **Common causes:** Missing DATABASE_URL (SQLite fails on Render), CSRF_TRUSTED_ORIGINS, migrations not run.

---

## Free Tier Notes

- Web Service sleeps after ~15 minutes of no traffic; first request may take 30–60 seconds
- PostgreSQL free tier: 1 GB, 90-day expiration (then data is removed)
- For a real store, consider a paid plan
