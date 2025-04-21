import globalVars
import json
import pika

class User:
    """
    User class. A consumer that consumes messages from the promotions queues and
    makes notifications to the user logged in if the promotion is valid for the cruise
    it is looking for.
    """
    def __init__(self, host='localhost', user_id=None):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()

        with open('../databank/users.json', 'r') as file:
            users = json.load(file)
            users = users.get('users', [])
        users = users if isinstance(users, list) else []
        
        self.cruises_interests = []
        for user in users:
            if user['id'] == user_id:
                self.cruises_interests = user['cruises_interests']
                break

        for cruise_id in self.cruises_interests:
            exchange_name = globalVars.PROMOTION_EXCHANGE_NAME + str(cruise_id)
            self.channel.exchange_declare(exchange=exchange_name,
                                          exchange_type='direct',
                                          durable=True)
            queue_name = globalVars.PROMOTION_QUEUE_NAME + str(cruise_id)
            self.channel.queue_declare(queue=queue_name, durable=True)
            self.channel.queue_bind(exchange=exchange_name,
                                    queue=queue_name,
                                    routing_key=globalVars.PROMOTIONS_ROUTING_KEY)
    
    def on_promotion(self, ch, method, properties, body):
        msg = json.loads(body.decode('utf-8'))
        print(f"[User MS] Received promotion: {msg}")
        cruise_id = msg['cruise_id']
        promotion_value = msg['promotion_value']

        # 2. Load the existing itineraries JSON
        with open('../databank/cruises.json', 'r') as file:
            data = json.load(file)

        # 3. Find the matching itinerary and update its price
        for itin in data.get('itineraries', []):
            if itin.get('id') == cruise_id:
                itin['price'] = promotion_value
                print(f"[User MS] Updated cruise {cruise_id} price to {promotion_value}")
                break
        else:
            print(f"[User MS] No itinerary found with id {cruise_id}")

        # 4. Write the updated data back to the file
        with open('../databank/cruises.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        ch.basic_ack(delivery_tag=method.delivery_tag)
    
    def run(self):
        for cruise_id in self.cruises_interests:
            queue_name = globalVars.PROMOTION_QUEUE_NAME + str(cruise_id)
            self.channel.basic_consume(queue=queue_name, on_message_callback=self.on_promotion)

        print("[User MS] Listening for promotions...")
        self.channel.start_consuming()

    def subscribe_to_promotion(self, cruise_id):
        """
        Subscribes to the promotions for a specific cruise ID and adds this id
        on the cruises_interests array on the users json.
        """
        # Channel subscription
        self.channel.stop_consuming()

        exchange_name = globalVars.PROMOTION_EXCHANGE_NAME + str(cruise_id)
        queue_name = globalVars.PROMOTION_QUEUE_NAME + str(cruise_id)
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(exchange=exchange_name,
                                queue=queue_name,
                                routing_key=globalVars.PROMOTIONS_ROUTING_KEY)
        self.channel.basic_consume(queue=queue_name, on_message_callback=self.on_promotion)

        self.channel.start_consuming()

        # Update user JSON
        with open('../databank/users.json', 'r') as file:
            data = json.load(file)
            users = data.get('users', [])
        users = users if isinstance(users, list) else []

        for user in users:
            if user['id'] == self.user_id:
                user['cruises_interests'].append(cruise_id)
                print(f"[User MS] User ID {self.user_id} subscribed to cruise ID {cruise_id}")
                break
        else:
            print(f"[User MS] User ID {self.user_id} not found in users.json")

        with open('../databank/users.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def stop(self):
        self.connection.close()
        print("[User MS] Connection closed.")