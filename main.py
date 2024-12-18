from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import mysql.connector
from mysql.connector import errorcode
import os
from dotenv import load_dotenv
from datetime import datetime
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import gc
from contextlib import contextmanager

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tech0-gen-7-step4-student-finalproject-3-g6fnhbbhhegnccc0.canadacentral-01.azurewebsites.net",  # Production
        "http://localhost:3000",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#データベース接続情報の設定
config = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME"),
    'charset': 'utf8mb4', # 日本語を扱うための設定
}

# If running on Azure, add SSL configuration
if os.getenv("AZURE_DEPLOYMENT", "false").lower() == "true":
    config.update({
        'client_flags': [mysql.connector.ClientFlag.SSL],
        'ssl_ca': '/home/site/certificates/DigiCertGlobalRootG2.crt.pem'
    })

# Pydantic Models
class Place(BaseModel):
    place_id: Optional[int] = None  
    placename: str
    description: str
    category: str
    latitude: float
    longitude: float
    url: str
    has_coupon: Optional[bool] = False
    image_url: Optional[str] = None
    coupon_url: Optional[str] = None
    cover_image_url: Optional[str] = None

class LocationData(BaseModel):
    J_league_id: str
    latitude: float
    longitude: float
    accuracy: float
    timestamp: str
    favorite_club: str

class TrafficRequest(BaseModel):
    current_latitude: float
    current_longitude: float
    destination_latitude: float
    destination_longitude: float
    game_time: str
    favorite_club: str

class TrafficResponse(BaseModel):
    route_suggestion: str
    estimated_time: str
    crowd_level: str
    additional_tips: str

# Database connection context manager
class DatabaseConnection:
    def __init__(self):
        self.config = config
    
    def __enter__(self):
        try:
            self.conn = mysql.connector.connect(**self.config)
            return self.conn
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                raise HTTPException(status_code=500, detail="Database access denied")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                raise HTTPException(status_code=500, detail="Database does not exist")
            else:
                raise HTTPException(status_code=500, detail=str(err))
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, 'conn'):
            self.conn.close()

# AI Traffic Assistant Implementation
class TrafficAssistant:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.model_name = "cyberagent/calm2-7b-chat"  # Using smaller 7B model
        self.max_memory = {"cpu": "4GB"}  # Memory management
    
    @contextmanager
    def model_context(self):
        """Context manager for handling model loading and cleanup"""
        try:
            self.ensure_initialized()
            yield
        finally:
            # Clear CUDA cache if using GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
    
    def ensure_initialized(self):
        if self.tokenizer is None or self.model is None:
            try:
                print("Initializing model...")
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    use_fast=True
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    torch_dtype=torch.float16,
                    max_memory=self.max_memory,
                    low_cpu_mem_usage=True
                )
                print("Model initialized successfully")
            except Exception as e:
                print(f"Error initializing model: {str(e)}")
                raise

    def analyze_traffic(self, request: TrafficRequest, historical_data: List[Dict]) -> str:
        with self.model_context():
            try:
                prompt = f"""
現在地({request.current_latitude}, {request.current_longitude})から
目的地({request.destination_latitude}, {request.destination_longitude})まで、
{request.game_time}開催の{request.favorite_club}の試合に向かうための最適な経路を提案してください。

以下の要素を考慮してアドバイスをお願いします：
1. 試合開始時間に合わせた出発時間
2. 公共交通機関と徒歩経路の場合のアドバイス
3. 当日の天候による影響と対策

なお、過去の同様の試合では以下のような人出がありました：
"""
                for data in historical_data[:3]:
                    prompt += f"- {data['timestamp']}: {data['accuracy']}の精度で{data['favorite_club']}戦の観客データあり\n"

                messages = [
                    {"role": "system", "content": "あなたは交通案内の専門家です。目的地への最適な経路を提案します。"},
                    {"role": "user", "content": prompt}
                ]

                input_ids = self.tokenizer.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    return_tensors="pt"
                ).to(self.model.device)
                
                output_ids = self.model.generate(
                    input_ids,
                    max_new_tokens=512,  # Reduced from 1024
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    top_p=0.9,
                    repetition_penalty=1.1
                )
                
                response = self.tokenizer.decode(
                    output_ids[0][len(input_ids[0]):],
                    skip_special_tokens=True
                )
                return response.strip()
            
            except Exception as e:
                print(f"Error in analyze_traffic: {str(e)}")
                # Fallback response in case of model error
                return """
申し訳ありません。現在システムが混み合っております。
以下の一般的なアドバイスをご参考ください：
1. 試合開始の2時間前には会場到着を目指してください。
2. 公共交通機関をご利用の場合、余裕を持ってお出かけください。
3. 天候の確認を忘れずに行ってください。
"""

