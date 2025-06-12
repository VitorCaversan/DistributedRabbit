import os, sys, time, socket, signal, threading
from wsgiref.simple_server import make_server
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import globalVars as gv
import json
from msReserve     import MSReserve, ReservationRequest
from msPayment     import MSPayment
from msTicket      import MSTicket
from msItineraries import MSItineraries
from user          import User
from dataclasses import asdict
from flask_sse import sse 

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONT_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR  = os.path.join(BASE_DIR, "databank")

app = Flask(__name__, static_folder=FRONT_DIR, static_url_path="")
app.config["REDIS_URL"] = "redis://localhost:6379/0"
app.register_blueprint(sse, url_prefix="/stream")

CORS(app)

MS_ITINERARIES_URL = f"http://localhost:{gv.ITINERARIES_PORT}/itineraries"

ms_reserve = MSReserve()
ms_payment = MSPayment()
ms_ticket  = MSTicket()
ms_itineraries = MSItineraries()

users = {}
users_threads = {}

@app.route("/") 
def index():
    return send_from_directory(FRONT_DIR, "index.html")

@app.route("/databank/<path:fname>")
def databank(fname):
    return send_from_directory(DATA_DIR, fname)

@app.route("/promos/<int:user_id>")
def promos(user_id):
    return jsonify(users[user_id].pop_promos() if users.get(user_id) else [])

@app.route("/reserve", methods=["POST"])
def reserve():
    data = request.get_json()
    reservation = ReservationRequest(**data)
    ms_reserve.reserve_cruise(reservation)
    resp = requests.post(f"http://localhost:{gv.PAYMENT_PORT}/generate_payment", json=asdict(reservation))
    if resp.status_code == 200:
        pay_data = resp.json()
        return jsonify({
            "status"     : "Reservation created and published!",
            "payment_url": pay_data["payment_url"],
            "reserve_id" : reservation.id            # <<< NOVO
        })
    else:
        return jsonify({"status": "error", "details": "Could not create payment link"}), 502

@app.route("/favicon.ico")
def favicon():
    return "", 204

@app.route("/reserve/itineraries", methods=["GET"])
def fetch_available_itineraries():
    dest = request.args.get("dest")
    embark_port = request.args.get("embark_port")
    departure_date = request.args.get("departure_date")

    params = {}
    if dest:  params["dest"] = dest
    if embark_port:  params["embark_port"] = embark_port
    if departure_date:  params["departure_date"] = departure_date

    try:
        resp = requests.get(MS_ITINERARIES_URL, params=params, timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return  jsonify({"error": "Unable to fetch itineraries", "details": str(e)}), 502

    try:
        itineraries = resp.json()
    except ValueError:
        return jsonify({"error": "msItineraries returned invalid JSON"}), 502

    return jsonify(itineraries), 200

@app.route("/users/<int:user_id>/promotions", methods=["PUT"])
def toggle_promotions(user_id):
    # Expects JSON: { "wants_promo": true } or { "wants_promo": false }
    body = request.get_json(force=True)
    if "wants_promo" not in body:
        return jsonify({"error": "missing wants_promo"}), 400

    wants = bool(body["wants_promo"])

    if users.get(user_id) is None or users[user_id].user_id != user_id:
        return jsonify({"error": "user not logged in"}), 403
    users[user_id].set_wants_promo(wants)

    return jsonify({
        "user_id":      user_id,
        "wants_promo":  users[user_id].wants_promo
    }), 200

from werkzeug.serving import make_server

def start() -> None:
    """
    Sobe o HTTP em modo *threaded* para que a conexão SSE não bloqueie
    as outras requisições.  
    Mantém o mesmo esquema de threads para os micro-services.
    """
    # servidor HTTP capaz de atender em paralelo
    httpd = make_server("0.0.0.0",
                        gv.MAIN_PORT,
                        app,
                        threaded=True)          # ← aqui está o segredo!

    threads = [
        threading.Thread(target=httpd.serve_forever,
                         daemon=True,
                         name="HTTP"),
        threading.Thread(target=ms_reserve.run,
                         daemon=True,
                         name="MSReserve"),
        threading.Thread(target=ms_payment.run,
                         daemon=True,
                         name="MSPayment"),
        threading.Thread(target=ms_ticket.run,
                         daemon=True,
                         name="MSTicket"),
        threading.Thread(target=ms_itineraries.run,
                         daemon=True,
                         name="MSItineraries"),
    ]
    for t in threads:
        t.start()

    def shutdown(*_):
        ms_reserve.stop(); ms_payment.stop(); ms_ticket.stop(); ms_itineraries.stop()
        for u in users.values():
            if u is not None:
                u.stop()
        httpd.shutdown()

    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()

    for t in threads:
        t.join()
    sys.exit(0)

@app.get("/status/<int:rid>")
def current_status(rid: int):
    st = ms_reserve.get_status(rid)
    return (jsonify(st), 200) if st else (jsonify({"error": "not found"}), 404)

@app.route("/login", methods=["POST"])
def login():
    uid = request.get_json(force=True).get("id")
    if uid is None:
        return jsonify(status="error", error="missing id"), 400

    if uid not in users:
        users[uid] = User(user_id=uid, flask_app=app)
        t = threading.Thread(target=users[uid].run, daemon=True)
        users_threads[uid] = t
        t.start()

    return jsonify(status="success")

@app.route('/reserve/user/<int:user_id>', methods=['GET'])
def get_user_reservations(user_id):
    users_path = os.path.abspath('../databank/users.json')
    cruises_path = os.path.abspath('../databank/cruises.json')

    with open(users_path, 'r') as f:
        users = json.load(f).get("users", [])
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "Usuário não encontrado"}), 404

    reservations = user.get("reservations", [])
    if not reservations:
        return jsonify([])

    with open(cruises_path, 'r') as f:
        cruises = {c["id"]: c for c in json.load(f).get("itineraries", [])}

    reservas_detalhadas = []
    for r in reservations:
        cruise = cruises.get(r["cruise_id"])
        if cruise:
            reserva = {
                "cruise_id": r["cruise_id"],
                "ship": cruise["ship"],
                "departure_dates": cruise["departure_dates"],
                "embark_port": cruise["embark_port"],
                "return_port": cruise["return_port"],
                "visited_places": cruise["visited_places"],
                "nights": cruise["nights"],
                "price": cruise["price"],
                "reserved_passengers": r["passenger_count"],
                "reserved_cabins": r["cabins"]
            }
            reservas_detalhadas.append(reserva)

    return jsonify(reservas_detalhadas)

@app.route("/reserve/cancel", methods=["POST"])
def cancel_reservation():
    data = request.get_json(force=True)
    cruise_id = data.get("cruise_id")
    user_id = data.get("user_id")
    if not cruise_id or not user_id:
        return jsonify({"status": "error", "error": "Missing cruise_id or user_id"}), 400

    ms_reserve.publish_cancelled_reserve(cruise_id=cruise_id, user_id=user_id)
    return jsonify({"status": "success"})

if __name__ == "__main__":
    print(f"⇢  http://0.0.0.0:{gv.MAIN_PORT}/  (Ctrl-C para sair)")
    start()
