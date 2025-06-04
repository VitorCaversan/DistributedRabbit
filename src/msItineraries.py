# ms_reserve.py
from verif_signature import verify_sig, InvalidSignature
import globalVars
import json
import pika

class MSItineraries:
    """
    msItineraries class to handle itinerary management for cruise reservations.
    It receives a REST api post request to return the available itineraries.
    It listens for the created_reserve and cancelled_reserve queues to update the itineraries with
    the correct amount of available seats.
    """
    def __init__(self, host='localhost'):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()
        
        for queue_name in [
            globalVars.CREATED_RESERVE_Q_NAME,
            globalVars.CANCELLED_RESERVE_Q_NAME,
        ]:
            self.channel.queue_declare(queue=queue_name)

    def run(self):
        def on_created_reserve(ch, method, properties, body):
            msg = json.loads(body.decode('utf-8'))
            cruise_id = msg['cruise_id']

            with open('../databank/cruises.json', 'r') as file:
                data = json.load(file)

            for itin in data.get('itineraries', []):
                if itin.get('id') == cruise_id:
                    itin['available_cabins'] = itin['available_cabins'] - 1
                    print(f"[Itineraries MS] Updated cruise {cruise_id} available cabins to {itin['available_cabins']}")
                    break
            else:
                print(f"[Itineraries MS] No itinerary found with id {cruise_id}")

            with open('../databank/cruises.json', 'w', encoding='utf-8') as f:
                print(f"[Itineraries MS] Updated file cruise {cruise_id} available cabins")
                json.dump(data, f, indent=2, ensure_ascii=False)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        def on_cancelled_reserve(ch, method, properties, body):
            msg = json.loads(body.decode('utf-8'))
            cruise_id = msg['cruise_id']

            with open('../databank/cruises.json', 'r') as file:
                data = json.load(file)

            for itin in data.get('itineraries', []):
                if itin.get('id') == cruise_id:
                    itin['available_cabins'] = itin['available_cabins'] + 1
                    print(f"[Itineraries MS] Updated cruise {cruise_id} available cabins to {itin['available_cabins']}")
                    break
            else:
                print(f"[Itineraries MS] No itinerary found with id {cruise_id}")

            with open('../databank/cruises.json', 'w', encoding='utf-8') as f:
                print(f"[Itineraries MS] Updated file cruise {cruise_id} available cabins")
                json.dump(data, f, indent=2, ensure_ascii=False)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=globalVars.CREATED_RESERVE_Q_NAME, on_message_callback=on_created_reserve, auto_ack=False)
        self.channel.basic_consume(queue=globalVars.CANCELLED_RESERVE_Q_NAME, on_message_callback=on_cancelled_reserve, auto_ack=False)
        
        try:
            print("[Itineraries MS] Listening on all queues")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionsClosed:
            pass
        except pika.exceptions.ConnectionWrongStateError:
            pass
        finally:
            self.channel.close()
            self.connection.close()
            print("[Itineraries MS] Connection closed.")
    
    def stop(self):
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)