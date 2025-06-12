import json, threading, pika, globalVars
from flask_sse import sse

class User(threading.Thread):

    def __init__(self, host="localhost", user_id=None, flask_app=None):
        super().__init__(daemon=True)
        self.user_id = user_id
        self.flask_app = flask_app
        self._buf : list[dict] = []
        self._lock = threading.Lock()

        # conexão/ canal
        self.conn = pika.BlockingConnection(pika.ConnectionParameters(host))
        self.ch   = self.conn.channel()

        self.cruise_interest_to_add = None # Used only to subscribe to promotion on a callback
        self.consumer_tag = None
        self.wants_promo = 0

        if user_id is None:
            self.wants_promo = 1
        else:
            with open("../databank/users.json") as f:
                users = json.load(f)["users"]
            self.wants_promo = next(u["wants_promo"] for u in users if u["id"] == user_id)

        exchange_name = globalVars.PROMOTION_EXCHANGE_NAME
        self.ch.exchange_declare(exchange=exchange_name,
                                 exchange_type='direct',
                                 durable=True)
        self.setup_promo_consumer()

    def _on_promotion(self, _ch, _m, _p, body):
        if self.wants_promo == 0:
            print("[User MS] User does not want promotions, ignoring message")
            _ch.basic_ack(delivery_tag=_m.delivery_tag)
            return
        
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
        
        with self.flask_app.app_context():
            sse.publish(
                {"cruise_id": cruise_id, "promotion_value": promotion_value},
                type="promotion",
                channel=f"user-{self.user_id}"
            )


        print("[User] promo ->", body.decode())

    def pop_promos(self):
        with self._lock:
            out, self._buf = self._buf, []
            return out

    def setup_promo_consumer(self):
        queue = f"{globalVars.PROMOTION_QUEUE_NAME}_ {self.user_id}"
        key   = globalVars.PROMOTIONS_ROUTING_KEY
        exch  = globalVars.PROMOTION_EXCHANGE_NAME

        self.ch.queue_declare(queue=queue, durable=True)
        self.ch.queue_bind(exchange=exch, queue=queue, routing_key=key)

        self.consumer_tag = self.ch.basic_consume(
            queue=queue,
            on_message_callback=self._on_promotion,
            auto_ack=False
        )

    def disable_promotions(self):
        self.wants_promo = 0

        # Update user JSON
        with open('../databank/users.json', 'r') as file:
            data = json.load(file)
            users = data.get('users', [])
        users = users if isinstance(users, list) else []

        for user in users:
            if user['id'] == self.user_id:
                user['wants_promo'] = 0
                print(f"[User MS] User ID {self.user_id} unsubscribed to promotions")
                break
        else:
            print(f"[User MS] User ID {self.user_id} not found in users.json")

        with open('../databank/users.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


    def enable_promotions(self):
        self.wants_promo = 1

        # Update user JSON
        with open('../databank/users.json', 'r') as file:
            data = json.load(file)
            users = data.get('users', [])
        users = users if isinstance(users, list) else []

        for user in users:
            if user['id'] == self.user_id:
                user['wants_promo'] = 1
                print(f"[User MS] User ID {self.user_id} subscribed to promotions")
                break
        else:
            print(f"[User MS] User ID {self.user_id} not found in users.json")

        with open('../databank/users.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def set_wants_promo(self, flag: bool):
        if flag and not self.wants_promo:
            self.enable_promotions()
        else:
            self.disable_promotions()

    def run(self):
        print("[User] Running user ", self.user_id)
        self.ch.start_consuming()

    def stop(self):
        self.conn.add_callback_threadsafe(self.ch.stop_consuming)
