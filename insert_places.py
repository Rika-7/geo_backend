import requests
import json
import logging

# Enable logging to see more details
logging.basicConfig(level=logging.INFO)

# # For local development, use localhost
# BASE_URL = "http://localhost:8000"  # FastAPI runs on port 8000 by default

# For Azure deployment, use the deployed URL
BASE_URL = "tech0-db-step4-studentrdb-4.mysql.database.azure.com"

def test_connection():
    """Test the basic connection to the backend"""
    try:
        response = requests.get(f"{BASE_URL}/")
        logging.info(f"Connection test response: {response.status_code}")
        logging.info(f"Response content: {response.text}")
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    if test_connection():
        print("Connection successful!")
    else:
        print("Connection failed. Please check your configuration.")