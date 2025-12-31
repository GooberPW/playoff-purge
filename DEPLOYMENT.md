# 🚀 Deployment Guide - Render

Complete guide to securely deploy PlayoffPurge to Render.

## 🔒 Security Overview

Your setup is **secure by design**:
- ✅ API keys never committed to git (`.gitignore` blocks them)
- ✅ Environment variables encrypted in Render
- ✅ Service account has minimal permissions (read/write one sheet only)
- ✅ HTTPS automatically enabled
- ✅ Temp credentials file cleaned up automatically

## 📋 Prerequisites

1. **Google Cloud Setup** (Already Done ✅)
   - Service account created
   - Google Sheets API enabled
   - Sheet shared with service account email

2. **GitHub Account**
   - Free account at https://github.com

3. **Render Account**
   - Free account at https://render.com

## 🚀 Deployment Steps

### Step 1: Push to GitHub

```bash
# Initialize git repository (if not already done)
git init

# Add all files (secrets are excluded by .gitignore)
git add .
git commit -m "Initial commit - PlayoffPurge draft app"

# Create a new repository on GitHub:
# Go to https://github.com/new
# Repository name: playoff-purge
# Description: Fantasy Football Playoff Draft System
# Public or Private: Your choice
# DO NOT initialize with README (you already have one)
# Click "Create repository"

# Link your local repo to GitHub
git remote add origin https://github.com/YOUR_USERNAME/playoff-purge.git

# Push to GitHub
git branch -M main
git push -u origin main
```

**Verify Security**: Visit your GitHub repo and confirm:
- ❌ No `credentials/` folder visible
- ❌ No `.env` file visible
- ❌ No `*.json` files visible (except `package.json` if you had one)
- ✅ Only source code files visible

### Step 2: Prepare Service Account JSON

You need to copy the **entire contents** of your service account JSON file:

**On Windows:**
```powershell
# Option 1: Copy to clipboard
Get-Content credentials\service-account.json | Set-Clipboard

# Option 2: Open in notepad
notepad credentials\service-account.json
```

Then select all (Ctrl+A) and copy (Ctrl+C).

The JSON looks like:
```json
{
  "type": "service_account",
  "project_id": "your-project",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
  "client_email": "playoff-purge@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

### Step 3: Get Your Google Sheet ID

From your Google Sheet URL:
```
https://docs.google.com/spreadsheets/d/156ZrwEK6Yr3F5Hj7yQ07FkJBoNQqKSi8R_Fzs5lQ3Y0/edit
                                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                         This is your SHEET_ID
```

Copy this ID.

### Step 4: Deploy to Render

1. **Go to Render Dashboard**
   - Visit https://dashboard.render.com
   - Sign up / Log in

2. **Create New Web Service**
   - Click "New +" button → "Web Service"
   - Click "Connect GitHub" (authorize if first time)
   - Find and select your `playoff-purge` repository

3. **Configure Service** (Render auto-detects `render.yaml`)
   - **Name**: `playoff-purge` (or your choice)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt` (auto-filled)
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT` (auto-filled)

4. **Add Environment Variables** (CRITICAL!)
   
   Click "Advanced" → Scroll to "Environment Variables" → Add these:

   | Variable Name | Value | Notes |
   |--------------|--------|-------|
   | `GOOGLE_SHEET_ID` | *your sheet ID* | The ID you copied above |
   | `GOOGLE_APPLICATION_CREDENTIALS_JSON` | *paste entire JSON* | The service account JSON (all of it!) |
   | `CACHE_TTL_SECONDS` | `300` | Optional (default is 300) |
   | `ADMIN_PASSWORD` | *auto-generated* | Click "Generate" button |
   | `APP_TITLE` | `PlayoffPurge 2025` | Optional (default already set) |

   **Important**: When pasting the JSON, make sure:
   - ✅ Include the opening `{` and closing `}`
   - ✅ All newlines are preserved
   - ✅ The `private_key` field includes `\n` characters
   - ✅ No extra spaces before/after

5. **Create Web Service**
   - Click "Create Web Service"
   - Render will start building your app (takes 2-3 minutes)

6. **Monitor Deployment**
   - Watch the build logs in real-time
   - Look for: `Build successful`
   - Then: `Service is live 🎉`

7. **Get Your URL**
   - Render assigns: `https://playoff-purge.onrender.com`
   - Or custom: `https://your-custom-name.onrender.com`

### Step 5: Test Your Deployment

1. **Visit your URL**
   ```
   https://playoff-purge.onrender.com
   ```

2. **Test the dashboard**
   - Should see team standings
   - Data loads from your Google Sheet

3. **Test the draft page**
   ```
   https://playoff-purge.onrender.com/draft
   ```
   - Select your name
   - Should see available players
   - Should see FPPG and opponent data

4. **Test health check**
   ```
   https://playoff-purge.onrender.com/health
   ```
   - Should return: `{"status": "healthy", ...}`

## 🔧 Troubleshooting

### Error: "The caller does not have permission"

**Cause**: Google Sheet not shared with service account

**Fix**:
1. Open your Google Sheet
2. Click "Share"
3. Add the service account email (from JSON: `client_email`)
4. Give "Editor" permissions
5. Click "Send"

