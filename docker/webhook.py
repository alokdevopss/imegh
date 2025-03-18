from flask import Flask, request
import requests
import os

app = Flask(__name__)

ARGOCD_SERVER = os.getenv("ARGOCD_SERVER")
ARGOCD_TOKEN = os.getenv("ARGOCD_TOKEN")

def update_sync_status(app_name, approve):
    url = f"{ARGOCD_SERVER}/api/v1/applications/{app_name}/sync"
    headers = {"Authorization": f"Bearer {ARGOCD_TOKEN}"}

    if approve:
        payload = {"dryRun": False}  # Proceed with sync
    else:
        payload = {"dryRun": True}   # Cancel sync

    response = requests.post(url, json=payload, headers=headers, verify=False)
    return response.status_code, response.text

@app.route("/approve", methods=["GET"])
def approve():
    app_name = request.args.get("app")
    status_code, response = update_sync_status(app_name, True)
    return f"Approved sync for {app_name}. Response: {response}"

@app.route("/reject", methods=["GET"])
def reject():
    app_name = request.args.get("app")
    status_code, response = update_sync_status(app_name, False)
    return f"Rejected sync for {app_name}. Response: {response}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

