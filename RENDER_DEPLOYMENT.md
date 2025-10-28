# 🚀 RENDER DEPLOYMENT GUIDE
## Deploy Your EEG Monitoring System to Render

---

## 📋 WHAT YOU NEED

✅ **Files Ready:**
- `requirements.txt` - All Python packages (UPDATED ✅)
- `Procfile` - Tells Render how to run your app (CREATED ✅)
- `runtime.txt` - Specifies Python version (CREATED ✅)
- `.env` - Local credentials (DO NOT upload to Git!)
- All your project files

✅ **Accounts:**
- GitHub account (to upload code)
- Render account (for hosting) - Free tier available!
- Clever Cloud MySQL database (already have ✅)

---

## 🎯 STEP-BY-STEP DEPLOYMENT

### **PHASE 1: Prepare Your Code for GitHub**

#### Step 1: Make Sure .gitignore is Set Up
Your `.gitignore` file already protects sensitive data. Verify it contains:
```
.env
__pycache__/
*.pyc
*.db
```

#### Step 2: Initialize Git Repository (if not done)
```powershell
# In your project folder, run:
git init
git add .
git commit -m "Initial commit - EEG monitoring system"
```

#### Step 3: Create GitHub Repository
1. **Go to GitHub.com**
2. **Click "New Repository"** (top-right, green button)
3. **Name it:** `eeg-monitoring-system`
4. **Make it Public** (required for free Render hosting)
5. **DO NOT** check "Initialize with README" (you already have code)
6. **Click "Create repository"**

#### Step 4: Push Code to GitHub
```powershell
# Copy the commands from GitHub (they'll look like this):
git remote add origin https://github.com/YOUR_USERNAME/eeg-monitoring-system.git
git branch -M main
git push -u origin main
```

**✅ VERIFY:** Go to your GitHub repo - you should see all your files EXCEPT `.env`

---

### **PHASE 2: Deploy to Render**

#### Step 1: Create Render Account
1. **Go to:** https://render.com/
2. **Click "Get Started for Free"**
3. **Sign up with GitHub** (easiest - click "Sign up with GitHub")
4. **Authorize Render** to access your GitHub

#### Step 2: Create New Web Service
1. **Click "New +"** button (top-right)
2. **Select "Web Service"**
3. **Connect your GitHub repository:**
   - If asked, click "Configure account"
   - Grant access to your `eeg-monitoring-system` repo
4. **Select** your `eeg-monitoring-system` repository

#### Step 3: Configure Web Service

**Fill in the settings:**

| Setting | Value |
|---------|-------|
| **Name** | `eeg-monitoring-system` (or any name you like) |
| **Region** | Choose closest to you |
| **Branch** | `main` |
| **Root Directory** | (leave blank) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120` |
| **Instance Type** | `Free` |

#### Step 4: Add Environment Variables
**CRITICAL:** You must add your database credentials!

1. **Scroll down** to "Environment Variables" section
2. **Click "Add Environment Variable"**
3. **Add these ONE BY ONE:**

| Key | Value |
|-----|-------|
| `MYSQL_HOST` | `b6j7l1hhpzjv6qll63yh-mysql.services.clever-cloud.com` |
| `MYSQL_PORT` | `3306` |
| `MYSQL_USER` | `uyu4ekvclteohe9c` |
| `MYSQL_PASSWORD` | `40jhl8t6X4CvhJ6dG92Z` |
| `MYSQL_DATABASE` | `b6j7l1hhpzjv6qll63yh` |
| `PYTHON_VERSION` | `3.12.3` |

#### Step 5: Deploy!
1. **Click "Create Web Service"** (bottom of page)
2. **Wait 3-5 minutes** while Render:
   - ✅ Downloads your code
   - ✅ Installs Python packages
   - ✅ Starts your application
3. **Watch the logs** for any errors

#### Step 6: Get Your Live URL
1. **Once deployment succeeds**, you'll see: "Your service is live 🎉"
2. **Your URL** will be: `https://eeg-monitoring-system-XXXX.onrender.com`
3. **Click the URL** to open your website!

---

## ✅ VERIFY DEPLOYMENT

### Test Your Live Website:

1. **Open your Render URL** in browser
2. **You should see** your EEG monitoring welcome page
3. **Test the endpoints:**
   - `/` - Welcome page ✅
   - `/dashboard` - Main dashboard ✅
   - `/students-page` - Students page ✅
   - `/session-history` - Session history ✅

### Check Database Connection:
1. **Look at Render logs** (in Render dashboard)
2. **You should see:**
   ```
   ✅ Connected to MySQL: b6j7l1hhpzjv6qll63yh-mysql...
   ✅ Database tables initialized successfully
   ```

---

## 🔧 TROUBLESHOOTING

### ❌ **Build Failed**

**Error:** "Could not install requirements"
- **Fix:** Check `requirements.txt` is in root folder
- **Fix:** Make sure no typos in package names

