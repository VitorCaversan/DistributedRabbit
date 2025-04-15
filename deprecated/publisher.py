from rabbitMQueue import RabbitMQueue

class Publisher:
    """
    Publisher class to handle message publishing to different RabbitMQ queues.
    """

    def __init__(self, host: str):
        self.created_reserve_queue  = RabbitMQueue(host, 'created_reserve_queue')
        self.approved_payment_queue = RabbitMQueue(host, 'approved_payment_queue')
        self.denied_payment_queue   = RabbitMQueue(host, 'denied_payment_queue')
        self.ticket_generated_queue = RabbitMQueue(host, 'ticket_generated_queue')

    def publish_created_reserve(self, message):
        self.created_reserve_queue.publish(message)
    
    def publish_approved_payment(self, message):
        self.approved_payment_queue.publish(message)

    def publish_denied_payment(self, message):
        self.denied_payment_queue.publish(message)

    def publish_ticket_generated(self, message):
        self.ticket_generated_queue.publish(message)

    def close(self):
        self.created_reserve_queue.close()
        self.approved_payment_queue.close()
        self.denied_payment_queue.close()
        self.ticket_generated_queue.close()