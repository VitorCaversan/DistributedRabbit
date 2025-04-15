# ms_reserve.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from dataclasses import dataclass, asdict
from rabbitMQueue import RabbitMQueue

@dataclass
class ReservationRequest:
    ship: str
    departure_date: str
    embark_port: str
    return_port: str
    visited_places: list
    nights: int
    price: float
    passenger_count: int = 1
    cabins: int = 1

class MSReserve:
    def __init__(self, host='localhost'):
        self.queue = RabbitMQueue(host, 'created_reserve_queue')
        self.queue.connect()

    def reserve_cruise(self, reservation: ReservationRequest):
        message = json.dumps(asdict(reservation))
        self.queue.publish(message)
        return "Reservation published"

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
