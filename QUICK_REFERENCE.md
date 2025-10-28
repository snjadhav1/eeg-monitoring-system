# 📋 QUICK REFERENCE CARD

## 🔑 Your Clever Cloud Credentials Template

**Copy this to your .env file:**

```env
MYSQL_HOST=your-value-here
MYSQL_PORT=3306
MYSQL_USER=your-value-here
MYSQL_PASSWORD=your-value-here
MYSQL_DATABASE=your-value-here
```

---

## ⚡ Quick Commands Cheat Sheet

### Install Dependencies
```powershell
pip install -r requirements.txt
```

### Test Database Connection
```powershell
python test_db_connection.py
```

### Run Application Locally
```powershell
python app.py
```
Then open: http://localhost:5000

### Deploy to Clever Cloud
```powershell
# First time only
git init
git add .
git commit -m "Initial commit"
git remote add clever YOUR_CLEVER_CLOUD_GIT_URL

# Deploy (first time and updates)
git push clever master

# For updates later:
git add .
git commit -m "Updated application"
git push clever master
```

---

## 🗺️ Where to Find Things in Clever Cloud Dashboard

| What You Need | Where to Find It |
|---------------|------------------|
| **Database Credentials** | MySQL Add-on → Environment Variables |
| **Git URL** | Application → Information → Git Remote |
| **Add Environment Variables** | Application → Environment Variables → Add a variable |
| **View App Logs** | Application → Logs |
| **Your Live URL** | Application → Domain names |
| **Start/Stop App** | Application → Overview → Start/Stop button |

---

## ✅ Deployment Checklist

Before deploying, make sure you:

- [ ] Filled in all values in .env file
- [ ] Tested connection with test_db_connection.py
- [ ] Added environment variables in Clever Cloud dashboard
- [ ] Committed all your code to git
- [ ] Pushed to Clever Cloud
- [ ] Checked logs for errors
- [ ] Visited your live URL

---

## 🆘 Emergency Fixes

### Database not connecting?
```powershell
# 1. Verify credentials
python test_db_connection.py

# 2. Check .env file has no spaces
# CORRECT: MYSQL_HOST=value
# WRONG:   MYSQL_HOST = value
```

### App not showing changes?
```powershell
# Clear cache and redeploy
git add .
git commit -m "Force update"
git push clever master --force
```

### Can't access live website?
1. Check Clever Cloud dashboard → Application → Logs
2. Make sure environment variables are set
3. Restart app: Dashboard → Overview → Restart

---

## 📞 Support Resources

- **Clever Cloud Docs:** https://www.clever-cloud.com/doc/
- **Python/Flask Issues:** Check app logs in Clever Cloud
- **Database Issues:** Verify MySQL add-on is running

---

## 🎯 Files You Created/Modified

| File | Purpose |
|------|---------|
| `.env` | Stores database credentials (NEVER commit to git!) |
| `.gitignore` | Protects .env from being uploaded |
| `requirements.txt` | Lists Python packages to install |
| `app.py` | Modified to use Clever Cloud database |
| `test_db_connection.py` | Test script to verify database works |
| `BEGINNER_GUIDE.md` | Full step-by-step guide |
| `CLEVER_CLOUD_SETUP.md` | Setup instructions |

---

## 🔒 Security Reminders

- ✅ .env file is protected by .gitignore
- ✅ Never share your database password
- ✅ Always use environment variables for credentials
- ✅ Check .env is NOT in your git commits: `git status`

---

## 🎉 Success Indicators

**Local testing works if:**
- ✅ `python test_db_connection.py` shows "SUCCESS"
- ✅ `python app.py` shows "Connected to MySQL"
- ✅ http://localhost:5000 loads your website

**Deployment works if:**
- ✅ `git push clever master` completes without errors
- ✅ Your Clever Cloud app URL loads the website
- ✅ Data saves to database (check in Clever Cloud dashboard)

---

**Need detailed instructions? Open BEGINNER_GUIDE.md**
