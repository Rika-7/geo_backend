import requests
import json
import logging

# Enable logging to see more details
logging.basicConfig(level=logging.INFO)

# # For local development, use localhost
# BASE_URL = "http://localhost:8000"  # FastAPI runs on port 8000 by default

# For Azure deployment, use the deployed URL
BASE_URL = "tech0-db-step4-studentrdb-4.mysql.database.azure.com"

# Example data
places_data = [
    {
        "placename": "町田GIONスタジアム",
        "description": "FC町田ゼルビアのホームスタジアム",
        "latitude": 35.592735510792195,
        "longitude": 139.43884126045768,
        "category": "stadium",
        "url": "https://www.zelvia.co.jp/stadium/access/"
    },
    {
        "placename": "町田薬師池公園",
        "description": "四季彩の杜",
        "latitude": 35.578879824273436,
        "longitude": 139.4481512601811,
        "category": "park",
        "url": "https://machida-shikisainomori.com"
    },
    {
        "placename": "小野路宿里山交流館",
        "description": "江戸時代、小野路宿にあった旅籠はたご・旧「角屋かどや」を改修した施設",
        "latitude": 35.60129950268735,
        "longitude": 139.43801152786767,
        "category": "sightseeing",
        "url": "https://www.city.machida.tokyo.jp/kanko/miru_aso/satoyamakoryukan/kouryukan_gaiyou_kinou.html"
    }
]

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

def insert_places():
    if not test_connection():
        logging.error("Failed to connect to the backend. Please check if the FastAPI server is running on localhost:8000")
        return

    headers = {
        "Content-Type": "application/json"
    }
    
    for place in places_data:
        try:
            logging.info(f"Attempting to insert: {place['placename']}")
            response = requests.post(
                f"{BASE_URL}/places",
                headers=headers,
                data=json.dumps(place)
            )
            
            logging.info(f"Response status code: {response.status_code}")
            logging.info(f"Response content: {response.text}")
            
            if response.status_code == 200:
                print(f"Successfully inserted: {place['placename']}")
            else:
                print(f"Failed to insert {place['placename']}: {response.text}")
                
        except Exception as e:
            print(f"Error inserting {place['placename']}: {str(e)}")
            logging.error(f"Detailed error: {str(e)}")

if __name__ == "__main__":
    insert_places()