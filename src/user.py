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

        qname = self.ch.queue_declare(queue="", exclusive=True).method.queue
        for cid in self.cruises_interests:
            ex = f"{globalVars.PROMOTION_EXCHANGE_NAME}{cid}"
            self.ch.exchange_declare(exchange=ex, exchange_type="direct",
                                     durable=True)
            self.ch.queue_bind(exchange=ex, queue=qname,
                               routing_key=globalVars.PROMOTIONS_ROUTING_KEY)

        self.ch.basic_consume(queue=qname,
                              on_message_callback=self._on_promotion,
                              auto_ack=True)

    def _on_promotion(self, _ch, _m, _p, body):
        with self._lock:
            self._buf.append(json.loads(body.decode()))
        print("[User] promo ->", body.decode())

    def pop_promos(self):
        with self._lock:
            out, self._buf = self._buf, []
            return out

    def run(self):
        print("[User] Listening promotions…")
        self.ch.start_consuming()

    def stop(self):
        self.conn.add_callback_threadsafe(self.ch.stop_consuming)
