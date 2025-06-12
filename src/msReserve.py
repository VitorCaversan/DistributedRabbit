"""
Micro-serviço de Reserva  – thread-safe com add_callback_threadsafe
------------------------------------------------------------------
Usamos **1 conexão + 1 canal** que pertencem
exclusivamente à thread do `start_consuming()`.
O endpoint Flask apenas agenda a publicação
no loop I/O dessa thread usando `add_callback_threadsafe`.
"""

import json, logging

from flask import Flask, render_template, jsonify
from flask_sse import sse
from dataclasses import dataclass, asdict
from wsgiref.simple_server import make_server
from functools import partial
import threading
import pika
from pika.exceptions import (
    ConnectionClosed,
    StreamLostError,
    ChannelWrongStateError,
)
from verif_signature import verify_sig, InvalidSignature
from msPromotions import MSPromotions
import globalVars

app = Flask(__name__)
app.config["REDIS_URL"] = "redis://localhost"
app.register_blueprint(sse, url_prefix='/stream')

# --- logging -----------------------------------------------------------------
logging.basicConfig(level=logging.ERROR)
LOGGER = logging.getLogger(__name__)
# logging.disable(logging.CRITICAL)

# --- modelo de dados ---------------------------------------------------------
@dataclass
class ReservationRequest:
    id: int
    ship: str
    departure_date: str
    embark_port: str
    return_port: str
    visited_places: list
    nights: int
    price: float
    passenger_count: int = 1
    cabins: int = 1
    user_id: int = 0
    
