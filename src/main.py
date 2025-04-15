from msReserve import ReservationRequest, MSReserve
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- Flask Setup ---
app = Flask(__name__)
CORS(app)
ms_reserve = MSReserve()

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

if __name__ == '__main__':
    app.run(port=5000)