### Error: "Could not load default credentials"

**Cause**: Environment variable not set correctly

**Fix**:
1. Go to Render Dashboard → Your Service → Environment
2. Check `GOOGLE_APPLICATION_CREDENTIALS_JSON` exists
3. Verify JSON is complete (starts with `{`, ends with `}`)
4. Re-paste if needed
5. Trigger manual deploy

### Error: "Service Unavailable"

**Cause**: App is in sleep mode (free tier)

**Fix**:
- Wait 30 seconds, app will wake up
- Upgrade to paid tier ($7/mo) for always-on

### Error: "Module not found"

**Cause**: Missing dependency in requirements.txt

**Fix**:
1. Check deploy logs for missing module name
2. Add to `requirements.txt`
3. Push to GitHub
4. Render auto-deploys

## 🔄 Updating Your App

After making code changes:

```bash
# 1. Commit changes
git add .
git commit -m "Description of changes"

# 2. Push to GitHub
git push

# 3. Render automatically deploys! 🎉
```

Watch deploy progress in Render dashboard.

## 🔐 Security Best Practices

### ✅ Already Implemented

1. **No Secrets in Git**
   - `.gitignore` blocks credentials
   - GitHub never sees API keys

2. **Encrypted Environment Variables**
   - Render encrypts all env vars
   - Only your app can access them

3. **HTTPS Only**
   - Automatic SSL certificate
   - All traffic encrypted

4. **Minimal Permissions**
   - Service account only accesses one sheet
   - Can't access your Google account

### 🔒 Additional Hardening (Optional)

1. **Add HTTP Basic Auth to Admin Endpoints**
   ```python
   # Already implemented in /refresh endpoint!
   # Username: admin
   # Password: from ADMIN_PASSWORD env var
   ```

2. **IP Whitelisting** (Paid Feature)
   - Render Pro: Static IP addresses
   - Restrict Google Sheet access to Render IPs only

3. **Secret Rotation**
   - Every 90 days: Generate new service account key
   - Update in Render dashboard
   - Delete old key from Google Cloud

4. **Monitoring**
   - Enable Google Cloud audit logs
   - Set up alerts for API usage spikes
   - Monitor Render logs for errors

## 💰 Cost Breakdown

### Free Tier (What You'll Use)

**Render Free:**
- ✅ 750 hours/month (24/7 for one service)
- ✅ Automatic HTTPS
- ✅ Automatic deploys from GitHub
- ⚠️ Spins down after 15 min inactivity (wakes in 30s)
- **Cost: $0/month**

**Google Sheets API:**
- ✅ 60 requests/minute
- ✅ Your app uses ~6 req/min with caching
- **Cost: $0/month**

**Total: $0/month** 🎉

### Paid Options (If Needed)

**Render Starter ($7/mo):**
- Always-on (no sleep)
- 750 hours/month
- Good for active use

**Render Pro ($25/mo):**
- Static IP addresses
- Advanced features
- Priority support

## 📊 Monitoring Your App

### View Logs

```bash
# In Render Dashboard:
# Your Service → Logs
```

See real-time logs including:
- HTTP requests
- Errors
- API calls to Google Sheets

### View Metrics

```bash
# In Render Dashboard:
# Your Service → Metrics
```

Monitor:
- CPU usage
- Memory usage
- Response times
- Error rates

### Health Check

Render automatically pings `/health` every minute:
- ✅ Green: App is healthy
- ❌ Red: App is down (will restart automatically)

## 🎯 Custom Domain (Optional)

Want to use your own domain? (e.g., `draft.yourleague.com`)

1. **In Render Dashboard:**
   - Your Service → Settings → Custom Domains
   - Click "Add Custom Domain"
   - Enter: `draft.yourleague.com`

2. **In Your DNS Provider:**
   - Add CNAME record:
     - Name: `draft`
     - Value: `playoff-purge.onrender.com`
     - TTL: 3600

3. **Wait for SSL Certificate** (automatic, ~5 minutes)

4. **Done!** Visit https://draft.yourleague.com

## 🆘 Support

### Render Support
- Docs: https://render.com/docs
- Community: https://community.render.com
- Status: https://status.render.com

### Google Cloud Support
- Docs: https://cloud.google.com/docs
- Support: https://cloud.google.com/support

### App Issues
- Check logs in Render Dashboard
- Test locally first: `uvicorn main:app --reload`
- Verify Google Sheet is shared with service account

## ✅ Deployment Checklist

Before going live:

- [ ] Code pushed to GitHub
- [ ] No secrets visible in GitHub repo
- [ ] Service account JSON copied
- [ ] Google Sheet ID copied
- [ ] Render service created
- [ ] All environment variables added
- [ ] Build completed successfully
- [ ] App is live and accessible
- [ ] Dashboard loads team data
- [ ] Draft page works
- [ ] Health check returns healthy
- [ ] Google Sheet properly shared with service account

## 🎉 You're Live!

Your draft app is now:
- ✅ Publicly accessible
- ✅ Secure (HTTPS + encrypted secrets)
- ✅ Auto-deploying from GitHub
- ✅ Free to run
- ✅ Production-ready

Share your URL with your league members and start drafting! 🏈
