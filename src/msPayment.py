import os
import json
import base64
import threading
import pika
from flask import Flask, request, jsonify
from msReserve import ReservationRequest
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import globalVars as gv
import requests

class MSPayment:
    def __init__(self, host='localhost'):
        self.host = host
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=gv.APPROVED_PAYMENT_EXCHANGE,
                                      exchange_type='direct',
                                      durable=True)
        self.channel.queue_declare(queue=gv.DENIED_PAYMENT_NAME)

        # Carregar chave privada
        _PRIV_PATH = os.getenv("MSPAYMENT_PRIV_KEY")
        with open(_PRIV_PATH, "rb") as f:
            self._private_key = load_pem_private_key(f.read(), password=None)

        # Inicia Flask na thread
        self.app = Flask("payment_ms_webhook")
        self._setup_routes()
        self._flask_thread = threading.Thread(target=self._run_flask, daemon=True)

    def _setup_routes(self):
        @self.app.route("/payment_webhook", methods=["POST"])
        def payment_webhook():
            data = request.get_json()
            reserve_id = data.get("reserve_id")
            user_id = data.get("user_id")
            status = data.get("status", "APPROVED")
            print(f"[Payment MS] Webhook recebido: {data}")

            payload = {"reserve_id": reserve_id, "user_id": user_id, "status": status}
            out_body = json.dumps(payload).encode('utf-8')
            sig = base64.b64encode(self._private_key.sign(out_body)).decode('utf-8')

            def _publish():
                if status == "APPROVED":
                    self.channel.basic_publish(
                        exchange=gv.APPROVED_PAYMENT_EXCHANGE,
                        routing_key=gv.APPROVED_PAYMENT_ROUTING_KEY,
                        body=out_body,
                        properties=pika.BasicProperties(
                            content_type="application/json",
                            headers={"sig_alg": "ed25519", "sig": sig},
                            delivery_mode=2
                        )
                    )
                else:
                    self.channel.basic_publish(
                        exchange='',
                        routing_key=gv.DENIED_PAYMENT_NAME,
                        body=out_body,
                        properties=pika.BasicProperties(
                            content_type="application/json",
                            headers={"sig_alg": "ed25519", "sig": sig},
                            delivery_mode=2
                        )
                    )

            self.connection.add_callback_threadsafe(_publish)
            return jsonify({"status": "ok"})

        # NOVAS ROTAS PARA INTERFACE EXTERNA DE PAGAMENTO
        @self.app.route("/pay/<int:rid>/<int:user_id>/confirm", methods=["POST"])
        def pay_confirm(rid, user_id):
            # Simula confirmação, chama o próprio webhook interno
            url = f"http://localhost:{gv.PAYMENT_INTERNAL_PORT}/payment_webhook"
            data = {"reserve_id": rid, "user_id": user_id, "status": "APPROVED"}
            try:
                requests.post(url, json=data)
            except Exception as e:
                print(f"[Payment MS] Erro ao chamar webhook: {e}")
            return '', 204

        @self.app.route("/pay/<int:rid>/<int:user_id>/deny", methods=["POST"])
        def pay_deny(rid, user_id):
            # Simula recusa, chama o próprio webhook interno
            url = f"http://localhost:{gv.PAYMENT_INTERNAL_PORT}/payment_webhook"
            data = {"reserve_id": rid, "user_id": user_id, "status": "DENIED"}
            try:
                requests.post(url, json=data)
            except Exception as e:
                print(f"[Payment MS] Erro ao chamar webhook: {e}")
            return '', 204

    def _run_flask(self):
        self.app.run(host="0.0.0.0", port=gv.PAYMENT_INTERNAL_PORT, debug=False, use_reloader=False)

    def run(self):
        # Iniciar o webhook REST na thread
        self._flask_thread.start()

        def on_created_reserve(ch, method, properties, body):
            reservation = ReservationRequest(**json.loads(body.decode('utf-8')))
            print(f"[Payment MS] Received: {body.decode('utf-8')}")
            # NADA acontece aqui, só aguarda o webhook do serviço externo!
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(
            queue=gv.CREATED_RESERVE_Q_NAME,
            on_message_callback=on_created_reserve,
            auto_ack=False
        )

        try:
            print("[Payment MS] Listening on all queues + webhook REST")
            self.channel.start_consuming()
        except pika.exceptions.ConnectionClosed:
            pass
        except pika.exceptions.ConnectionWrongStateError:
            pass
        finally:
            self.channel.close()
            self.connection.close()
            print("[Payment MS] Connection closed.")

    def stop(self):
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)
