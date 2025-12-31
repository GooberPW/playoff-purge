# Google Sheet Setup Template

This document provides copy-paste ready content for setting up your PlayoffPurge Google Sheet.

## 📊 Create Your Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Name it "PlayoffPurge 2025"
4. Create 4 tabs with the exact names below

---

## Tab 1: League_Meta

### Headers (Row 1):
```
key | value
```

### Sample Data (Rows 2-4):
```
league_name      | PlayoffPurge 2025
current_week     | Week 18
last_updated     | 2025-01-05 14:30:00
```

**Instructions:**
- Column A: Key names (don't change these)
- Column B: Your actual values (update as needed)
- Update `last_updated` after each data change

---

## Tab 2: Teams

### Headers (Row 1):
```
team_id | owner_name | team_name | seed | status | total_points | current_week
```

### Sample Data for All 9 Teams (Rows 2-10):
```
1 | Goober   | Goober's Goons    | 1 | active | 0 | Week 18
2 | Kevin    | Kevin's Killers   | 2 | active | 0 | Week 18
3 | Kathleen | Kat's Krew        | 3 | active | 0 | Week 18
4 | Russo    | Russo's Raiders   | 4 | active | 0 | Week 18
5 | Brett    | Brett's Bashers   | 5 | active | 0 | Week 18
6 | Hamm     | Hamm's Heroes     | 6 | active | 0 | Week 18
7 | Maulin   | Maulin's Maulers  | 7 | active | 0 | Week 18
8 | Steve    | Steve's Slayers   | 8 | active | 0 | Week 18
9 | Wil      | Wil's Warriors    | 9 | active | 0 | Week 18
```

**Instructions:**
- `team_id`: Unique ID (1-9)
- `owner_name`: Owner's actual name
- `team_name`: Fantasy team name (be creative!)
- `seed`: Draft order / ranking (1-9)
- `status`: Must be one of: `active`, `eliminated`, `champion`
- `total_points`: Use formula or manual entry (see below)
- `current_week`: Should match League_Meta current_week

### Auto-Calculate Points Formula

In cell F2 (total_points for team 1):
```
=SUMIF(Rosters!A:A, A2, Rosters!F:F)
```

Copy this formula down to F3:F10 for all teams. This will automatically sum points from the Rosters tab.

---

## Tab 3: Rosters

### Headers (Row 1):
```
team_id | week | position | player_name | team | points | status
```

### Sample Data Structure:
```
1 | Week 18 | QB  | Patrick Mahomes      | KC  | 24.5 | active
1 | Week 18 | RB  | Christian McCaffrey  | SF  | 18.2 | active
1 | Week 18 | RB  | Bijan Robinson       | ATL | 15.8 | active
1 | Week 18 | WR  | CeeDee Lamb          | DAL | 22.1 | active
1 | Week 18 | WR  | Tyreek Hill          | MIA | 19.4 | active
2 | Week 18 | QB  | Josh Allen           | BUF | 28.3 | active
2 | Week 18 | RB  | Derrick Henry        | BAL | 16.5 | active
...
```

**Instructions:**
- `team_id`: Must match team_id from Teams tab
- `week`: Current week (Week 18, Wildcard, Divisional, etc.)
- `position`: QB, RB, WR, TE, FLEX, K, DST, SUPERFLEX
- `player_name`: Full player name
- `team`: NFL team abbreviation (3 letters)
- `points`: FanDuel scoring (4pt pass TD, 0.5 PPR)
- `status`: Usually "active"

### Week 18 Roster Requirements (per team):
- 1 QB
- 2 RB
- 2 WR

Each team should have **5 rows** in the Rosters tab for Week 18.

---

## Tab 4: Roster_Requirements

### Headers (Row 1):
```
week | teams_left | positions_required | payout
```

### Data (Rows 2-6):
```
Week 18       | 9 | QB,RB,RB,WR,WR                     | $20
Wildcard      | 8 | QB,RB,WR,FLEX,FLEX                 | $20
Divisional    | 6 | SUPERFLEX,RB,WR,FLEX,FLEX          | $20
Championship  | 4 | SUPERFLEX,FLEX,FLEX,FLEX,FLEX      | $20
Superbowl     | 2 | SUPERFLEX,FLEX,FLEX,FLEX,FLEX      | $100
```

**Instructions:**
- This tab is for reference only
- The app doesn't read this tab (yet)
- Keep it updated for your league members

---

## 🔐 Important: Share Your Sheet

After creating the sheet:

1. Click the **Share** button (top right)
2. Paste your service account email:
   ```
   playoff-purge@your-project-id.iam.gserviceaccount.com
   ```
3. Set permission to **Viewer** (read-only)
4. Click **Done**

---

## 📝 Weekly Update Process

### After Games Complete:

1. **Update Rosters tab**:
   - Enter final player points in column F

2. **Teams tab auto-updates** (if using formula):
   - `total_points` recalculates automatically
   - If not using formula, manually sum points

3. **Eliminate teams**:
   - Change `status` from `active` to `eliminated` for bottom teams

4. **Update League_Meta**:
   - Change `current_week` to next week
   - Update `last_updated` timestamp

5. **Refresh dashboard**:
   - Visit your dashboard URL
   - Or use `/refresh` endpoint to clear cache immediately

---

## 🎨 Quick Copy Template

Want to get started fast? Use this spreadsheet URL to make a copy:

[Create a template sheet and paste link here]

Or manually copy the tables above into your new sheet.

---

## 💡 Pro Tips

### Use Data Validation

For the `status` column in Teams tab:
1. Select cells E2:E10
2. Data → Data validation
3. Criteria: List of items: `active,eliminated,champion`
4. Save

This prevents typos in status values.

### Use Conditional Formatting

Highlight eliminated teams:
1. Select Teams tab data range
2. Format → Conditional formatting
3. Format rules: Custom formula: `=$E2="eliminated"`
4. Formatting style: Light red background
5. Done

### Freeze Header Rows

For easier scrolling:
1. Click on row 2 (data row)
2. View → Freeze → 1 row

---

## 📊 NFL Team Abbreviations Reference

Common NFL team codes for the `team` column:

```
ARI - Arizona Cardinals      MIA - Miami Dolphins
ATL - Atlanta Falcons        MIN - Minnesota Vikings
BAL - Baltimore Ravens       NE  - New England Patriots
BUF - Buffalo Bills          NO  - New Orleans Saints
CAR - Carolina Panthers      NYG - New York Giants
CHI - Chicago Bears          NYJ - New York Jets
CIN - Cincinnati Bengals     PHI - Philadelphia Eagles
CLE - Cleveland Browns       PIT - Pittsburgh Steelers
DAL - Dallas Cowboys         SF  - San Francisco 49ers
DEN - Denver Broncos         SEA - Seattle Seahawks
DET - Detroit Lions          TB  - Tampa Bay Buccaneers
GB  - Green Bay Packers      TEN - Tennessee Titans
HOU - Houston Texans         WAS - Washington Commanders
IND - Indianapolis Colts     
JAX - Jacksonville Jaguars   
KC  - Kansas City Chiefs     
LV  - Las Vegas Raiders      
LAC - Los Angeles Chargers   
LAR - Los Angeles Rams       
```

---

## ✅ Verification Checklist

Before connecting to your app:

- [ ] All 4 tabs created with exact names
- [ ] League_Meta has all 3 required keys
- [ ] Teams tab has all 9 teams with headers
- [ ] Rosters tab has headers (data can be added later)
- [ ] Roster_Requirements has all 5 weeks
- [ ] Sheet shared with service account email (Viewer access)
- [ ] Sheet ID copied from URL

Your sheet is ready! 🎉

---

**Next Step:** Copy your Sheet ID and add it to `.env` file in your app.
