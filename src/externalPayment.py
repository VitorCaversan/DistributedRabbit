import os
from flask import Flask, request, jsonify, send_from_directory
import globalVars as gv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend"))

app = Flask(__name__)

@app.route("/pay.css")
def pay_css():
    return send_from_directory(FRONT_DIR, "pay.css")

@app.route("/pay.js")
def pay_js():
    return send_from_directory(FRONT_DIR, "pay.js")

@app.route("/generate_payment", methods=["POST"])
def generate_payment():
    data = request.get_json()
    reserve_id = data.get("id")
    user_id = data.get("user_id")
    payment_url = f"http://localhost:{gv.PAYMENT_PORT}/pay/{reserve_id}/{user_id}"
    return jsonify({"payment_url": payment_url})

@app.route("/pay/<int:reserve_id>/<int:user_id>", methods=["GET"])
def pay_page(reserve_id, user_id):
    # Servir pay.html direto do disco
    return send_from_directory(FRONT_DIR, "pay.html")

@app.route("/pay/<int:reserve_id>/<int:user_id>/confirm", methods=["POST"])
def confirm_payment(reserve_id, user_id):
    import requests
    payload = {"reserve_id": reserve_id, "user_id": user_id, "status": "APPROVED"}
    resp = requests.post(f"http://localhost:{gv.PAYMENT_INTERNAL_PORT}/payment_webhook", json=payload, timeout=3)
    return '', 204

@app.route("/pay/<int:reserve_id>/<int:user_id>/deny", methods=["POST"])
def deny_payment(reserve_id, user_id):
    import requests
    payload = {"reserve_id": reserve_id, "user_id": user_id, "status": "DENIED"}
    resp = requests.post(f"http://localhost:{gv.PAYMENT_INTERNAL_PORT}/payment_webhook", json=payload, timeout=3)
    return '', 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=gv.PAYMENT_PORT)
    print(f"Payment service running on port {gv.PAYMENT_PORT}")
