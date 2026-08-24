import os, socket, sys, threading, time, traceback, webview
from io import BytesIO
import pandas as pd
from flask import Flask, render_template, request, jsonify
from automation import run_playwright
from db import (get_absences_by_date, update_absences, delete_absences_bulk,
                get_eleves, add_eleve, delete_eleves_bulk,
                get_encadrants, add_encadrant, delete_encadrant)

app = Flask(__name__)

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

LOG_PATH = os.path.join(APP_DIR, "automation_error.log")


def safe_run_playwright(date):
    """Wrapper qui capture toute exception du thread et l'écrit dans un fichier log,
    car une exception dans un thread daemon est sinon totalement silencieuse
    (surtout dans l'exe packagé sans console)."""
    try:
        run_playwright(date)
    except Exception:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n--- Erreur automation ({date}) ---\n")
            f.write(traceback.format_exc())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/absences")
def absences():
    date = request.args.get("date")
    if not date:
        return jsonify([])
    return jsonify(get_absences_by_date(date))

@app.route("/api/absences/delete", methods=["POST"])
def delete_absences():
    ids = request.json.get("ids", [])
    delete_absences_bulk(ids)
    return jsonify({"status": "ok"})


@app.route("/api/save", methods=["POST"])
def save():
    rows = request.json
    try:
        update_absences(rows)
    except Exception:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("\n--- Erreur update_absences ---\n")
            f.write(traceback.format_exc())
        return jsonify({"status": "error", "error": "Erreur lors de l'enregistrement en base."}), 500

    date = rows[0]["date"]
    threading.Thread(target=safe_run_playwright, args=(date,), daemon=True).start()
    return jsonify({"status": "ok"})


@app.route("/api/eleves", methods=["GET", "POST"])
def handle_eleves():
    if request.method == "GET":
        search = request.args.get("search", "")
        return jsonify(get_eleves(search))
    elif request.method == "POST":
        add_eleve(request.json)
        return jsonify({"status": "ok"})


@app.route("/api/eleves/delete", methods=["POST"])
def delete_eleves():
    codes = request.json.get("codes", [])
    delete_eleves_bulk(codes)
    return jsonify({"status": "ok"})


@app.route("/api/eleves/upload", methods=["POST"])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({"error": "Aucun fichier reçu"}), 400

    file = request.files['file']
    try:
        raw = file.read()
        try:
            df = pd.read_excel(BytesIO(raw))
        except Exception:
            # Massar exports souvent un .xls dont le contenu est en fait du HTML
            df = pd.read_html(BytesIO(raw))[0]

        df["nom_complet"] = (
            df["Nom"].astype(str).str.strip() + " " + df["Prénom"].astype(str).str.strip()
        )

        count = 0
        for _, row in df.dropna(subset=["CNE"]).iterrows():
            add_eleve({
                "nom": row["nom_complet"],
                "classe": row["Classe"],
                "code": str(row["CNE"])
            })
            count += 1

        return jsonify({"status": "ok", "message": f"{count} élèves importés."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/encadrants", methods=["GET", "POST", "DELETE"])
def handle_encadrants():
    if request.method == "GET":
        return jsonify(get_encadrants())
    elif request.method == "POST":
        add_encadrant(request.json)
        return jsonify({"status": "ok"})
    elif request.method == "DELETE":
        delete_encadrant(request.args.get("nom"))
        return jsonify({"status": "ok"})


def start_flask():
    app.run(port=2846, debug=False, use_reloader=False)


def wait_for_server(host="127.0.0.1", port=2846, timeout=10):
    """Bloque jusqu'à ce que Flask accepte des connexions, pour éviter que la
    fenêtre pywebview ne s'ouvre avant que le serveur soit prêt (page blanche/
    erreur silencieuse, aucune requête ne part jamais)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


if __name__ == "__main__":
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    wait_for_server()
    webview.create_window("Gestion des Absences - CPGE", "http://127.0.0.1:2846", width=1100, height=750)
    webview.start(debug=False)