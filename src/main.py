from msReserve import ReservationRequest, MSReserve
from msPayment import MSPayment
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import time

# --- Flask Setup ---
app = Flask(__name__)
CORS(app)
ms_reserve = MSReserve()
ms_payment = MSPayment()

@app.route('/reserve', methods=['POST'])
def reserve():
    try:
        data = request.get_json()
        reservation = ReservationRequest(
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

    # Start threads
    flask_thread.start()
    ms_reserve_thread.start()
    ms_payment_thread.start()

    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            ms_reserve.stop()
            flask_thread.join()
            ms_reserve_thread.join()
            ms_payment_thread.join()
            break

    return 1

if __name__ == '__main__':
    main()
