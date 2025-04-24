import json, threading, pika, globalVars

class User(threading.Thread):

    def __init__(self, host="localhost", user_id=None):
        super().__init__(daemon=True)
        self.user_id = user_id
        self._buf : list[dict] = []
        self._lock = threading.Lock()

        # conexão/ canal
        self.conn = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.ch   = self.conn.channel()

        self.cruise_interest_to_add = None # Used only to subscribe to promotion on a callback

        if user_id is None:
            with open("../databank/cruises.json") as f:
                self.cruises_interests = [c["id"]
                                          for c in json.load(f)["itineraries"]]
        else:
            with open("../databank/users.json") as f:
                users = json.load(f)["users"]
            self.cruises_interests = next(
                (u["cruises_interests"] for u in users if u["id"] == user_id),
                []
            )

        exchange_name = globalVars.PROMOTION_EXCHANGE_NAME
        self.ch.exchange_declare(exchange=exchange_name,
                                 exchange_type='direct',
                                 durable=True)
        for cruise_id in self.cruises_interests:
            queue_name = globalVars.PROMOTION_QUEUE_NAME + str(cruise_id)
            routing_key = globalVars.PROMOTIONS_ROUTING_KEY + str(cruise_id)
            self.ch.queue_declare(queue=queue_name, durable=True)
            self.ch.queue_bind(exchange=exchange_name,
                               queue=queue_name,
                               routing_key=routing_key)
            self.ch.basic_consume(queue=queue_name,
                                  on_message_callback=self._on_promotion,
                                  auto_ack=False)


    def _on_promotion(self, _ch, _m, _p, body):
        with self._lock:
            self._buf.append(json.loads(body.decode()))

        msg = json.loads(body.decode('utf-8'))
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
            print(f"[User MS] Updated file cruise {cruise_id} price to {promotion_value}")
            json.dump(data, f, indent=2, ensure_ascii=False)
        _ch.basic_ack(delivery_tag=_m.delivery_tag)
        
        print("[User] promo ->", body.decode())

    def pop_promos(self):
        with self._lock:
            out, self._buf = self._buf, []
            return out

    def run(self):
        print("[User] Listening promotions…")
        self.ch.start_consuming()

    def do_subscribe(self):
        """
        Subscribes to the promotions for a specific cruise ID and adds this id
        on the cruises_interests array on the users json.
        """
        exchange_name = globalVars.PROMOTION_EXCHANGE_NAME
        queue_name = globalVars.PROMOTION_QUEUE_NAME + str(self.cruise_interest_to_add)
        routing_key = globalVars.PROMOTIONS_ROUTING_KEY + str(self.cruise_interest_to_add)
        self.ch.queue_declare(queue=queue_name, durable=True)
        self.ch.queue_bind(exchange=exchange_name,
                                queue=queue_name,
                                routing_key=routing_key)
        self.ch.basic_consume(queue=queue_name, on_message_callback=self.on_promotion)

        # Update user JSON
        with open('../databank/users.json', 'r') as file:
            data = json.load(file)
            users = data.get('users', [])
        users = users if isinstance(users, list) else []

        for user in users:
            if user['id'] == self.user_id:
                user['cruises_interests'].append(self.cruise_interest_to_add)
                print(f"[User MS] User ID {self.user_id} subscribed to cruise ID {self.cruise_interest_to_add}")
                break
        else:
            print(f"[User MS] User ID {self.user_id} not found in users.json")

        with open('../databank/users.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.cruise_interest_to_add = None

    def subscribe_to_promotion(self, cruise_id):
        self.cruise_interest_to_add = cruise_id

        # Thread-safe way to subscribe to a new queue and bind it to the exchange
        self.conn.add_callback_threadsafe(self.do_subscribe)

    def stop(self):
        self.conn.add_callback_threadsafe(self.ch.stop_consuming)
