import os, sys, time, socket, signal, threading, json
from wsgiref.simple_server import make_server
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from msReserve  import MSReserve, ReservationRequest
from msPayment  import MSPayment
from msTicket   import MSTicket
from user       import User

BASE_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONT_DIR = os.path.join(BASE_DIR, "frontend")
DATA_DIR  = os.path.join(BASE_DIR, "databank")

app = Flask(__name__, static_folder=FRONT_DIR, static_url_path="")
CORS(app)

ms_reserve = MSReserve()
ms_payment = MSPayment()
ms_ticket  = MSTicket()

main_user   = None
user_thread = None
promo_user  = User(user_id=None)

@app.route("/") 
def index():
    return send_from_directory(FRONT_DIR, "index.html")

@app.route("/databank/<path:fname>")
def databank(fname):
    return send_from_directory(DATA_DIR, fname)

@app.route("/promos")
def promos():
    return jsonify(main_user.pop_promos() if main_user else [])

@app.route("/reserve", methods=["POST"])
def reserve():
    reservation = ReservationRequest(**request.get_json())
    ms_reserve.reserve_cruise(reservation)
    return jsonify(status="Reservation created and published!")

@app.route("/status/<int:rid>")
def status(rid):
    st = ms_reserve.get_status(rid)
    return (jsonify(st) if st
            else (jsonify(error="unknown reservation"), 404))

@app.route("/favicon.ico")
def favicon():
    return "", 204

PORT = 5050

def start():
    httpd = make_server("127.0.0.1", PORT, app)

    threads = [
        threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.1),
                         daemon=True, name="HTTP"),
        threading.Thread(target=ms_reserve.run, daemon=True, name="MSReserve"),
        threading.Thread(target=ms_payment.run, daemon=True, name="MSPayment"),
        threading.Thread(target=ms_ticket.run,  daemon=True, name="MSTicket"),
        promo_user
    ]
    for t in threads:
        t.start()

    def shutdown(*_):
        ms_reserve.stop(); ms_payment.stop(); ms_ticket.stop(); promo_user.stop()
        if main_user: main_user.stop()
        try:
            socket.create_connection(("127.0.0.1", PORT), 1).close()
        except:
            pass
        httpd.shutdown()

    signal.signal(signal.SIGINT, shutdown)

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        shutdown()

    for t in threads:
        t.join()
    if user_thread:
        user_thread.join()
    sys.exit(0)

@app.route("/login", methods=["POST"])
def login():
    global main_user, user_thread
    uid = request.get_json().get("id", 0)
    if uid and main_user is None:
        main_user   = User(user_id=uid)
        user_thread = threading.Thread(target=main_user.run, daemon=True)
        user_thread.start()
    return (jsonify(status="success") if main_user
            else (jsonify(status="error", error="User could not be created"), 404))

if __name__ == "__main__":
    print(f"⇢  http://127.0.0.1:{PORT}/  (Ctrl-C para sair)")
    start()
