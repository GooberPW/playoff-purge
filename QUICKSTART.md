# PlayoffPurge Quick Start Guide

Get your dashboard running in 10 minutes! ⚡

## 1️⃣ Google Cloud Setup (5 minutes)

```bash
# Visit: https://console.cloud.google.com
# 1. Create project: "PlayoffPurge"
# 2. Enable: Google Sheets API
# 3. Create Service Account (IAM & Admin → Service Accounts)
# 4. Create JSON key → Download
# 5. Copy service account email
```

## 2️⃣ Google Sheet Setup (2 minutes)

```bash
# Visit: https://sheets.google.com
# 1. Create new sheet: "PlayoffPurge 2025"
# 2. Create 4 tabs: League_Meta, Teams, Rosters, Roster_Requirements
# 3. Copy headers from GOOGLE_SHEET_TEMPLATE.md
# 4. Share with service account email (Viewer)
# 5. Copy Sheet ID from URL
```

## 3️⃣ Local Setup (3 minutes)

```bash
# Navigate to project
cd PlayoffPurge

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup credentials
mkdir credentials
# Copy your service-account.json to credentials/

# Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_SHEET_ID

# Run!
uvicorn main:app --reload --port 8000
```

Visit: http://localhost:8000 🎉

## 🚀 Deploy to Render (Optional - 5 minutes)

```bash
# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git push

# On Render.com:
# 1. New Web Service
# 2. Connect GitHub repo
# 3. Add env vars:
#    - GOOGLE_SHEET_ID
#    - GOOGLE_APPLICATION_CREDENTIALS_JSON (paste JSON)
#    - ADMIN_PASSWORD
# 4. Deploy
```

## 📝 Minimum Viable Sheet Data

To test the app, add this to your Google Sheet:

**League_Meta tab:**
```
key          | value
league_name  | PlayoffPurge 2025
current_week | Week 18
last_updated | 2025-01-05 14:30:00
```

**Teams tab:**
```
team_id | owner_name | team_name       | seed | status | total_points | current_week
1       | Goober     | Goober's Goons  | 1    | active | 0            | Week 18
```

**Rosters tab:**
```
team_id | week    | position | player_name     | team | points | status
1       | Week 18 | QB       | Patrick Mahomes | KC   | 24.5   | active
```

That's it! Your dashboard should now display data.

## ⚠️ Troubleshooting

**Error: "Failed to load dashboard"**
- Check `.env` has correct GOOGLE_SHEET_ID
- Verify sheet is shared with service account
- Confirm credentials JSON is in `credentials/` folder

**Error: "Permission denied"**
- Sheet not shared with service account email
- Check service account email in JSON file
- Share sheet with that email (Viewer access)

**No data showing**
- Verify sheet tab names exactly match: `League_Meta`, `Teams`, `Rosters`
- Check column headers match the schema
- Add at least one team to Teams tab

## 🎯 Next Steps

1. ✅ Add all 9 teams to Teams tab
2. ✅ Add player rosters to Rosters tab
3. ✅ Update points after games
4. ✅ Mark eliminated teams
5. ✅ Deploy to Render for public access

## 📚 Full Documentation

- README.md - Complete setup and deployment guide
- GOOGLE_SHEET_TEMPLATE.md - Detailed sheet structure
- .env.example - All environment variables

## 🆘 Need Help?

Check the README.md for detailed troubleshooting steps.

---

**You're ready to run PlayoffPurge! 🏈**
