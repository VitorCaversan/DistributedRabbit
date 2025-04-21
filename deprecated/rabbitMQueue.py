import pika

class RabbitMQueue:
    """
    A class to manage publishing to and consuming from a single RabbitMQ queue.
    """

    def __init__(self, host: str, queue_name: str):
        self.queue_name = queue_name
        self.host = host

    def connect(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel    = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name)

    def publish(self, message: str):
        self.channel.basic_publish(exchange='',
                                   routing_key=self.queue_name,
                                   body=message)
        
        print(f"[x] Message sent to queue '{self.queue_name}': {message}")

    def consume(self, callback):
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=callback
        )
        print(f"[*] Waiting for messages in queue '{self.queue_name}'. Press CTRL+C to exit.")
        self.channel.start_consuming()

    def get_once(self, callback):
        method_frame, header_frame, body = self.channel.basic_get(
            queue=self.queue_name, 
            auto_ack=False
        )

        if method_frame:
            callback(self.channel, method_frame, header_frame, body)
        else:
            print("No messages in the queue right now.")

    def close(self):
        self.connection.close()
