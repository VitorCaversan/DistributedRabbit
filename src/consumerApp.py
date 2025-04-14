from consumer import Consumer

if __name__ == "__main__":
    consumer = Consumer('localhost')
    
    while True:
        choice = input("\n\nPlease select one of the following options:\n"
                       "1. Get from created reserve queue once\n"
                       "2. Consume from created reserve queue once and remove from queue\n"
                       "3. Call it a day\n")
        
        if choice == "1":
            consumer.get_once_created_reserve(consumer.std_callback_without_ack)
        elif choice == "2":
            consumer.get_once_created_reserve(consumer.std_callback_with_ack)
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")