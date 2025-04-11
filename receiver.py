import pika

connection_parameters = pika.ConnectionParameters('localhost')
connection = pika.BlockingConnection(connection_parameters)
channel = connection.channel()

channel.queue_declare(queue='created_reserve')

def callback(ch, method, properties, body):
    print("[x] Mensagem recebida:", body.decode('utf-8'))
    # Confirma o recebimento (ack) para remover a msg da fila
    ch.basic_ack(delivery_tag=method.delivery_tag)

# Iniciar o consumo da fila
channel.basic_consume(
    queue='created_reserve',
    on_message_callback=callback
)

print("[*] Esperando mensagens. Para sair, pressione CTRL+C")
channel.start_consuming()