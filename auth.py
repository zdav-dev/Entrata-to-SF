import os
from simple_salesforce import Salesforce
from dotenv import load_dotenv

# Authenticate to Salesforce
def auth():
    # Authenticate with username, password, and security token
    load_dotenv()

    try:
        sf = Salesforce(
            username=os.getenv("SF_USERNAME"),
            password=os.getenv("SF_PASSWORD"),
            security_token=os.getenv("SF_SECURITY_TOKEN"),
            consumer_key=os.getenv("SF_CONSUMER_KEY"),
            consumer_secret=os.getenv("SF_SECRET")
        )

        return sf
    except Exception as e:
        print(f"Error connecting to Salesforce: {e}")

    return None


sf = auth()