# ms_reserve.py
import globalVars
import json
import pika

class MSPromotions:
    def __init__(self, host="localhost"):
        self.host = host
        self._connect()

        with open('../databank/cruises.json', 'r') as file:
            cruises = json.load(file)
            cruises = cruises.get('itineraries', [])
        self.cruises = cruises if isinstance(cruises, list) else []

        for cruise in self.cruises:
            exchange_name = globalVars.PROMOTION_EXCHANGE_NAME + str(cruise['id'])
            self.channel.exchange_declare(exchange=exchange_name,
                                          exchange_type='direct',
                                          durable=True)
            
    def _connect(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(self.host, heartbeat=30))
        self.channel = self.connection.channel()
        with open("../databank/cruises.json") as f:
            self.cruises = json.load(f)["itineraries"]
        for c in self.cruises:
            ex = f"{globalVars.PROMOTION_EXCHANGE_NAME}{c['id']}"
            self.channel.exchange_declare(exchange=ex,
                                          exchange_type="direct", durable=True)
    
    def _ensure(self):
        if self.connection.is_closed or self.channel.is_closed:
            try: self.connection.close()
            except: pass
            self._connect()
    

    def publish_promotion(self, cruise_id, promotion_value):
        self._ensure()
        ex = f"{globalVars.PROMOTION_EXCHANGE_NAME}{cruise_id}"
        msg = json.dumps(
            {"cruise_id": cruise_id, "promotion_value": promotion_value}
        ).encode()
        self.channel.basic_publish(
            exchange=ex,
            routing_key=globalVars.PROMOTIONS_ROUTING_KEY,
            body=msg,
            properties=pika.BasicProperties(content_type="application/json",
                                            delivery_mode=2))
        print("[Promotion MS] Published:", msg)

    def stop(self):
        self.connection.close()
        print("[Promotion MS] Connection closed.")


if __name__ == "__main__":
    msPromotions = MSPromotions()
    with open('../databank/cruises.json', 'r') as file:
        cruises = json.load(file)
        cruises = cruises.get('itineraries', [])
    cruises = cruises if isinstance(cruises, list) else []
    cruise_qty = len(cruises)
    
    while True:
        cruise_id = int(input("Enter cruise ID to publish promotion (or -1 to exit): "))
        if cruise_id == -1:
            print("Exiting...")
            break
        elif cruise_id < 1 or cruise_id > cruise_qty:
            print("Invalid cruise ID. Please try again.")
            continue
        promotion_value = int(input("Enter promotion value: "))
        msPromotions.publish_promotion(cruise_id, promotion_value)