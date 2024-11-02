from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

@app.get("/")
def read_root():
    return {"Hello": "World"}