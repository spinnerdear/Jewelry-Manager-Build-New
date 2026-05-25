import base64
import json
import subprocess
import os
import re
from datetime import datetime

# Configuration
REPO = "spinnerdear/Jewelry-Manager-Build-New"
BASE_DIR = "/Users/ksdear/Documents/JewelryManager"
MAIN_FILE = "jewelry_manager_v1_9.py"

def get_version():
    try:
        with open(os.path.join(BASE_DIR, MAIN_FILE), "r", encoding="utf-8") as f:
            content = f.read()
            m = re.search(r'self\.version = "([^"]+)"', content)
            return m.group(1) if m else "Unknown"
    except: return "Unknown"

def upload_unified():
    version = get_version()
    print(f"📦 Preparing Unified Release for v{version}...")
    
    files = [
        (os.path.join(BASE_DIR, MAIN_FILE), "jewelry_manager.py"),
        (os.path.join(BASE_DIR, "README.md"), "README.md")
    ]

    # To do a single commit for multiple files via API is complex, 
    # but we can at least make sure they trigger only ONE action run 
    # by using the proper Git commands if available, or just updating them rapidly.
    
    # Best approach for Single Action: Use Git Push instead of API for multiple files
    try:
        os.chdir(BASE_DIR)
        # Check if it's a git repo
        if not os.path.exists(".git"):
            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{REPO}.git"], check=True)
        
        # Copy main file to the name GitHub expects
        shutil.copy2(MAIN_FILE, "jewelry_manager.py")
        
        subprocess.run(["git", "add", "jewelry_manager.py", "README.md"], check=True)
        commit_msg = f"🚀 Release v{version} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        
        # Use GH CLI to push to handle authentication
        subprocess.run(["gh", "auth", "setup-git"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        
        print(f"✅ Successfully pushed v{version} in a single commit!")
        print(f"🔗 View Action: https://github.com/{REPO}/actions")
        
    except Exception as e:
        print(f"❌ Error during Unified Push: {e}")
        print("Falling back to API upload...")
        # (Fallback code here if needed, but git push is cleaner for single action)

if __name__ == "__main__":
    import shutil
    upload_unified()
