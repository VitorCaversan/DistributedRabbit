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

    def consume_approved_payment(self, callback):
        self.approved_payment_queue.consume(callback)

    def consume_denied_payment(self, callback):
        self.denied_payment_queue.consume(callback)

    def consume_ticket_generated(self, callback):
        self.ticket_generated_queue.consume(callback)

    def std_callback(self, ch, method, properties, body):
        print(f"Received message: {body.decode('utf-8')}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

        return
