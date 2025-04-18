# ms_reserve.py
from dataclasses import dataclass, asdict
import globalVars
import json
import pika

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
    """
    MSReserve class to handle cruise reservation requests.
    It publishes reservation requests to a the created_reserve queue and
    listens for payment approval and denial messages from the respective queues,
    taking actions based on the received messages.
    It also listens for ticket generation messages and creates tickets after that.
    """
    def __init__(self, host='localhost'):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=globalVars.CREATED_RESERVE_NAME)
        self.channel.queue_declare(queue=globalVars.APPROVED_PAYMENT_NAME)
        self.channel.queue_declare(queue=globalVars.DENIED_PAYMENT_NAME)
        self.channel.queue_declare(queue=globalVars.TICKET_GENERATED_NAME)

    def reserve_cruise(self, reservation: ReservationRequest):
        message = json.dumps(asdict(reservation))
        self.channel.basic_publish(exchange='',
                                   routing_key=globalVars.CREATED_RESERVE_NAME,
                                   body=message)
        return "Reservation published"

    def run(self):
        def on_approved_payment(ch, method, properties, body):
            print(f"[Reserve MS] Payment approved: {body.decode('utf-8')}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        def on_denied_payment(ch, method, properties, body):
            print(f"[Reserve MS] Payment denied: {body.decode('utf-8')}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=globalVars.APPROVED_PAYMENT_NAME, on_message_callback=on_approved_payment)
        self.channel.basic_consume(queue=globalVars.DENIED_PAYMENT_NAME, on_message_callback=on_denied_payment)
        print("[Reserve MS] Listening on approved_payment and denied_payment...")
        self.channel.start_consuming()
    
    def stop(self):
        self.connection.close()
        print("[Reserve MS] Connection closed.")