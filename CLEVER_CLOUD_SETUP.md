# 🚀 CLEVER CLOUD SETUP GUIDE - STEP BY STEP

## ✅ **STEP-BY-STEP INSTRUCTIONS**

### **📌 STEP 1: Fill in Your Database Credentials**

1. **Open the `.env` file** in this folder
2. **Go to your Clever Cloud dashboard** in your browser
3. **Click on your MySQL add-on**
4. **Click "Environment Variables"** on the left sidebar
5. **Copy each value** and paste into `.env`:

   **From Clever Cloud** → **To .env file:**
   - Copy `MYSQL_ADDON_HOST` → Paste as `MYSQL_HOST=`
   - Copy `MYSQL_ADDON_PORT` → Paste as `MYSQL_PORT=`
   - Copy `MYSQL_ADDON_USER` → Paste as `MYSQL_USER=`
   - Copy `MYSQL_ADDON_PASSWORD` → Paste as `MYSQL_PASSWORD=`
   - Copy `MYSQL_ADDON_DB` → Paste as `MYSQL_DATABASE=`

6. **Save the `.env` file**

**Example of completed .env:**
```
MYSQL_HOST=bxxxxxx-mysql.services.clever-cloud.com
MYSQL_PORT=3306
MYSQL_USER=uxxxxxx
MYSQL_PASSWORD=xxxxxxxxxxxxxxxxxx
MYSQL_DATABASE=bxxxxxx
```

---

### **📌 STEP 2: Install Required Packages**

1. **Open PowerShell** in this folder (right-click → "Open in Terminal")
2. **Run this command:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Wait for installation to complete**

---

### **📌 STEP 3: Test the Database Connection**

1. **In PowerShell, run:**
   ```powershell
   python test_db_connection.py
   ```
2. **You should see:**
   - ✅ Connected to MySQL successfully!
   - ✅ Tables created successfully!

   **If you see errors:**
   - Check your `.env` file has correct values
   - Make sure you copied from Clever Cloud exactly
   - Check your internet connection

---

### **📌 STEP 4: Run Your Application Locally**

1. **In PowerShell, run:**
   ```powershell
   python app.py
   ```
2. **Open your browser** and go to: http://localhost:5000
3. **Your app is now connected to Clever Cloud database!** 🎉

---

### **📌 STEP 5: Deploy to Clever Cloud (Make Website Live)**

1. **Install Git** (if not installed): https://git-scm.com/download/win

2. **In PowerShell, run these commands ONE BY ONE:**

   ```powershell
   # Initialize git repository
   git init

   # Add all files
   git add .

   # Commit files
   git commit -m "Initial commit"

   # Add Clever Cloud remote (GET THIS FROM YOUR CLEVER CLOUD DASHBOARD)
   # Go to: Your Application → Information → Copy the Git remote URL
   git remote add clever <PASTE_YOUR_CLEVER_CLOUD_GIT_URL_HERE>

   # Push to Clever Cloud
   git push clever master
   ```

3. **Clever Cloud will automatically:**
   - Install Python packages from requirements.txt
   - Set up environment variables
   - Deploy your application
   - Give you a live URL!

4. **Get your live URL:**
   - Go to Clever Cloud dashboard
   - Click on your application
   - Look for the "Domain names" section
   - Your app URL will be something like: `app-xxxxx.cleverapps.io`

---

## 🔧 **TROUBLESHOOTING**

### **Problem: Can't connect to database**
**Solution:**
- Double-check `.env` file has correct credentials
- Make sure no extra spaces in `.env` file
- Verify MySQL add-on is running in Clever Cloud dashboard

### **Problem: Tables not created**
**Solution:**
- Run `python test_db_connection.py` to create tables
- Or run your app once - tables will be created automatically

### **Problem: Git push fails**
**Solution:**
- Make sure you're using the correct Git URL from Clever Cloud
- Try: `git push clever master --force` (if needed)

---

## 📝 **IMPORTANT SECURITY NOTES**

1. ✅ **NEVER** commit `.env` file to GitHub
2. ✅ `.gitignore` file already protects `.env`
3. ✅ In Clever Cloud dashboard, add environment variables manually:
   - Go to: Application → Environment Variables
   - Add each variable from your `.env` file

---

## 🎯 **WHAT CHANGED IN YOUR CODE**

1. ✅ Added `python-dotenv` to load environment variables
2. ✅ Updated `get_db_connection()` to use Clever Cloud credentials
3. ✅ Added connection pooling for better performance
4. ✅ Increased timeout for cloud connections (30 seconds)
5. ✅ Your local code works the same - just connects to cloud database now!

---

## 🌐 **ENVIRONMENT VARIABLES FOR CLEVER CLOUD**

When deploying, add these in Clever Cloud dashboard:

| Variable Name    | Value (from your Clever Cloud MySQL) |
|------------------|--------------------------------------|
| MYSQL_HOST       | bxxxxxx-mysql.services.clever-cloud.com |
| MYSQL_PORT       | 3306 |
| MYSQL_USER       | uxxxxxx |
| MYSQL_PASSWORD   | your-password |
| MYSQL_DATABASE   | bxxxxxx |

**How to add them:**
1. Clever Cloud Dashboard → Your Application
2. Click "Environment variables" (left sidebar)
3. Click "Add a variable"
4. Enter name and value
5. Click "Update changes"

---

## ✨ **YOU'RE DONE!**

Your website is now connected to Clever Cloud MySQL database!
Both local testing and live deployment will use the cloud database.

**Need help?** Check the troubleshooting section above.
