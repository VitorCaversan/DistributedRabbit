# ms_reserve.py
from msReserve import ReservationRequest
import globalVars
import json
import pika
import os
import base64
# For signatures
from cryptography.hazmat.primitives.serialization import load_pem_private_key

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
        self.channel.exchange_declare(exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
                                      exchange_type='direct',
                                      durable=True)
        self.channel.queue_declare(queue=globalVars.DENIED_PAYMENT_NAME)

        # Get private key from file
        _PRIV_PATH = os.getenv("MSPAYMENT_PRIV_KEY")
        with open(_PRIV_PATH, "rb") as f:
            self._private_key = load_pem_private_key(f.read(), password=None)

    def run(self):
        def on_created_reserve(ch, method, properties, body):
            reservation = ReservationRequest(**json.loads(body.decode('utf-8')))
            print(f"[Payment MS] Received: {body.decode('utf-8')}")

            # Decide whether to approve or deny
            if reservation.price < 1000:
                payload = {"reserve_id": reservation.id, "status": "APPROVED"}
                out_body = json.dumps(payload).encode('utf-8')
                
                # Sign the payload with private key
                sig = base64.b64encode(self._private_key.sign(out_body)).decode('utf-8')

                self.channel.basic_publish(
                    exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
                    routing_key=globalVars.APPROVED_PAYMENT_ROUTING_KEY,
                    body=out_body,
                    properties=pika.BasicProperties(
                        content_type="application/json",
                        headers={"sig_alg": "ed25519", "sig": sig},
                        delivery_mode=2          # make message persistent
                    )
                )
            else:
                payload = {"reserve_id": reservation.id, "status": "DENIED"}
                out_body = json.dumps(payload).encode('utf-8')

                # Sign the payload with private key
                sig = base64.b64encode(self._private_key.sign(out_body)).decode('utf-8')

                ch.basic_publish(exchange='',
                                 routing_key=globalVars.DENIED_PAYMENT_NAME,
                                 body=out_body,
                                 properties=pika.BasicProperties(
                                    content_type="application/json",
                                    headers={"sig_alg": "ed25519", "sig": sig},
                                    delivery_mode=2          # make message persistent
                                 )
                                )
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=globalVars.CREATED_RESERVE_NAME, on_message_callback=on_created_reserve)
        
        try:
            print("[Payment MS] Listening on all queues")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionsClosed:
            pass
        except pika.exceptions.ConnectionWrongStateError:
            pass
        finally:
            self.channel.close()
            self.connection.close()
            print("[Payment MS] Connection closed.")
    
    def stop(self):
        # thread‑safe way to break out of start_consuming
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)