class MSReserve:
    def __init__(self, host: str = "localhost"):
        self.host = host
        self._setup_connection()

        self._lock = threading.Lock()
        # {reserve_id: {"reserve": PENDING|APPROVED|FAILED,
        #               "payment": PENDING|APPROVED|DENIED,
        #               "ticket" : PENDING|GENERATED}}
        self._status = {}

    def reserve_cruise(self, reservation: ReservationRequest) -> str:
        LOGGER.debug("Scheduling publish for reservation id=%s", reservation.id)
        self.connection.add_callback_threadsafe(
            partial(self._publish_reservation, reservation)
        )
        return "Reservation scheduled to publish"

    def _publish_reservation(self, reservation: ReservationRequest) -> None:
        body = json.dumps(asdict(reservation)).encode()
        self.channel.basic_publish(
            exchange="",
            routing_key=globalVars.CREATED_RESERVE_Q_NAME,
            body=body,
            properties=pika.BasicProperties(content_type="application/json")
        )
        with self._lock:
            self._status[reservation.id] = {"reserve": "PENDING",
                                            "payment": "PENDING",
                                            "ticket" : "PENDING"}
        self._publish_status(reservation.id)
        LOGGER.info("Reserva publicada id=%s", reservation.id)

    def run(self):
        self._declare_topology()
        self.channel.basic_consume(
            queue=globalVars.APPROVED_PAYMENT_RESERVE_NAME,
            on_message_callback=self._on_approved_payment,
            auto_ack=False,
        )
        self.channel.basic_consume(
            queue=globalVars.DENIED_PAYMENT_NAME,
            on_message_callback=self._on_denied_payment,
        )
        self.channel.basic_consume(
            queue=globalVars.TICKET_GENERATED_NAME,
            on_message_callback=self._on_ticket_generated,
        )

        try:
            print("[Reserve MS] Listening on all queues.")
            self.channel.start_consuming()
        except (ConnectionClosed, StreamLostError):
            LOGGER.warning("Connection closed unexpectedly – leaving consume loop")
        finally:
            self._safe_close()

    def stop(self):
        self.connection.add_callback_threadsafe(self.channel.stop_consuming)

    def _publish_status(self, rid: int) -> None:
        with self._lock:
            payload = {"reserve_id": rid, **self._status[rid]}

        with app.app_context():
            sse.publish(
                payload,
                type="status",
                channel=f"reserve-{rid}" 
            )

    def _setup_connection(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(self.host)
        )
        self.channel = self.connection.channel()

        httpd = make_server("localhost", globalVars.RESERVER_PORT, app)
        print(f"[Reserve MS] HTTP API listening on :{globalVars.RESERVER_PORT}")
        threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.1),
                         daemon=True, name="HTTP_itineraries").start()

    def _declare_topology(self):
        for q in (
            globalVars.DENIED_PAYMENT_NAME,
            globalVars.TICKET_GENERATED_NAME,
            globalVars.CREATED_RESERVE_Q_NAME,
            globalVars.CANCELLED_RESERVE_Q_NAME,
        ):
            self.channel.queue_declare(queue=q)

        self.channel.exchange_declare(
            exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
            exchange_type="direct",
            durable=True,
        )
        self.channel.queue_declare(
            queue=globalVars.APPROVED_PAYMENT_RESERVE_NAME, durable=True
        )
        self.channel.queue_bind(
            exchange=globalVars.APPROVED_PAYMENT_EXCHANGE,
            queue=globalVars.APPROVED_PAYMENT_RESERVE_NAME,
            routing_key=globalVars.APPROVED_PAYMENT_ROUTING_KEY,
        )

    def publish_created_reserve(self, cruise_id):
        payload = {"cruise_id": cruise_id}
        out_body = json.dumps(payload).encode('utf-8')
        LOGGER.debug("Publishing reservation id=%s", cruise_id)
        self.channel.basic_publish(
            exchange="",
            routing_key=globalVars.CREATED_RESERVE_Q_NAME,
            body=out_body,
        )

    def publish_cancelled_reserve(self, cruise_id, user_id):
        payload = {"cruise_id": cruise_id, "user_id": user_id}
        out_body = json.dumps(payload).encode('utf-8')
        LOGGER.debug("Publishing cancelled reservation id=%s", cruise_id)
        self.connection.add_callback_threadsafe(
            partial(self._publish_cancelled_reserve, out_body)
        )

    def _publish_cancelled_reserve(self, out_body):
        self.channel.basic_publish(
            exchange="",
            routing_key=globalVars.CANCELLED_RESERVE_Q_NAME,
            body=out_body,
        )

    def _on_approved_payment(self, ch, method, props, body):
        try:
            evt = verify_sig(body, props.headers or {})
            rid  = evt["reserve_id"]

            with self._lock:
                st = self._status.setdefault(rid, {})
                st["reserve"] = "APPROVED"
                st["payment"] = "APPROVED"

            self._publish_status(rid)
            LOGGER.info("[Reserve MS] payment OK %s", evt)
            ch.basic_ack(method.delivery_tag)
        except InvalidSignature:
            LOGGER.error("[Reserve MS] bad signature")
            ch.basic_nack(method.delivery_tag, requeue=False)


    def _on_denied_payment(self, ch, method, props, body):
        try:
            evt = verify_sig(body, props.headers or {})
            rid = evt["reserve_id"]

            self.publish_cancelled_reserve(cruise_id=rid, user_id=evt["user_id"])

            with self._lock:
                st = self._status.setdefault(rid, {})
                st["reserve"] = "FAILED"
                st["payment"] = "DENIED"

            self._publish_status(rid)
            LOGGER.info("[Reserve MS] payment DENIED %s", evt)
            ch.basic_ack(method.delivery_tag)
        except InvalidSignature:
            LOGGER.error("[Reserve MS] bad signature")
            ch.basic_nack(method.delivery_tag, requeue=False)


    def _on_ticket_generated(self, ch, method, _props, body):
        try:
            rid = json.loads(body.decode())["reserve_id"]
        except Exception:
            rid = None

        if rid is not None:
            with self._lock:
                self._status.setdefault(rid, {})["ticket"] = "GENERATED"
            self._publish_status(rid)

        LOGGER.info("[Reserve MS] ticket gerado %s", body.decode())
        ch.basic_ack(method.delivery_tag)

    def get_status(self, rid: int) -> dict | None:
        with self._lock:
            return self._status.get(rid)

    def _safe_close(self):
        if self.channel.is_open:
            self.channel.close()
        if self.connection.is_open:
            self.connection.close()
        LOGGER.info("[Reserve MS] Connection closed.")
        print("[Reserve MS] Connection closed.")
