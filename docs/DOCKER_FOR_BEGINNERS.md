# DOCKER FOR ABSOLUTE BEGINNERS
## Complete Step-by-Step Guide to Deploy BRLF System

---

## 🎯 WHAT IS DOCKER? (Simple Explanation)

**Think of Docker like this:**
- Your application is like a **TV show**
- Docker is like a **TV box** that plays the show
- The **container** is the TV box playing your specific show
- The **image** is like the DVD/file of the show

**Why Docker?**
- ✅ Works the same on any computer
- ✅ No "it works on my machine" problems
- ✅ Easy to start/stop/restart
- ✅ Everything self-contained

---

## 📋 STEP 1: INSTALL DOCKER (One-Time Setup)

### **Windows:**

1. **Download Docker Desktop:**
   - Go to: https://www.docker.com/products/docker-desktop
   - Click "Download for Windows"
   - File size: ~500MB

2. **Install:**
   - Double-click the downloaded file
   - Follow the installer (click Next → Next → Install)
   - Restart your computer when asked

3. **Verify Installation:**
   - Open Command Prompt (search "cmd" in Start menu)
   - Type: `docker --version`
   - You should see: `Docker version 24.0.x...`

### **Mac:**

1. **Download Docker Desktop:**
   - Go to: https://www.docker.com/products/docker-desktop
   - Click "Download for Mac"
   - Choose Intel or Apple Silicon based on your Mac

2. **Install:**
   - Open the .dmg file
   - Drag Docker to Applications
   - Open Docker from Applications

3. **Verify:**
   - Open Terminal
   - Type: `docker --version`

### **Linux (Ubuntu):**

1. **Open Terminal**

2. **Run these commands one by one:**
   ```bash
   # Update package list
   sudo apt update

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Add your user to docker group (so you don't need sudo)
   sudo usermod -aG docker $USER

   # Logout and login again for changes to take effect
   ```

3. **Verify:**
   ```bash
   docker --version
   ```

---

## 📦 STEP 2: UNDERSTAND DOCKER BASICS

### **Key Concepts (Super Simple):**

1. **Image** = Blueprint/Recipe
   - Like a recipe for a cake
   - Contains instructions to build your application
   - You don't eat the recipe, you use it to make a cake

2. **Container** = Running Application
   - Like the actual cake made from the recipe
   - You can have multiple cakes from one recipe
   - You can start, stop, restart cakes (containers)

3. **Docker Compose** = Multiple Containers Working Together
   - Your system has 2 containers:
     - **Backend**: Python application (does the processing)
     - **Frontend**: Web interface (what you see in browser)
   - Docker Compose starts both at once

### **Common Docker Commands:**

```bash
# See what's running
docker ps

# See all containers (running + stopped)
docker ps -a

# See all images on your computer
docker images

# Stop everything
docker-compose down

# Start everything
docker-compose up -d

# View logs (to see what's happening)
docker-compose logs -f

# Restart everything
docker-compose restart
```

---

## 🚀 STEP 3: DEPLOY BRLF SYSTEM (Actual Steps)

### **Prerequisites:**
- [x] Docker installed (from Step 1)
- [x] Downloaded: `brlf-web-system-v3.0.tar.gz`

### **Step-by-Step Deployment:**

#### **3.1 Extract the Files**

**Windows:**
```
1. Right-click on brlf-web-system-v3.0.tar.gz
2. Click "Extract All..."
3. Choose a location (e.g., C:\BRLF\)
4. Click "Extract"
```

**Mac/Linux:**
```bash
# Open Terminal
cd ~/Downloads  # or wherever your file is
tar -xzf brlf-web-system-v3.0.tar.gz
cd brlf-web-complete
```

#### **3.2 Open Terminal/Command Prompt**

**Windows:**
```
1. Open File Explorer
2. Navigate to the extracted folder (e.g., C:\BRLF\brlf-web-complete)
3. Click in the address bar at the top
4. Type: cmd
5. Press Enter
→ Command Prompt opens in that folder
```

**Mac:**
```
1. Open Terminal
2. Type: cd /path/to/brlf-web-complete
3. Press Enter
```

**Linux:**
```
1. Open Terminal
2. Type: cd /path/to/brlf-web-complete
3. Press Enter
```

#### **3.3 Start the System**

**In the terminal/command prompt, type:**

```bash
docker-compose up -d
```

**What happens:**
1. Docker reads `docker-compose.yml` file
2. Builds the backend (Python) - takes 2-3 minutes first time
3. Builds the frontend (React) - takes 3-5 minutes first time
4. Starts both containers
5. You see: "Creating brlf-backend ... done" and "Creating brlf-frontend ... done"

