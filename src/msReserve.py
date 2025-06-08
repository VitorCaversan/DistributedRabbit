"""
Micro-serviço de Reserva  – thread-safe com add_callback_threadsafe
------------------------------------------------------------------
Usamos **1 conexão + 1 canal** que pertencem
exclusivamente à thread do `start_consuming()`.
O endpoint Flask apenas agenda a publicação
no loop I/O dessa thread usando `add_callback_threadsafe`.
"""

import json, logging

from dataclasses import dataclass, asdict
from functools import partial
import threading

import pika
from pika.exceptions import (
    ConnectionClosed,
    StreamLostError,
    ChannelWrongStateError,
)

from verif_signature import verify_sig, InvalidSignature
import globalVars

# --- logging -----------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
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

    def _setup_connection(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(self.host)
        )
        self.channel = self.connection.channel()

    def _declare_topology(self):
        for q in (
            globalVars.DENIED_PAYMENT_NAME,
            globalVars.TICKET_GENERATED_NAME,
            globalVars.CREATED_RESERVE_Q_NAME,
            globalVars.CANCELLED_RESERVE_Q_NAME,
        ):
            self.channel.queue_declare(queue=q)

        # exchange + filas para pagamentos aprovados
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

    def publish_cancelled_reserve(self, cruise_id):
        payload = {"cruise_id": cruise_id}
        out_body = json.dumps(payload).encode('utf-8')
        LOGGER.debug("Publishing reservation id=%s", cruise_id)
        self.channel.basic_publish(
            exchange="",
            routing_key=globalVars.CANCELLED_RESERVE_Q_NAME,
            body=out_body,
        )

    def _on_approved_payment(self, ch, method, properties, body):
        try:
            event = verify_sig(body, properties.headers or {})
            with self._lock:
                st = self._status.setdefault(event["reserve_id"], {})
                st["reserve"] = "APPROVED"
                st["payment"] = "APPROVED"
            LOGGER.info("[Reserve MS] verified: %s", event)
            ch.basic_ack(method.delivery_tag)
        except InvalidSignature:
            LOGGER.error("[Reserve MS] Signature check failed")
            ch.basic_nack(method.delivery_tag, requeue=False)

    def _on_denied_payment(self, ch, method, properties, body):
        try:
            data = verify_sig(body, properties.headers or {})
            with self._lock:
                st = self._status.setdefault(data["reserve_id"], {})
                st["reserve"]  = "FAILED"
                st["payment"]  = "DENIED"
            LOGGER.info("[Reserve MS] Received denial: %s", body.decode())
            ch.basic_ack(method.delivery_tag)
        except InvalidSignature:
            LOGGER.error("[Reserve MS] Signature check failed")
            ch.basic_nack(method.delivery_tag, requeue=False)

    def _on_ticket_generated(self, ch, method, _props, body):
        try:
            data = json.loads(body.decode())
            reserve_id = data.get("reserve_id")
        except json.JSONDecodeError:
            reserve_id = None

        if reserve_id is not None:
            with self._lock:
                st = self._status.setdefault(reserve_id, {})
                st["ticket"] = "GENERATED"

        LOGGER.info("[Reserve MS] Ticket generated msg: %s", body.decode())
        ch.basic_ack(method.delivery_tag)

    def _safe_close(self):
        if self.channel.is_open:
            self.channel.close()
        if self.connection.is_open:
            self.connection.close()
        LOGGER.info("[Reserve MS] Connection closed.")
        print("[Reserve MS] Connection closed.")

    def get_status(self, rid: int) -> dict | None:
        with self._lock:
            return self._status.get(rid)
