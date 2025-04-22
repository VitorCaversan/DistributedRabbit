# CruiseSync - Distributed Cruise Booking System

**Authors:**  
Alfons Andrade  
João Vitor Caversan dos Passos  

**Course:** Distributed Systems  
**Instructor:** Prof. Ana Cristina Barreiras Kochem Vendramin  
**University:** UTFPR - DAINF  

## Overview

CruiseSync is a distributed system built with a microservices architecture to manage cruise reservations. It leverages asynchronous communication through RabbitMQ and the AMQP protocol to ensure high scalability, flexibility, and decoupling between components.

The system is composed of four main microservices and a messaging infrastructure that coordinates the reservation flow from search to ticket issuance. It also includes cryptographic validation using asymmetric keys for secure message signing and verification.

## Technologies Used

- RabbitMQ (Message Broker using AMQP)
- Microservices (Publisher/Subscriber model)
- Asymmetric Cryptography (Digital Signature)
- Custom UI Interface (for user interaction)

## Microservices Architecture

### 1. **Reservation Service (Publisher/Subscriber)**

- Allows clients to **search for available cruise itineraries** based on destination, departure port, and dates.
- Handles **reservation requests** including number of passengers and cabins.
- **Publishes** new reservation events to the `reserva-criada` queue.
- **Subscribes** to `pagamento-aprovado`, `pagamento-recusado`, and `bilhete-gerado` queues to track the reservation status.
- **Verifies digital signatures** from the Payment Service using its public key.

### 2. **Payment Service (Publisher/Subscriber)**

- **Subscribes** to the `reserva-criada` queue.
- Validates the payment request and responds by:
  - Publishing a signed message to `pagamento-aprovado` queue (if approved).
  - Publishing a signed message to `pagamento-recusado` queue (if declined).
- **Signs all payment messages** with its private key.

### 3. **Ticketing Service (Publisher/Subscriber)**

- **Subscribes** to the `pagamento-aprovado` queue.
- Validates the digital signature from the Payment Service using its public key.
- Generates the cruise ticket and publishes it to the `bilhete-gerado` queue.

### 4. **Marketing Service (Publisher)**

- Publishes promotional messages to destination-specific queues such as:
  - `promocoes-destino_x`, `promocoes-destino_y`, etc.
- Promotions are only received by clients **subscribed to the relevant destination queues**.

### 5. **Subscriber (Client Notification Service)**

- **Subscribes** to promotional queues and receives notifications for selected destinations.

## Key Features

- ✅ **Asynchronous messaging** via RabbitMQ (event-driven architecture)
- ✅ **Loose coupling** between microservices
- ✅ **Scalability** through independent service deployment
- ✅ **Digital signature** for message authentication
- ✅ **Real-time status updates** for bookings and payments

## Usage

The user interface allows:

- Searching for cruise itineraries  
- Making reservations  
- Receiving real-time updates on reservation status  
- Viewing promotional offers by destination  

## Running the System
### Dependencies
**Technologies:**
 - Python 3.7+
 - RabbitMQ (via Docker or local install)
 - Docker & Docker Compose (optional for container-based deployment)

**Required Python packages:**
```bash
pip install pika flask flask_cors cryptography
```

### Running project locally
1. Ensure RabbitMQ is running locally or via Docker.
2. Clone the repository:
   ```bash
   git clone
   ```
3. Run **ONLY ONCE** the following script to create the asymmetric keys:
   ```bash
   python keygen_ed25519.py
   ```
4. Navigate to the project src directory:
   ```bash
   cd src
   ```
5. Run main.py to start the microservices:
   ```bash
   python main.py
   ```
6. Access the UI at `http://localhost:5000` or by running live server on VSCode.
7. Use the UI to interact with the system, search for cruises, make reservations, and view promotions.
8. Monitor RabbitMQ management interface at `http://localhost:15672` (default credentials: guest/guest).
9. Use the management interface to view queues, messages, and service interactions.
10. To stop the services, terminate the Python processes or use `Ctrl+C` in the terminal.
11. If needed to send promotional messages, run the `msPromotions.py` script in a separate terminal:
    ```bash
    python msPromotions.py
    ```

## License

This project is developed as part of the Distributed Systems course at UTFPR and is intended for academic use only.

---

