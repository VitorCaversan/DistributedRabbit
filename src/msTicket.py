# ms_reserve.py
import globalVars
import json
import pika

class MSTicket:
    """
    MSTicket class to handle ticket generation after a reservation is done and the payment is approved.
    It listens for payment approval messages and generates tickets accordingly.
    """
    def __init__(self, host='localhost'):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()
        
        # Binds a queue to a direct exchange
        self.channel.exchange_declare(exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
                                      exchange_type="direct", durable=True)
        self.channel.queue_declare(queue=globalVars.APPROVED_PAYMENT_TICKET_NAME, durable=True)
        self.channel.queue_bind(exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
                                queue=globalVars.APPROVED_PAYMENT_TICKET_NAME,
                                routing_key=globalVars.APPROVED_PAYMENT_ROUTING_KEY)

        self.channel.queue_declare(queue=globalVars.TICKET_GENERATED_NAME)

    def run(self):
        def on_approved_payment(ch, method, properties, body):
            print(f"[Ticket MS] Received: {json.loads(body.decode('utf-8'))}")

            ch.basic_publish(exchange='', routing_key=globalVars.TICKET_GENERATED_NAME, body='Ticket generated!')
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=globalVars.APPROVED_PAYMENT_TICKET_NAME, on_message_callback=on_approved_payment)
        
        try:
            print("[Ticket MS] Listening on all queues")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionsClosed:
            pass
        except pika.exceptions.ConnectionWrongStateError:
            pass
        finally:
            self.channel.close()
            self.connection.close()
            print("[Ticket MS] Connection closed.")
    
    def stop(self):
        # thread‑safe way to break out of start_consuming
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)