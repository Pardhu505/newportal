from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import pytz
import jwt
import hashlib
from passlib.context import CryptContext
import pandas as pd
from io import StringIO
from fastapi.responses import StreamingResponse
from bson import ObjectId
import json

# Custom JSON encoder to handle MongoDB ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Department and team data
DEPARTMENT_DATA = {
    "Soul Centre": {
        "Soul Central": ["Atia"],
        "Field Team": ["Siddharth Gautam", "Sai Kiran Gurram", "Akhilesh Mishra"]
    },
    "Directors": {
        "Director": ["Anant Tiwari"],
        "Associate Director": ["Alimpan Banerjee"]
    },
    "Directors team": {
        "Directors Team": ["Himani Sehgal", "Pawan Beniwal", "Aditya Pandit", "Sravya", "Eshwar"]
    },
    "Campaign": {
        "Campaign": ["S S Manoharan"]
    },
    "Data": {
        "Data": ["T. Pardhasaradhi"]
    },
    "Media": {
        "Media": ["Aakanksha Tandon"]
    },
    "Research": {
        "Research": ["P. Srinath Rao"]
    },
    "DMC": {
        "HIVE": ["Madhunisha and Apoorva"],
        "Digital Communication": ["Keerthana"],
        "Digital Production": ["Bapan"]
    },
    "HR": {
        "HR": ["Tejaswini"]
    },
    "Admin": {
        "Operations": ["Nikash"]
    }
}

STATUS_OPTIONS = ["WIP", "Completed", "Yet to Start", "Delayed"]

# Predefined users
PREDEFINED_USERS = [
    {"name": "Lokesh Reddy", "email": "lokeshreddy@showtimeconsulting.in", "password": "Welcome@123", "role": "employee"},
    {"name": "Vinod Kumar P", "email": "vinod.kumar@showtimeconsulting.in", "password": "Welcome@123", "role": "employee"},
    {"name": "Tejaswini Ch", "email": "tejaswini@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "P Srinath Rao", "email": "srinath@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Siddhartha Gautam", "email": "siddharthag@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Akhilesh Mishra", "email": "akhilesh@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Manoharan", "email": "manoharan@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Nikash Kumar", "email": "nikash.kumar@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Bapan Kumar Chanda", "email": "bapankumarchanda@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Keerthana Sampath", "email": "keerthana.sampath@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "T.Pardhasaradhi", "email": "pardhasaradhi@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Atia Latif", "email": "atia@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Gurram Saikiran", "email": "gurram.saikiran@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Himani sehgal", "email": "himani.sehgal@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Aditya Pandit", "email": "aditya.pandit@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Apoorva Singh", "email": "apoorva@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Madhunisha", "email": "madhunisha@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Challa Sravya", "email": "challa.sravya@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Sabavat Eshwar", "email": "sabavat.eshwar@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Robbin Sharma", "email": "rs@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Anant Tiwari", "email": "at@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Alimpan Banerjee", "email": "alimpan@showtimeconsulting.in", "password": "Welcome@123", "role": "manager"},
    {"name": "Test Employee", "email": "test@showtimeconsulting.in", "password": "Welcome@123", "role": "employee", "department": "Data", "team": "Data"},
]

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    password_hash: str
    role: str  # "manager" or "employee"
    department: str = ""
    team: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(IST))

class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str = "employee"  # Default to employee
    department: str = ""
    team: str = ""

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    department: str = ""
    team: str = ""

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    details: str
    status: str

class WorkReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_name: str
    employee_email: str
    department: str
    team: str
    reporting_manager: str
    date: str
    tasks: List[Task]
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(IST))
    last_modified_at: datetime = Field(default_factory=lambda: datetime.now(IST))
    last_modified_by: str = ""

class WorkReportCreate(BaseModel):
    employee_name: str
    department: str
    team: str
    reporting_manager: str
    date: str
    tasks: List[Task]

class WorkReportUpdate(BaseModel):
    tasks: List[Task]

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

# Helper function to convert MongoDB document to dict with proper ObjectId handling
def convert_mongo_doc(doc):
    if doc is None:
        return None
    
    doc_dict = dict(doc)
    
    # Convert ObjectId to string
    if '_id' in doc_dict:
        doc_dict['_id'] = str(doc_dict['_id'])
    
    return doc_dict

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await db.users.find_one({"email": payload.get("sub")})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Convert MongoDB document to dict with proper ObjectId handling
    user_dict = convert_mongo_doc(user)
    return UserResponse(**user_dict)

# Initialize database with predefined users
async def init_database():
    # Check if users already exist
    user_count = await db.users.count_documents({})
    if user_count == 0:
        # Insert predefined users
        users_to_insert = []
        for user_data in PREDEFINED_USERS:
            user = User(
                name=user_data["name"],
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                role=user_data["role"],
                department=user_data.get("department", ""),
                team=user_data.get("team", "")
            )
            users_to_insert.append(user.dict())
        
        await db.users.insert_many(users_to_insert)
        print("Database initialized with predefined users")

