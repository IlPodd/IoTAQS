from mongoengine import connect, EmbeddedDocument, DynamicDocument
from parameters.Database_parameters import db_host, db_name, db_port
from pymongo.errors import ConnectionFailure
connect(db_name, host=db_host, port=db_port)
class DatabaseManager():
    def __init__(self, db_name=db_name, host='localhost', port=27017):
        self.db_name = db_name
        self.host = host
        self.port = port
        self.client = None  # MongoClient instance
        self.db = None  # MongoDB database instance
        self.collection = None  # MongoDB collection instance
    def connect(self):
        try:
            # Attempt to connect to the database
            conn = connect(db=self.db_name, host=self.host, port=self.port)

            # Perform a dummy operation to force a connection and check its success
            conn.server_info()  # This will raise an exception if the connection failed

            print("Successfully connected to MongoDB.")
        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")


    def fetch_barriers(self):
        try:
            # Fetch barriers from MongoDB collection
            barriers = list(self.collection.find())
            return barriers
        except Exception as e:
            print(f"Error fetching barriers: {e}")
            return []

    def close_connection(self):
        try:
            if self.client:
                self.client.close()
                print("MongoDB connection closed.")
        except Exception as e:
            print(f"Error closing MongoDB connection: {e}")



if __name__ == "__main__":

    db_manager = DatabaseManager(db_name, host=db_host, port=db_port)
    db_manager.connect()