**The `-d` means "detached"** = runs in background (you can close terminal)

#### **3.4 Verify It's Running**

```bash
docker ps
```

**You should see:**
```
CONTAINER ID   IMAGE                  STATUS          PORTS
xxxxxxxxxxxx   brlf-web-complete_backend   Up 30 seconds   0.0.0.0:8000->8000/tcp
xxxxxxxxxxxx   brlf-web-complete_frontend  Up 30 seconds   0.0.0.0:3000->3000/tcp
```

**This means:**
- ✅ Backend running on port 8000
- ✅ Frontend running on port 3000
- ✅ System is ready!

#### **3.5 Access the Web Interface**

**Open your web browser and go to:**
```
http://localhost:3000
```

**You should see:**
- Beautiful BRLF web interface
- Upload button
- Processing options
- 🎉 **SUCCESS!**

---

## 📊 STEP 4: USE THE SYSTEM

### **Workflow:**

```
1. Open browser → http://localhost:3000

2. Click "Choose File" → Select your Excel file

3. Click "Upload File" → File uploads

4. Click "Start Processing" → AI processes automatically

5. Wait (progress bar shows status)
   - Small files (10K): 5-10 seconds
   - Large files (100K): 30-60 seconds

6. Download results:
   - Clean Data (for Sanket Portal)
   - Full Report (all changes)
   - Backup (original file)

7. Done! Upload clean file to Sanket Portal
```

---

## 🛠️ STEP 5: MANAGE THE SYSTEM

### **Stop the System:**
```bash
docker-compose down
```
**What happens:**
- Stops both containers
- Data is safe (stored in `data/` folder)
- You can start again anytime

### **Start the System:**
```bash
docker-compose up -d
```
**What happens:**
- Starts everything again
- Previous data still there
- Ready to use immediately

### **Restart the System:**
```bash
docker-compose restart
```
**Use when:**
- Something seems stuck
- After changing configuration
- As a quick fix

### **View Logs (See What's Happening):**
```bash
docker-compose logs -f
```
**Use when:**
- Something not working
- Want to debug
- Curious what's happening

**Press Ctrl+C to stop viewing logs**

### **Check Status:**
```bash
docker ps
```
**Shows:**
- Which containers are running
- How long they've been up
- Ports they're using

---

## 📁 STEP 6: UNDERSTAND THE FOLDERS

```
brlf-web-complete/
├── backend/              [Python AI code]
├── frontend/             [React web interface]
├── data/                 [YOUR DATA - DON'T DELETE!]
│   ├── uploads/         [Temporary uploaded files]
│   ├── outputs/         [Cleaned files - DOWNLOAD FROM HERE]
│   ├── backups/         [Original file backups]
│   ├── reports/         [Generated reports]
│   └── logs/            [System logs]
├── docker-compose.yml   [Main configuration]
└── docs/                [Documentation]
```

**Important:**
- ✅ `data/` folder contains ALL your processed files
- ✅ Even if you stop Docker, data/ folder remains
- ✅ You can copy files from data/outputs/ anytime
- ⚠️ Don't delete data/ folder!

---

## 🔧 STEP 7: COMMON ISSUES & FIXES

### **Issue 1: "docker: command not found"**
**Fix:**
- Docker not installed properly
- Restart computer after installing Docker
- Open a new terminal window

### **Issue 2: "port 3000 already in use"**
**Fix:**
```bash
# Stop any other programs using port 3000
# Or edit docker-compose.yml and change "3000:3000" to "3001:3000"
```

### **Issue 3: "Cannot connect to Docker daemon"**
**Fix:**
- Docker Desktop not running
- Open Docker Desktop application
- Wait for it to fully start (green light)

### **Issue 4: Website shows "Cannot connect"**
**Fix:**
```bash
# Check if containers are running
docker ps

# If not running, start them
docker-compose up -d

# Wait 30 seconds, then try again
```

### **Issue 5: "Out of space" or slow performance**
**Fix:**
```bash
# Clean up old Docker data
docker system prune -a

# This removes unused images and containers
# Frees up disk space
```

---

## 📖 STEP 8: VISUAL GUIDE

### **What You See:**

#### **Terminal/Command Prompt:**
```
C:\BRLF\brlf-web-complete> docker-compose up -d

Creating network "brlf_brlf-network" ... done
Creating brlf-backend  ... done
Creating brlf-frontend ... done
```

