import base64
import json
import subprocess
import os

REPO = "spinnerdear/Jewelry-Manager-Build-New"
FILE_NAME = "README.md"
LOCAL_PATH = "/Users/ksdear/Documents/JewelryManager/README.md"

def upload():
    with open(LOCAL_PATH, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    
    try:
        sha = subprocess.run(["gh", "api", f"/repos/{REPO}/contents/{FILE_NAME}", "--jq", ".sha"], capture_output=True, text=True).stdout.strip()
    except: sha = None

    payload = {"message": "Add README.md", "content": content}
    if sha: payload["sha"] = sha
    
    with open("tmp_up.json", "w") as f: json.dump(payload, f)
    subprocess.run(["gh", "api", "--method", "PUT", f"/repos/{REPO}/contents/{FILE_NAME}", "--input", "tmp_up.json"], check=True)
    print(f"✅ {FILE_NAME} uploaded to {REPO}.")

if __name__ == "__main__":
    upload()
    if os.path.exists("tmp_up.json"): os.remove("tmp_up.json")