# API Routes
@app.get('/favicon.ico', include_in_schema=False)
@app.get('/apple-touch-icon.png', include_in_schema=False)
@app.get('/apple-touch-icon-precomposed.png', include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/")
def read_root():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/places", response_model=List[Place])
async def get_places():
    with DatabaseConnection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM places")
        places = cursor.fetchall()
        cursor.close()
        return places

@app.post("/places", response_model=Place)
async def create_place(place: Place):
    with DatabaseConnection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            INSERT INTO places (placename, description, latitude, longitude, category, url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (place.placename, place.description, place.latitude, place.longitude, place.category, place.url))
        conn.commit()
        place_id = cursor.lastrowid
        cursor.execute("SELECT * FROM places WHERE id = %s", (place_id,))
        result = cursor.fetchone()
        cursor.close()
        return result

@app.get("/places/category/{category}", response_model=List[Place])
async def get_places_by_category(category: str):
    with DatabaseConnection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM places WHERE category = %s", (category,))
        places = cursor.fetchall()
        cursor.close()
        return places

@app.put("/places/{place_id}", response_model=Place)
async def update_place(place_id: int, place: Place):
    with DatabaseConnection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            UPDATE places 
            SET placename = %s, description = %s, latitude = %s, 
                longitude = %s, category = %s, url = %s,
                has_coupon = %s, image_url = %s, coupon_url = %s,
                cover_image_url = %s
            WHERE place_id = %s
        """, (
            place.placename, place.description, place.latitude,
            place.longitude, place.category, place.url,
            place.has_coupon, place.image_url, place.coupon_url,
            place.cover_image_url, place_id
        ))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Place not found")
            
        cursor.execute("SELECT * FROM places WHERE place_id = %s", (place_id,))
        result = cursor.fetchone()
        cursor.close()
        return result

@app.delete("/places/{place_id}")
async def delete_place(place_id: int):
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM places WHERE id = %s", (place_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Place not found")
        cursor.close()
        return {"message": "Place deleted successfully"}

@app.get("/locations", response_model=List[LocationData])
async def get_locations():
    with DatabaseConnection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT J_league_id, latitude, longitude, accuracy, 
                   timestamp, favorite_club 
            FROM d_location_data
        """)
        locations = cursor.fetchall()
        
        for location in locations:
            if isinstance(location['timestamp'], datetime):
                location['timestamp'] = location['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        return locations

@app.post("/traffic_advice", response_model=TrafficResponse)
async def get_traffic_advice(request: TrafficRequest):
    try:
        # Hardcoded stadium coordinates for 町田GION stadium
        GION_STADIUM = {
            "latitude": 35.5466,
            "longitude": 139.4769
        }
        
        # Game details
        GAME_INFO = {
            "home": "町田ゼルビア",
            "away": "浦和レッズ",
            "stadium": "町田GIONスタジアム",
            "datetime": "2024-12-19 14:00"
        }

        # Modify request to always use GION stadium as destination
        request.destination_latitude = GION_STADIUM["latitude"]
        request.destination_longitude = GION_STADIUM["longitude"]
        request.game_time = GAME_INFO["datetime"]
        request.favorite_club = f"{GAME_INFO['home']} vs {GAME_INFO['away']}"
        
        traffic_assistant = TrafficAssistant.get_instance()
        
        # Get historical data for both teams
        with DatabaseConnection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT J_league_id, latitude, longitude, accuracy, 
                       timestamp, favorite_club 
                FROM d_location_data
                WHERE favorite_club IN (%s, %s)
                ORDER BY timestamp DESC
                LIMIT 3
            """, (GAME_INFO["home"], GAME_INFO["away"]))
            historical_data = cursor.fetchall()
            cursor.close()
        
        if isinstance(historical_data, list):
            for data in historical_data:
                if isinstance(data['timestamp'], datetime):
                    data['timestamp'] = data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        
        advice = traffic_assistant.analyze_traffic(request, historical_data)
        
        response_parts = advice.split('\n\n')
        response = TrafficResponse(
            route_suggestion=response_parts[0] if len(response_parts) > 0 else "",
            estimated_time=response_parts[1] if len(response_parts) > 1 else "",
            crowd_level=response_parts[2] if len(response_parts) > 2 else "",
            additional_tips=response_parts[3] if len(response_parts) > 3 else ""
        )
        
        return response
        
    except Exception as e:
        print(f"Error in get_traffic_advice: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )