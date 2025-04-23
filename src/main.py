from msReserve import ReservationRequest, MSReserve
from msPayment import MSPayment
from msTicket import MSTicket
from user import User
from flask import Flask, request, jsonify
from flask_cors import CORS
from wsgiref.simple_server import make_server
import threading
import signal
import sys
import time
import socket

# --- Flask Setup ---
app = Flask(__name__)
CORS(app)
ms_reserve  = MSReserve()
ms_payment  = MSPayment()
ms_ticket   = MSTicket()
main_user   = None
user_thread = None

import os
from flask import send_from_directory

# diretórios absolutos
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONT_DIR  = os.path.join(BASE_DIR, "frontend")
DATA_DIR   = os.path.join(BASE_DIR, "databank")

# ---------- páginas HTML / assets ----------
@app.route("/")
def index():
    return send_from_directory(FRONT_DIR, "index.html")

@app.route("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONT_DIR, filename)

# ---------- arquivos JSON ----------
@app.route("/databank/<path:filename>")
def databank_files(filename):
    return send_from_directory(DATA_DIR, filename)


@app.route('/reserve', methods=['POST'])
def reserve():
    try:
        data = request.get_json()
        reservation = ReservationRequest(**data)
        ms_reserve.reserve_cruise(reservation)   # agenda publicação
        return jsonify({"status": "Reservation created and published!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    payload = request.get_json()
    user_id = payload.get('id')

    global main_user
    global user_thread

    if user_id > 0 and not main_user:
        main_user = User(user_id=user_id)
        user_thread = threading.Thread(target=main_user.run, daemon=True)
        user_thread.start()

    if user_id < 1 or not main_user:
        return jsonify({'status': 'error', 'error': 'User could not be created'}), 404

    return jsonify({'status': 'success'})

@app.route("/status/<int:rid>")
def status(rid):
    st = ms_reserve.get_status(rid)
    if st is None:
        return jsonify({"error": "unknown reservation"}), 404
    return jsonify(st)

def main():
    """
    Main function to run the Flask app and all the microservices in sepparate threads.
    """
    # Make a WSGI server around Flask app
    httpd = make_server('localhost', 5000, app)

    # Flask app
    flask_thread = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.1), daemon=True)
    # MSReserve
    ms_reserve_thread = threading.Thread(target=ms_reserve.run, daemon=True)
    # MSPayment
    ms_payment_thread = threading.Thread(target=ms_payment.run, daemon=True)
    # MSTicket
    ms_ticket_thread = threading.Thread(target=ms_ticket.run, daemon=True)

    # Shutdown logic
    def _shutdown(sig, frame):
        print("\n🛑 SIGINT received, shutting down…")
        # stop consuming on each service
        ms_reserve.stop()
        ms_payment.stop()
        ms_ticket.stop()
        if main_user:
            main_user.stop()
        # stop the HTTP server
        # wake the HTTP server's select() so shutdown() can return
        try:
            sock = socket.create_connection(('localhost', 5000), timeout=1)
            sock.close()
        except:
            pass
        httpd.shutdown()

    signal.signal(signal.SIGINT, _shutdown)

    # Start threads
    for t in (flask_thread, ms_reserve_thread, ms_payment_thread, ms_ticket_thread):
        t.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt: # If signal.SIGINT is not working
        # This is a fallback in case the signal handler doesn't work
        print("\n🛑  SIGINT received, shutting down…")
        ms_reserve.stop()
        ms_payment.stop()
        ms_ticket.stop()
        if main_user:
            main_user.stop()

        # wake the HTTP server's select() so shutdown() can return
        try:
            sock = socket.create_connection(('localhost', 5000), timeout=1)
            sock.close()
        except:
            pass
        httpd.shutdown()

    # Wait for threads to finish
    for t in (flask_thread, ms_reserve_thread, ms_payment_thread, ms_ticket_thread):
        print(f"Waiting for {t.name} to finish...")
        t.join()

    if user_thread:
        print(f"Waiting for {user_thread.name} to finish...")
        user_thread.join()

    print("✅ All services stopped cleanly.")
    sys.exit(0)

if __name__ == '__main__':
    main()
