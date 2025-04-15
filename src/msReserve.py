# ms_reserve.py
from dataclasses import dataclass, asdict
from rabbitMQueue import RabbitMQueue
import json

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