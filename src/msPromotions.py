# ms_reserve.py
import globalVars
import json
import pika

class MSPromotions:
    """
    MSPromotion class. A publisher that publishes promotions to many exchanges that are bound to the
    promotions queues. The User will listen to these queues and make notifications to the user
    logged in if the promotion is valid for the cruise they are looking for.
    """
    def __init__(self, host='localhost'):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()

        # creates one exchange for each cruise declared in database/cruises.json
        with open('../databank/cruises.json', 'r') as file:
            cruises = json.load(file)
            cruises = cruises.get('itineraries', [])
        self.cruises = cruises if isinstance(cruises, list) else []

        for cruise in self.cruises:
            exchange_name = globalVars.PROMOTION_EXCHANGE_NAME + str(cruise['id'])
            self.channel.exchange_declare(exchange=exchange_name,
                                          exchange_type='direct',
                                          durable=True)
    
    def publish_promotion(self, cruise_id, promotion_value):
        """
        Publishes a promotion to the exchange corresponding to the cruise ID.
        """
        exchange_name = globalVars.PROMOTION_EXCHANGE_NAME + str(cruise_id)
        payload = {"cruise_id": cruise_id, "promotion_value": promotion_value}
        message = json.dumps(payload).encode('utf-8')
        self.channel.basic_publish(exchange=exchange_name,
                                   routing_key=globalVars.PROMOTIONS_ROUTING_KEY,
                                   body=message,
                                   properties=pika.BasicProperties(
                                       content_type="application/json",
                                       delivery_mode=2  # make message persistent
                                   ))
        print(f"[Promotion MS] Published promotion: {message}")

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