@app.on_event("startup")
async def startup_event():
    await init_database()

# Routes
@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Convert MongoDB document to dict with proper ObjectId handling
    user_dict = convert_mongo_doc(user)
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user_dict)
    }

@api_router.post("/auth/signup")
async def signup(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user with provided role or default to employee
    user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        department=user_data.department,
        team=user_data.team
    )
    
    await db.users.insert_one(user.dict())
    
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user.dict())
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@api_router.get("/departments")
async def get_departments():
    return {"departments": DEPARTMENT_DATA}

@api_router.get("/status-options")
async def get_status_options():
    return {"status_options": STATUS_OPTIONS}

@api_router.post("/work-reports")
async def create_work_report(
    report_data: WorkReportCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    report = WorkReport(
        employee_name=report_data.employee_name,
        employee_email=current_user.email,
        department=report_data.department,
        team=report_data.team,
        reporting_manager=report_data.reporting_manager,
        date=report_data.date,
        tasks=report_data.tasks
    )
    
    await db.work_reports.insert_one(report.dict())
    return {"message": "Work report submitted successfully", "report_id": report.id}

@api_router.get("/work-reports")
async def get_work_reports(
    current_user: UserResponse = Depends(get_current_user),
    department: Optional[str] = None,
    team: Optional[str] = None,
    manager: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    # Build query
    query = {}
    
    # If user is employee, only show their reports
    if current_user.role == "employee":
        query["employee_email"] = current_user.email
    
    # Apply filters
    if department and department != "All Departments":
        query["department"] = department
    if team and team != "All Teams":
        query["team"] = team
    if manager and manager != "All Reporting Managers":
        query["reporting_manager"] = manager
    
    # Date filtering
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    elif from_date:
        query["date"] = {"$gte": from_date}
    elif to_date:
        query["date"] = {"$lte": to_date}
    
    cursor = db.work_reports.find(query).sort("submitted_at", -1)
    reports = await cursor.to_list(1000)
    
    # Convert MongoDB documents to dict with proper ObjectId handling
    reports_list = [convert_mongo_doc(report) for report in reports]
    
    return {"reports": reports_list}

@api_router.put("/work-reports/{report_id}")
async def update_work_report(
    report_id: str,
    report_data: WorkReportUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    # Check if user is manager
    if current_user.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can edit reports"
        )
    
    # Find the report
    report = await db.work_reports.find_one({"id": report_id})
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Update the report
    update_data = {
        "tasks": [task.dict() for task in report_data.tasks],
        "last_modified_at": datetime.now(IST),
        "last_modified_by": current_user.email
    }
    
    await db.work_reports.update_one(
        {"id": report_id},
        {"$set": update_data}
    )
    
    return {"message": "Report updated successfully"}

@api_router.get("/work-reports/export/csv")
async def export_csv(
    current_user: UserResponse = Depends(get_current_user),
    department: Optional[str] = None,
    team: Optional[str] = None,
    manager: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
):
    # Build query (same as get_work_reports)
    query = {}
    
    if current_user.role == "employee":
        query["employee_email"] = current_user.email
    
    if department and department != "All Departments":
        query["department"] = department
    if team and team != "All Teams":
        query["team"] = team
    if manager and manager != "All Reporting Managers":
        query["reporting_manager"] = manager
    
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    elif from_date:
        query["date"] = {"$gte": from_date}
    elif to_date:
        query["date"] = {"$lte": to_date}
    
    cursor = db.work_reports.find(query).sort("submitted_at", -1)
    reports = await cursor.to_list(1000)
    
    # Convert MongoDB documents to dict with proper ObjectId handling
    reports_list = [convert_mongo_doc(report) for report in reports]
    
    # Flatten data for CSV
    csv_data = []
    for report in reports_list:
        for task in report["tasks"]:
            csv_data.append({
                "Date": report["date"],
                "Employee Name": report["employee_name"],
                "Department": report["department"],
                "Team": report["team"],
                "Reporting Manager": report["reporting_manager"],
                "Task Details": task["details"],
                "Status": task["status"],
                "Submitted At": report["submitted_at"]
            })
    
    # Create DataFrame and convert to CSV
    df = pd.DataFrame(csv_data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=work_reports.csv"}
    )

@api_router.get("/managers")
async def get_managers():
    cursor = db.users.find({"role": "manager"})
    managers = await cursor.to_list(1000)
    
    # Convert MongoDB documents to dict with proper ObjectId handling
    managers_list = [convert_mongo_doc(manager) for manager in managers]
    
    return {"managers": [{"name": manager["name"], "email": manager["email"]} for manager in managers_list]}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()