**Error:** "Python version not found"
- **Fix:** Add environment variable: `PYTHON_VERSION=3.12.3`

---

### ❌ **Deployment Failed**

**Error:** "Application failed to start"
- **Fix:** Check Start Command is exactly:
  ```
  gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
  ```
- **Fix:** Verify `app.py` exists in root folder

**Error:** "Module not found"
- **Fix:** Add missing package to `requirements.txt`
- **Fix:** Trigger redeploy (push any change to GitHub)

---

### ❌ **Website Loads But Database Errors**

**Error:** "Database connection failed"
- **Fix:** Verify ALL 5 environment variables are added in Render
- **Fix:** No extra spaces in environment variable values
- **Fix:** MySQL credentials are correct (check Clever Cloud)

**Error:** "Table doesn't exist"
- **Fix:** App will auto-create tables on first run
- **Fix:** Check Render logs for database init messages

---

### ❌ **Website is Slow**

**Issue:** Free tier "spins down" after 15 min of inactivity
- **Solution:** Upgrade to paid plan ($7/month) for always-on
- **Workaround:** First request after idle takes 30-60 seconds (normal)

---

## 🔄 UPDATING YOUR DEPLOYED APP

### Method 1: Push to GitHub (Recommended)

1. **Make changes** to your code locally
2. **Commit changes:**
   ```powershell
   git add .
   git commit -m "Updated feature X"
   git push origin main
   ```
3. **Render auto-deploys** when it detects GitHub changes! (takes 2-3 min)

### Method 2: Manual Deploy

1. **Go to Render dashboard**
2. **Click your service**
3. **Click "Manual Deploy"** → "Deploy latest commit"

---

## 📊 MONITORING YOUR APP

### View Logs:
1. **Render Dashboard** → Your Service → **"Logs"** tab
2. **See real-time logs** of your app
3. **Check for errors** or connection issues

### Check Metrics:
1. **Render Dashboard** → Your Service → **"Metrics"** tab
2. **See:**
   - CPU usage
   - Memory usage
   - Request count

---

## 💰 RENDER PRICING

**Free Tier (Perfect for Testing):**
- ✅ 750 hours/month free
- ✅ Auto-sleeps after 15 min inactivity
- ✅ 512 MB RAM
- ✅ Shared CPU
- ⚠️ First request after sleep is slow (30-60s)

**Starter Plan ($7/month):**
- ✅ Always on (no sleeping)
- ✅ 512 MB RAM
- ✅ Faster response times
- ✅ Custom domains

---

## 🎯 YOUR DEPLOYED URLS

**Local Development:**
- http://localhost:5000 (when running `python app.py`)

**Production (Render):**
- https://eeg-monitoring-system-XXXX.onrender.com
- (Your actual URL will be shown in Render dashboard)

**Database:**
- Clever Cloud MySQL (already set up ✅)
- Accessible from anywhere
- Shared between local & production

---

## 📝 FILES CREATED FOR DEPLOYMENT

| File | Purpose |
|------|---------|
| `requirements.txt` | Lists all Python packages (UPDATED ✅) |
| `Procfile` | Tells Render how to start app |
| `runtime.txt` | Specifies Python 3.12.3 |
| `render.yaml` | Render configuration reference |
| `.gitignore` | Protects secrets from Git |

---

## ✅ DEPLOYMENT CHECKLIST

**Before deploying:**
- [ ] Code pushed to GitHub
- [ ] `.env` file NOT in GitHub (check with `git status`)
- [ ] `requirements.txt` is complete and updated
- [ ] `Procfile` exists
- [ ] `runtime.txt` exists

**During deployment:**
- [ ] Created Render account
- [ ] Connected GitHub repository
- [ ] Added all 5 environment variables
- [ ] Set Start Command correctly
- [ ] Selected Free tier

**After deployment:**
- [ ] Deployment succeeded (green checkmark)
- [ ] Website loads at Render URL
- [ ] Can see welcome page
- [ ] Dashboard loads correctly
- [ ] Database connection works

---

## 🎉 CONGRATULATIONS!

Your EEG Monitoring System is now:
- ✅ **Live on the internet** (Render)
- ✅ **Connected to cloud database** (Clever Cloud)
- ✅ **Accessible from anywhere**
- ✅ **Automatically deploys** when you push to GitHub
- ✅ **Production-ready** and scalable!

**Share your URL with the world!** 🌍

---

## 🆘 NEED HELP?

**Render Issues:**
- Check Render logs (Dashboard → Logs)
- Render Discord: https://discord.gg/render
- Render Docs: https://render.com/docs

**Database Issues:**
- Verify Clever Cloud MySQL is running
- Check environment variables in Render
- Test connection with `test_db_connection.py` locally

**App Issues:**
- Check app logs in Render dashboard
- Test locally first: `python app.py`
- Verify all files are in GitHub

---

**Good luck with your deployment! 🚀**
