# ms_reserve.py
from dataclasses import dataclass, asdict
import globalVars
import json
import pika

@dataclass
class ReservationRequest:
    id: int
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
        self.channel.queue_declare(queue=globalVars.DENIED_PAYMENT_NAME)
        self.channel.queue_declare(queue=globalVars.TICKET_GENERATED_NAME)

        # Binds a queue to a direct exchange
        self.channel.exchange_declare(exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
                                      exchange_type="direct",
                                      durable=True)
        self.channel.queue_declare(queue=globalVars.APPROVED_PAYMENT_RESERVE_NAME, durable=True)
        self.channel.queue_bind(exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
                                queue=globalVars.APPROVED_PAYMENT_RESERVE_NAME,
                                routing_key=globalVars.APPROVED_PAYMENT_ROUTING_KEY)

    def reserve_cruise(self, reservation: ReservationRequest):
        message = json.dumps(asdict(reservation))
        self.channel.basic_publish(exchange='',
                                   routing_key=globalVars.CREATED_RESERVE_NAME,
                                   body=message)
        return "Reservation published"

    def run(self):
        def on_approved_payment(ch, method, properties, body):
            print(f"[Reserve MS] Received: {json.loads(body.decode('utf-8'))}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        def on_denied_payment(ch, method, properties, body):
            print(f"[Reserve MS] Received: {json.loads(body.decode('utf-8'))}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        def on_ticket_generated(ch, method, properties, body):
            print(f"[Reserve MS] Ticket generated: {body.decode('utf-8')}")
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=globalVars.APPROVED_PAYMENT_RESERVE_NAME, on_message_callback=on_approved_payment, auto_ack=False)
        self.channel.basic_consume(queue=globalVars.DENIED_PAYMENT_NAME, on_message_callback=on_denied_payment)
        self.channel.basic_consume(queue=globalVars.TICKET_GENERATED_NAME, on_message_callback=on_ticket_generated)
        
        try:
            print("[Reserve MS] Listening on all queues")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionsClosed:
            pass
        except pika.exceptions.ConnectionWrongStateError:
            pass
        finally:
            self.channel.close()
            self.connection.close()
            print("[Reserve MS] Connection closed.")
    
    def stop(self):
        # thread‑safe way to break out of start_consuming
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)