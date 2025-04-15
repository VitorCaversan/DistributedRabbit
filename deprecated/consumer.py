from rabbitMQueue import RabbitMQueue

class Consumer:
    """
    Consumer class to handle RabbitMQ message consumption.
    It declares the same queues as the publisher and consumes messages from them.
    """

    def __init__(self, host : str):
        self.host = host
        self.created_reserve_queue  = RabbitMQueue(host, 'created_reserve_queue')
        self.approved_payment_queue = RabbitMQueue(host, 'approved_payment_queue')
        self.denied_payment_queue   = RabbitMQueue(host, 'denied_payment_queue')
        self.ticket_generated_queue = RabbitMQueue(host, 'ticket_generated_queue')

    def consume_created_reserve(self, callback):
        self.created_reserve_queue.consume(callback)
    def get_once_created_reserve(self, callback):
        self.created_reserve_queue.connect()
        self.created_reserve_queue.get_once(callback)
        self.created_reserve_queue.close()

    def consume_approved_payment(self, callback):
        self.approved_payment_queue.consume(callback)
    def get_once_approved_payment(self, callback):
        self.approved_payment_queue.connect()
        self.approved_payment_queue.get_once(callback)
        self.approved_payment_queue.close()

    def consume_denied_payment(self, callback):
        self.denied_payment_queue.consume(callback)
    def get_once_denied_payment(self, callback):
        self.denied_payment_queue.connect()
        self.denied_payment_queue.get_once(callback)
        self.denied_payment_queue.close()

    def consume_ticket_generated(self, callback):
        self.ticket_generated_queue.consume(callback)
    def get_once_ticket_generated(self, callback):
        self.ticket_generated_queue.connect()
        self.ticket_generated_queue.get_once(callback)
        self.ticket_generated_queue.close()

    def std_callback_without_ack(self, ch, method, properties, body):
        print(f"Received message once: {body.decode('utf-8')}")

    def std_callback_with_ack(self, ch, method, properties, body):
        print(f"Received message: {body.decode('utf-8')}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

        return
