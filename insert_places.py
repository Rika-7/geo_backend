import requests
import json

# Backend URL - replace with your actual backend URL
BASE_URL = "https://tech0-gen-7-step4-student-finalproject-4-exeabgd9eyekb7c2.canadacentral-01.azurewebsites.net"

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

def insert_places():
    headers = {
        "Content-Type": "application/json"
    }
    
    for place in places_data:
        try:
            response = requests.post(
                f"{BASE_URL}/places",
                headers=headers,
                data=json.dumps(place)
            )
            
            if response.status_code == 200:
                print(f"Successfully inserted: {place['placename']}")
            else:
                print(f"Failed to insert {place['placename']}: {response.text}")
                
        except Exception as e:
            print(f"Error inserting {place['placename']}: {str(e)}")

if __name__ == "__main__":
    insert_places()