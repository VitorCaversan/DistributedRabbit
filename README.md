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

1. Start the RabbitMQ broker.
2. Run each microservice independently (ensure they are connected to RabbitMQ).
3. Use the UI to interact with the services.
4. Monitor logs for event flow and signature verification.

## License

This project is developed as part of the Distributed Systems course at UTFPR and is intended for academic use only.

---

