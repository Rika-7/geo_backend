from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import errorcode
import os

app = FastAPI()

# CORSミドルウェアを追加
# これにより、フロントエンド（Next.js）からのリクエストを許可する
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # フロントエンドのURLを指定
    allow_credentials=True,
    allow_methods=["*"],
        allow_headers=["*"],
    )

# データベース接続情報の設定
config = {
  'host':os.getenv("DB_HOST"),
  'user':os.getenv("DB_USER"),
  'password':os.getenv("DB_PASSWORD"),
  'database':os.getenv("DB_NAME"),
  'client_flags': [mysql.connector.ClientFlag.SSL],
  'ssl_ca': '/home/site/certificates/DigiCertGlobalRootG2.crt.pem'
}

@app.get("/")
def read_root():
    return {"Hello": "World"}