#### **Browser (http://localhost:3000):**
```
┌────────────────────────────────────────┐
│ 🌾 BRLF - Sanket Portal Migration    │
│ Intelligent Data Cleaning v3.0       │
├────────────────────────────────────────┤
│                                        │
│ 📁 Step 1: Upload File                │
│ [Choose File] [No file chosen]        │
│ [📤 Upload File]                       │
│                                        │
└────────────────────────────────────────┘
```

#### **Docker Desktop (if you open it):**
```
Containers
├── brlf-backend     [Running] [green dot]
└── brlf-frontend    [Running] [green dot]
```

---

## 🎓 STEP 9: DAILY USAGE

### **Morning (Start System):**
```bash
cd /path/to/brlf-web-complete
docker-compose up -d
# Wait 30 seconds
# Open browser: http://localhost:3000
```

### **During Day (Process Files):**
```
1. Upload file in browser
2. Click Process
3. Wait for completion
4. Download results
5. Repeat for next file
```

### **Evening (Stop System - Optional):**
```bash
docker-compose down
# System stops, data saved
```

**Note:** You can leave it running 24/7 if you want!

---

## 💡 STEP 10: PRO TIPS

### **Tip 1: Access from Other Computers**

If you want other people on your network to access:

1. **Find your computer's IP address:**
   - Windows: `ipconfig` in cmd → look for "IPv4 Address"
   - Mac/Linux: `ifconfig` → look for "inet"
   - Example: `192.168.1.100`

2. **Share this URL with team:**
   ```
   http://192.168.1.100:3000
   ```

3. **Make sure firewall allows port 3000**

### **Tip 2: Check Processed Files**

```bash
# See all cleaned files
ls data/outputs/

# Copy a file to desktop (Windows)
copy data\outputs\yourfile.xlsx C:\Users\YourName\Desktop\

# Copy a file to desktop (Mac/Linux)
cp data/outputs/yourfile.xlsx ~/Desktop/
```

### **Tip 3: Backup Everything**

```bash
# Backup the entire data folder
# Windows:
xcopy /E /I data C:\Backup\brlf-data

# Mac/Linux:
cp -r data ~/Backup/brlf-data
```

### **Tip 4: Update the System**

When I provide a new version:

```bash
# Stop current system
docker-compose down

# Remove old images
docker system prune -a

# Extract new version
# Run docker-compose up -d again
```

---

## ✅ CHECKLIST: ARE YOU READY?

```
□ Docker installed and running
□ Extracted brlf-web-complete folder
□ Opened terminal in that folder
□ Ran: docker-compose up -d
□ Saw: "Creating brlf-backend ... done"
□ Saw: "Creating brlf-frontend ... done"
□ Ran: docker ps (shows 2 containers)
□ Opened: http://localhost:3000 in browser
□ Saw: BRLF web interface
□ Tested: Uploaded a file
□ Tested: Processed a file
□ Tested: Downloaded results

✅ ALL DONE! System operational!
```

---

## 🚀 QUICK REFERENCE CARD

**Print this and keep it handy:**

```
═══════════════════════════════════════════
        BRLF SYSTEM - QUICK COMMANDS
═══════════════════════════════════════════

START SYSTEM:
  docker-compose up -d

STOP SYSTEM:
  docker-compose down

CHECK STATUS:
  docker ps

VIEW LOGS:
  docker-compose logs -f

RESTART:
  docker-compose restart

ACCESS WEB:
  http://localhost:3000

FIND DATA:
  data/outputs/

CLEAN UP:
  docker system prune -a

═══════════════════════════════════════════
```

---

## 📞 HELP & SUPPORT

**If something doesn't work:**

1. Check Docker Desktop is running
2. Run: `docker ps` - should show 2 containers
3. Run: `docker-compose logs` - see errors
4. Try: `docker-compose restart`
5. Last resort: `docker-compose down`, then `docker-compose up -d`

**Common Questions:**

Q: Do I need to run commands every time?
A: Only `docker-compose up -d` to start. It remembers everything else.

Q: Can I close the terminal?
A: Yes! The `-d` flag means it runs in background.

Q: Where are my files?
A: In `data/outputs/` folder. You can copy them anytime.

Q: How do I stop it?
A: `docker-compose down` or just close Docker Desktop.

Q: Can multiple people use it?
A: Yes! Just share your computer's IP + port 3000.

---

**🎉 CONGRATULATIONS! You now know Docker basics and can run the BRLF system!**

**Remember:** Docker is just a way to package and run applications. You don't need to understand everything - just these basic commands to start, stop, and manage your system.
