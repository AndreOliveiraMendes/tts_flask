import json
import os
import subprocess
import threading

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
lock = threading.Lock()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/vibrate')
def vibrate():
    os.system("termux-vibrate -d 500")
    return jsonify({"status": "ok"})

@app.route('/fala')
def fala():
    msg = request.args.get('msg', '')
    volume = float(request.args.get('volume', 0.9))
    rate = float(request.args.get('rate', 1))
    pitch = float(request.args.get('pitch', 1))

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
def start_tunel():
    porta = request.args.get("porta", "5000")

    subprocess.Popen([
        "/data/data/com.termux/files/usr/bin/bash",
        os.path.expanduser("~/misc_sh/tunear.sh"),
        porta,
        "cloud"
    ])

    return jsonify({"status": "ok", "porta": porta})

@app.route('/tunel/stop')
def stop_tunel():
    porta = request.args.get("porta")

    if not porta:
        return jsonify({"status": "error", "msg": "porta não informada"})

    subprocess.run([
        os.path.expanduser("~/misc_sh/tunel_kill.sh"),
        porta
    ])

    return jsonify({"status": "stopped", "porta": porta})

@app.route('/tunel/status')
def tunel_status():
    try:
        out = subprocess.check_output(["pgrep", "-f", "cloudflared"])
        return jsonify({"running": True})
    except:
        return jsonify({"running": False})

@app.route('/tunel/url')
def tunel_url():
    porta = request.args.get("porta", "5000")

    path = os.path.expanduser(f"~/misc_sh/current_tunnel_url_{porta}.txt")

    if os.path.exists(path):
        with open(path) as f:
            url = f.read().strip()
        return jsonify({"url": url})

    return jsonify({"url": None})

@app.route('/status')
def status():
    return render_template("status.html")

app.run(host="0.0.0.0", port=5000)
