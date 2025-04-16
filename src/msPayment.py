# ms_reserve.py
from msReserve import ReservationRequest
import globalVars
import json
import pika

class MSPayment:
    """
    MSPayment class to handle payment approval and denial after a reservation is done
    in the created_reserve queue.
    """
    def __init__(self, host='localhost'):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=globalVars.CREATED_RESERVE_NAME)
        self.channel.queue_declare(queue=globalVars.APPROVED_PAYMENT_NAME)
        self.channel.queue_declare(queue=globalVars.DENIED_PAYMENT_NAME)

    def run(self):
        def on_created_reserve(ch, method, properties, body):
            reservation = ReservationRequest(**json.loads(body.decode('utf-8')))
            print(f"[Payment MS] Received: {body.decode('utf-8')}")

            # Decide whether to approve or deny
            if reservation.price < 1000:
                ch.basic_publish(exchange='', routing_key=globalVars.APPROVED_PAYMENT_NAME, body='Payment approved!')
            else:
                ch.basic_publish(exchange='', routing_key=globalVars.DENIED_PAYMENT_NAME, body='Payment denied!')
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=globalVars.CREATED_RESERVE_NAME, on_message_callback=on_created_reserve)
        print("[Payment MS] Listening on created_reserve...")
        self.channel.start_consuming()
    
    def stop(self):
        self.connection.close()
        print("[Payment MS] Connection closed.")