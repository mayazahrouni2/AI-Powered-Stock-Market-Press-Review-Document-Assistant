import logging
from flask import Flask, jsonify
from flask_cors import CORS
from threading import Thread
import os

base_path = r"C:\Users\hp\Desktop\stage d'ete bourse"
LOG_FILE = os.path.join(base_path, "agent.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

app = Flask(__name__)
CORS(app)

status = {"running": False, "message": "✅ Prêt à démarrer"}

def run_agent():
    global status
    try:
        logging.info("🚀 Lancement de l’agent IA (scraping & résumé)...")
        status["running"] = True
        status["message"] = "⏳ Agent en cours d'exécution..."

        from agent_final import agent
        agent()

        logging.info("✅ Agent terminé avec succès.")
        status["message"] = "✅ Agent terminé avec succès"
    except Exception as e:
        logging.error(f"❌ Erreur pendant l’exécution de l’agent : {e}")
        status["message"] = f"❌ Erreur : {e}"
    finally:
        status["running"] = False
        logging.info("ℹ️ Agent stoppé (thread terminé).")

@app.route('/start', methods=['GET'])
def start():
    global status
    if status["running"]:
        logging.warning("⚠️ Tentative de relancer l’agent alors qu’il tourne déjà.")
        return jsonify({"message": "⚠️ L'agent est déjà en cours d'exécution."})
    else:
        Thread(target=run_agent).start()
        logging.info("▶️ Endpoint /start appelé → agent() lancé dans un thread.")
        return jsonify({"message": "🚀 Agent lancé !"})

@app.route('/status', methods=['GET'])
def check_status():
    logging.info("📡 Endpoint /status interrogé.")
    return jsonify(status)

@app.route('/stop', methods=['GET'])
def stop():
    global status
    if status["running"]:
        status["running"] = False
        status["message"] = "🛑 Agent stoppé manuellement."
        logging.info("🛑 Agent forcé à l’arrêt via endpoint /stop.")
        return jsonify({"message": "🛑 Agent arrêté."})
    else:
        logging.info("ℹ️ Endpoint /stop appelé mais aucun agent en cours.")
        return jsonify({"message": "ℹ️ Aucun agent en cours."})

if __name__ == '__main__':
    logging.info("🌐 API Flask démarrée sur http://localhost:5000")
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=5000)
    except ImportError:
        logging.warning("⚠️ Waitress non installé, Flask tourne en mode dev.")
        app.run(host="0.0.0.0", port=5000)
