from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import mysql.connector
from mysql.connector import errorcode
import os

app = FastAPI()

# CORSミドルウェアを追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース接続情報の設定
config = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME"),
    'client_flags': [mysql.connector.ClientFlag.SSL],
    'ssl_ca': '/home/site/certificates/DigiCertGlobalRootG2.crt.pem'
}

# Place モデルの定義
class Place(BaseModel):
    id: Optional[int] = None
    placename: str
    description: str
    latitude: float
    longitude: float
    category: str
    url: str

# データベース接続関数
def get_db_connection():
    try:
        conn = mysql.connector.connect(**config)
        return conn
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            raise HTTPException(status_code=500, detail="Database access denied")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            raise HTTPException(status_code=500, detail="Database does not exist")
        else:
            raise HTTPException(status_code=500, detail=str(err))

# places テーブルの作成
@app.on_event("startup")
async def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS places (
                id INT AUTO_INCREMENT PRIMARY KEY,
                placename VARCHAR(255) NOT NULL,
                description TEXT,
                latitude DOUBLE NOT NULL,
                longitude DOUBLE NOT NULL,
                category VARCHAR(50) NOT NULL,
                url TEXT
            )
        """)
        conn.commit()
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

# 全ての場所を取得
@app.get("/places", response_model=List[Place])
async def get_places():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM places")
        places = cursor.fetchall()
        return places
    finally:
        cursor.close()
        conn.close()

# 新しい場所を追加
@app.post("/places", response_model=Place)
async def create_place(place: Place):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO places (placename, description, latitude, longitude, category, url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (place.placename, place.description, place.latitude, place.longitude, place.category, place.url))
        conn.commit()
        place_id = cursor.lastrowid
        cursor.execute("SELECT * FROM places WHERE id = %s", (place_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

# IDで場所を取得
@app.get("/places/{place_id}", response_model=Place)
async def get_place(place_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM places WHERE id = %s", (place_id,))
        place = cursor.fetchone()
        if place is None:
            raise HTTPException(status_code=404, detail="Place not found")
        return place
    finally:
        cursor.close()
        conn.close()

# カテゴリーで場所を取得
@app.get("/places/category/{category}", response_model=List[Place])
async def get_places_by_category(category: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM places WHERE category = %s", (category,))
        places = cursor.fetchall()
        return places
    finally:
        cursor.close()
        conn.close()

# 場所を更新
@app.put("/places/{place_id}", response_model=Place)
async def update_place(place_id: int, place: Place):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            UPDATE places 
            SET placename = %s, description = %s, latitude = %s, longitude = %s, category = %s, url = %s
            WHERE id = %s
        """, (place.placename, place.description, place.latitude, place.longitude, place.category, place.url, place_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Place not found")
            
        cursor.execute("SELECT * FROM places WHERE id = %s", (place_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

# 場所を削除
@app.delete("/places/{place_id}")
async def delete_place(place_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM places WHERE id = %s", (place_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Place not found")
        return {"message": "Place deleted successfully"}
    finally:
        cursor.close()
        conn.close()

@app.get("/")
def read_root():
    return {"Hello": "World"}