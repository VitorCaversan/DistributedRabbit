# ms_itineraries.py
from verif_signature import verify_sig, InvalidSignature
import globalVars as gv
import json
import pika, threading
from flask import Flask, jsonify, request
from wsgiref.simple_server import make_server
from msReserve import ReservationRequest
import os

app = Flask(__name__)

@app.route("/itineraries", methods=["GET"])
def get_itineraries():
    cruises_path = os.path.abspath('../databank/cruises.json')
    with open(cruises_path, 'r') as file:
        data = json.load(file)

    dest = request.args.get("dest", type=str)
    embark_port = request.args.get("embark_port", type=str) 
    departure_date = request.args.get("departure_date", type=str) 

    filtered = data.get('itineraries', [])

    if dest and dest.lower() == "all":
        return jsonify(filtered), 200
    
    if dest:
        before = len(filtered)
        filtered = [it for it in filtered if (dest in it.get("visited_places", []))]

    if embark_port is not None:
        before = len(filtered)
        filtered = [it for it in filtered if it.get("embark_port").lower() == embark_port.lower()]

    if departure_date is not None:
        before = len(filtered)
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
        print(f"[Itineraries MS] HTTP API listening on :{gv.ITINERARIES_PORT}")
        print(f"[Itineraries MS] cruises.json path: {os.path.abspath('../databank/cruises.json')}")
        threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.1),
                         daemon=True, name="HTTP_itineraries").start(),

    def run(self):
        def on_created_reserve(ch, method, properties, body):
            print("\n[Itineraries MS] Mensagem recebida em CREATED_RESERVE_Q_NAME!")
            print(f"→ Body recebido: {body}")
            try:
                msg = json.loads(body.decode('utf-8'))
                print(f"[Itineraries MS] Decodificado: {msg}")
                reservation = ReservationRequest(**msg)

                # Atualiza o usuário correto
                users_path = os.path.abspath('../databank/users.json')
                with open(users_path, 'r') as file:
                    users_data = json.load(file)

                users = users_data.get("users", [])
                found_user = False
                for user in users:
                    if user.get("id") == reservation.user_id:
                        user.setdefault("reservations", [])
                        new_entry = {
                            "cruise_id":       reservation.id,
                            "passenger_count": reservation.passenger_count,
                            "cabins":          reservation.cabins
                        }
                        user["reservations"].append(new_entry)
                        found_user = True
                        print(f"[Itineraries MS] Usuário {reservation.user_id} atualizado com reserva {reservation.id}")
                        break
                if not found_user:
                    print(f"[Itineraries MS][WARN] Usuário {reservation.user_id} não encontrado para atualizar reserva.")

                with open(users_path, 'w', encoding='utf-8') as f:
                    json.dump(users_data, f, indent=2, ensure_ascii=False)
                    print(f"[Itineraries MS] users.json salvo: {users_path}")

                cruises_path = os.path.abspath('../databank/cruises.json')
                with open(cruises_path, 'r') as file:
                    data = json.load(file)

                found_itin = False
                for itin in data.get('itineraries', []):
                    if itin.get('id') == reservation.id:
                        old_cabins = itin['available_cabins']
                        old_passengers = itin.get('passenger_count', 0)
                        # Corrige para não ficar negativo!
                        itin['available_cabins'] = max(old_cabins - reservation.cabins, 0)
                        itin['passenger_count'] = max(old_passengers - reservation.passenger_count, 0)
                        print(f"[Itineraries MS] Cruise {reservation.id} atualizado:")
                        print(f"    Cabines: {old_cabins} → {itin['available_cabins']}")
                        print(f"    Passageiros: {old_passengers} → {itin['passenger_count']}")
                        found_itin = True
                        break
                if not found_itin:
                    print(f"[Itineraries MS][WARN] Cruise id {reservation.id} não encontrado.")

                with open(cruises_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"[Itineraries MS] cruises.json salvo: {cruises_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"[Itineraries MS][ERROR] Falha ao processar reserva: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        def on_cancelled_reserve(ch, method, properties, body):
            print("\n[Itineraries MS] Mensagem recebida em CANCELLED_RESERVE_Q_NAME!")
            print(f"→ Body recebido: {body}")
            try:
                msg = json.loads(body.decode('utf-8'))
                cruise_id = msg.get('cruise_id', msg.get('id'))
                user_id = msg.get('user_id', None)

                users_path = os.path.abspath('../databank/users.json')
                with open(users_path, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)

                found_user = False
                for user in users_data.get("users", []):
                    if user.get("id") == user_id:
                        existing = user.get("reservations", [])
                        reservation_to_remove = next((r for r in existing if r.get("cruise_id") == cruise_id), None)
                        user["reservations"] = [
                            r for r in existing
                            if r.get("cruise_id") != cruise_id
                        ]
                        found_user = True
                        print(f"[Itineraries MS] Reserva do usuário {user_id} para o cruzeiro {cruise_id} removida.")
                        break
                if not found_user:
                    print(f"[Itineraries MS][WARN] Usuário {user_id} não encontrado para cancelamento.")

                with open(users_path, 'w', encoding='utf-8') as f:
                    json.dump(users_data, f, ensure_ascii=False, indent=2)
                    print(f"[Itineraries MS] users.json salvo após cancelamento: {users_path}")

                cruises_path = os.path.abspath('../databank/cruises.json')
                with open(cruises_path, 'r') as file:
                    data = json.load(file)

                found_itin = False
                for itin in data.get('itineraries', []):
                    if itin.get('id') == cruise_id:
                        old_cabins = itin['available_cabins']
                        old_passengers = itin.get('passenger_count', 0)
                        if reservation_to_remove:
                            itin['available_cabins'] = old_cabins + reservation_to_remove['cabins']
                            itin['passenger_count'] = old_passengers + reservation_to_remove['passenger_count']
                            print(f"[Itineraries MS] Cancelamento cruise {cruise_id}:")
                            print(f"    Cabines: {old_cabins} → {itin['available_cabins']}")
                            print(f"    Passageiros: {old_passengers} → {itin['passenger_count']}")
                        else:
                            print(f"[Itineraries MS][WARN] Nenhuma reserva encontrada para remover do cruzeiro {cruise_id}.")
                        found_itin = True
                        break
                if not found_itin:
                    print(f"[Itineraries MS][WARN] Cruise id {cruise_id} não encontrado para cancelamento.")

                with open(cruises_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"[Itineraries MS] cruises.json salvo após cancelamento: {cruises_path}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"[Itineraries MS][ERROR] Falha ao processar cancelamento: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        self.channel.basic_consume(queue=gv.CREATED_RESERVE_Q_NAME, on_message_callback=on_created_reserve, auto_ack=False)
        self.channel.basic_consume(queue=gv.CANCELLED_RESERVE_Q_NAME, on_message_callback=on_cancelled_reserve, auto_ack=False)
        
        try:
            print("[Itineraries MS] Escutando todas as filas RabbitMQ.")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionClosed:
            print("[Itineraries MS] Conexão com RabbitMQ foi fechada.")
        except pika.exceptions.ConnectionWrongStateError:
            print("[Itineraries MS] RabbitMQ em estado errado para consumir.")
        finally:
            self.channel.close()
            self.connection.close()
            print("[Itineraries MS] Conexão encerrada.")

    def stop(self):
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)
