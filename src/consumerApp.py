from consumer import Consumer

if __name__ == "__main__":
    consumer = Consumer('localhost')
    
    while True:
        choice = input("\n\nPlease select one of the following options:\n"
                       "1. Consume from created reserve queue\n"
                       "2. Call it a day\n")
        
        if choice == "1":
            consumer.consume_created_reserve(consumer.std_callback)
        elif choice == "2":
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")