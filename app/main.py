from fastapi import FastAPI
from app.database import init_db  # Import init_db function
from app.routes.employee import router as employee_router
from app.routes.attendance import router as attendance_router
from app.routes.breaks import router as breaks_router
from app.routes.information import router as restaurant_hours
from app.routes.bonus import router as bonus
from app.routes.penalty import router as penalty
from app.routes.task import router as task
from fastapi.middleware.cors import CORSMiddleware
import logging





app = FastAPI()

# Set up logging to see if CORS headers are applied
logging.basicConfig(level=logging.INFO)

origins = [
    "http://localhost:5173",  # React development server
    "http://localhost:3000",  # React development server
    "https://employee-clock-frontend.vercel.app/"
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,  # Allows cookies to be included in requests
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Initialize the database tables on app startup
@app.on_event("startup")
def on_startup():
    init_db()  # Creates tables if they don't exist
    logging.info("Database initialized.")

@app.get("/")
def read_root():
    logging.info("Root endpoint accessed")
    return {"message": "Welcome to the Employee Time Tracking API"}

# Include routes for employee, attendance, and breaks
app.include_router(employee_router)
app.include_router(attendance_router)
app.include_router(breaks_router)
app.include_router(restaurant_hours)
app.include_router(bonus)
app.include_router(penalty)
app.include_router(task)