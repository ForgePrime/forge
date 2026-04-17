from fastapi import FastAPI

from app.auth.routes import router as auth_router
from app.stock.routes import router as stock_router

app = FastAPI(title="WarehouseFlow API")
app.include_router(auth_router)
app.include_router(stock_router)
