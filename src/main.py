from msReserve import ReservationRequest, MSReserve
from msPayment import MSPayment
from msTicket import MSTicket
from user import User
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time
import json

# --- Flask Setup ---
app = Flask(__name__)
CORS(app)
ms_reserve  = MSReserve()
ms_payment  = MSPayment()
ms_ticket   = MSTicket()
main_user   = None
user_thread = None

@app.route('/reserve', methods=['POST'])
def reserve():
    try:
        data = request.get_json()
        reservation = ReservationRequest(
            id=data['id'],
            ship=data['ship'],
            departure_date=data['departure_date'],
            embark_port=data['embark_port'],
            return_port=data['return_port'],
            visited_places=data['visited_places'],
            nights=data['nights'],
            price=data['price'],
            passenger_count=data.get('passenger_count', 1),
            cabins=data.get('cabins', 1)
        )
        ms_reserve.reserve_cruise(reservation)
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

def main():
    """
    Main function to run the Flask app and all the microservices in sepparate threads.
    """
    # Flask app
    flask_thread = threading.Thread(target=app.run, kwargs={'port': 5000, 'use_reloader': False, 'debug': False}, daemon=True)
    # MSReserve
    ms_reserve_thread = threading.Thread(target=ms_reserve.run, daemon=True)
    # MSPayment
    ms_payment_thread = threading.Thread(target=ms_payment.run, daemon=True)
    # MSTicket
    ms_ticket_thread = threading.Thread(target=ms_ticket.run, daemon=True)

    # Start threads
    flask_thread.start()
    ms_reserve_thread.start()
    ms_payment_thread.start()
    ms_ticket_thread.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            ms_reserve.stop()
            flask_thread.join()
            ms_reserve_thread.join()
            ms_payment_thread.join()
            ms_ticket_thread.join()
            if user_thread:
                user_thread.join()
            if main_user:
                main_user.stop()
            break

    return 1

if __name__ == '__main__':
    main()
