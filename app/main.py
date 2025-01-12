from fastapi import FastAPI
from app.database import init_db  # Import init_db function
from app.routes.employee import router as employee_router
from app.routes.attendance import router as attendance_router
from app.routes.breaks import router as breaks_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:5173",  # React development server
    "http://localhost:3000",  # React development server
    "https://employee-clock-frontend.vercel.app/"
    
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows listed origins
    allow_credentials=True,  # Allows cookies to be included in requests
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Initialize the database tables on app startup
@app.on_event("startup")
def on_startup():
    init_db()  # Creates tables if they don't exist

@app.get("/")
def read_root():
    return {"message": "Welcome to the Employee Time Tracking API"}

app.include_router(employee_router)
app.include_router(attendance_router)
app.include_router(breaks_router)
