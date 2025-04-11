from publisher import Publisher

if __name__ == "__main__":
    publisher = Publisher('localhost')
    
    while True:
        choice = input("\n\nPlease select one of the following options:\n"
                       "1. Publish to created reserve queue\n"
                       "2. Close all queues\n")
        
        if choice == '1':
            publisher.publish_created_reserve("New cruise for Angola!")
        elif choice == '2':
            publisher.close()
            print("All queues closed.")
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")