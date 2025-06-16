from flask import Flask, request
import hmac
import hashlib
import os
import subprocess

app = Flask(__name__)

GITHUB_SECRET = b''  # optional


@app.route("/payload", methods=["POST"])
def payload():
    # (Optional) verify signature
    if GITHUB_SECRET:
        signature = request.headers.get("X-Hub-Signature-256")
        body = request.get_data()
        expected = 'sha256=' + hmac.new(GITHUB_SECRET, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return "Invalid signature", 403

    # Run deploy script
    subprocess.Popen(["/home/gennis/deploy_bot.sh"])
    return "Updated", 200


if __name__ == "__main__":
    app.run(port=9000)  # use any port
