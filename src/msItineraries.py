# ms_reserve.py
from verif_signature import verify_sig, InvalidSignature
import globalVars as gv
import json
import pika, threading
from flask import Flask, jsonify, request
from wsgiref.simple_server import make_server

app = Flask(__name__)

@app.route("/itineraries", methods=["GET"])
def get_itineraries():
    with open('../databank/cruises.json', 'r') as file:
            data = json.load(file)

    dest = request.args.get("dest", type=str)
    embark_port = request.args.get("embark_port", type=str) 
    departure_date = request.args.get("departure_date", type=str) 

    filtered = data.get('itineraries', [])

    if dest.lower() == "all":
        return jsonify(filtered), 200
    
    if dest:
        filtered = [it for it in filtered if (dest in it.get("visited_places", []))]

    if embark_port is not None:
        filtered = [it for it in filtered if it.get("embark_port").lower() == embark_port.lower()]

    if departure_date is not None:
        filtered = [it for it in filtered if (departure_date in it.get("departure_dates", []))]

    return jsonify(filtered), 200

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
            gv.CREATED_RESERVE_Q_NAME,
            gv.CANCELLED_RESERVE_Q_NAME,
        ]:
            self.channel.queue_declare(queue=queue_name)

        httpd = make_server("localhost", gv.ITINERARIES_PORT, app)
        print(f"msItineraries listening on :{gv.ITINERARIES_PORT}")
        threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.1),
                         daemon=True, name="HTTP_itineraries").start(),

    def run(self):
        def on_created_reserve(ch, method, properties, body):
            msg = json.loads(body.decode('utf-8'))
            cruise_id = msg.get('cruise_id', msg.get('id'))

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
            cruise_id = msg.get('cruise_id', msg.get('id'))

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

        self.channel.basic_consume(queue=gv.CREATED_RESERVE_Q_NAME, on_message_callback=on_created_reserve, auto_ack=False)
        self.channel.basic_consume(queue=gv.CANCELLED_RESERVE_Q_NAME, on_message_callback=on_cancelled_reserve, auto_ack=False)
        
        try:
            print("[Itineraries MS] Listening on all queues")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionClosed:
            pass
        except pika.exceptions.ConnectionWrongStateError:
            pass
        finally:
            self.channel.close()
            self.connection.close()
            print("[Itineraries MS] Connection closed.")

    
    def stop(self):
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)