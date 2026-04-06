import json
import os
import subprocess
import threading

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask import session, redirect
from functools import wraps

load_dotenv()

app = Flask(__name__)
lock = threading.Lock()

# configs
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "127.0.0.1")
DEBUG = bool(os.getenv("DEBUG") in ["True", "true", "1"])
TUNNEL_SCRIPT = os.getenv("TUNNEL_SCRIPT")
TUNNEL_KILL_SCRIPT = os.getenv("TUNNEL_KILL_SCRIPT")
TUNNEL_DIR = os.getenv("TUNNEL_DIR", os.path.expanduser("~/misc_sh"))

API_TOKEN = os.getenv("API_TOKEN")
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", 0.9))
DEFAULT_RATE = float(os.getenv("DEFAULT_RATE", 1))
DEFAULT_PITCH = float(os.getenv("DEFAULT_PITCH", 1))

def check_auth():
    return session.get("auth") == True

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not check_auth():
            return jsonify({"error": "unauthorized"}), 403
        return f(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_auth():
    return {
        "auth": session.get("auth", False)
    }

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    token = request.args.get("token")

    if token == API_TOKEN:
        session["auth"] = True
        return redirect("/")  # volta pro painel

    return "unauthorized", 403

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route('/vibrate')
@login_required
def vibrate():
    os.system("termux-vibrate -d 500")
    return jsonify({"status": "ok"})

@app.route('/fala')
@login_required
def fala():
    msg = request.args.get('msg', '')
    volume = float(request.args.get('volume', DEFAULT_VOLUME))
    rate = float(request.args.get('rate', DEFAULT_RATE))
    pitch = float(request.args.get('pitch', DEFAULT_PITCH))

    if not msg:
        return jsonify({"status": "error", "msg": "Mensagem vazia"})

    with lock:
        try:
            output = subprocess.check_output(["termux-volume"])
            volumes = json.loads(output)

            music = next(v for v in volumes if v["stream"] == "music")
            original_volume = music["volume"]
            max_volume = music["max_volume"]

            temp_volume = int(max_volume * volume)

            subprocess.run(["termux-volume", "music", str(temp_volume)])

            subprocess.run([
                "termux-tts-speak",
                "-r", str(rate),
                "-p", str(pitch),
                msg
            ])

        finally:
            subprocess.run(["termux-volume", "music", str(original_volume)])

    return jsonify({"status": "ok"})

@app.route('/status_data')
def status_data():
    def safe(cmd):
        try:
            return json.loads(subprocess.check_output(cmd))
        except:
            return {}

    battery = safe(["termux-battery-status"])
    wifi = safe(["termux-wifi-connectioninfo"])
    device = safe(["termux-deviceinfo"])

    return jsonify({
        "battery": battery,
        "wifi": wifi,
        "device": device
    })

@app.route('/tunel/start')
@login_required
def start_tunel():
    porta = request.args.get("porta", "5000")

    subprocess.Popen([
        "/data/data/com.termux/files/usr/bin/bash",
        TUNNEL_SCRIPT,
        porta,
        "cloud"
    ])

    return jsonify({"status": "ok", "porta": porta})

@app.route('/tunel/stop')
@login_required
def stop_tunel():
    porta = request.args.get("porta")

    if not porta:
        return jsonify({"status": "error", "msg": "porta não informada"})

    subprocess.run([
        TUNNEL_KILL_SCRIPT,
        porta
    ])

    return jsonify({"status": "stopped", "porta": porta})

@app.route('/tunel/url')
def tunel_url():
    porta = request.args.get("porta", "5000")

    path = os.path.join(TUNNEL_DIR, f"current_tunnel_url_{porta}.txt")

    if os.path.exists(path):
        with open(path) as f:
            url = f.read().strip()
        return jsonify({"url": url})

    return jsonify({"url": None})

@app.route('/status')
def status():
    return render_template("status.html")

app.run(host=HOST, port=PORT, debug=DEBUG)