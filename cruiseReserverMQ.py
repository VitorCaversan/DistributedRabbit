import pika

connection_parameters = pika.ConnectionParameters('localhost')
connection = pika.BlockingConnection(connection_parameters)
channel = connection.channel()

channel.queue_declare(queue='created_reserve')

msg = 'Hello, RabbitMQ!'

channel.basic_publish(
    exchange='',
    routing_key='created_reserve',
    body=msg
)

print("[x] Enviado:", msg)

connection.close()