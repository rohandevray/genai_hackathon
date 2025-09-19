from fastapi import FastAPI, Request , Depends  , Form,HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
import httpx, os
from dotenv import load_dotenv, find_dotenv
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base 
from datetime import datetime, timedelta
from models import User
import jwt 
from pydantic import BaseModel



load_dotenv(find_dotenv())
app = FastAPI()

Base.metadata.create_all(bind=engine)

origins = ["http://localhost:3000"]  # your frontend

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "supersecretkey"
ALGORITHM = "HS256"

# 🔑 Load credentials from environment
CLIENT_ID = os.getenv("ATLASSIAN_CLIENT_ID")
CLIENT_SECRET = os.getenv("ATLASSIAN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ATLASSIAN_REDIRECT_URI")

# In-memory token store (replace with DB for real app)
user_tokens = {}


class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class LoginData(BaseModel):
    email: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def test_connection(db: Session = Depends(get_db)):
    return {"message": "Connected to Cloud SQL postgres!", "db_status": str(db.bind)}    


#user authentication
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/signup")
async def signup(user: UserCreate,request:Request, db: Session = Depends(get_db)):
    print(await request.body())
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pw = pwd_context.hash(user.password)
    new_user = User(name=user.name, email=user.email, password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "Signup successful! Please login."}

@app.post("/login")
def login(user: LoginData, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not pwd_context.verify(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token = jwt.encode({"sub": db_user.email, "exp": datetime.utcnow() + timedelta(minutes=30)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer","username":db_user.name}



# Step 1: Redirect to Atlassian login/consent
@app.get("/connect-jira")
async def connect_jira():
    print(CLIENT_ID)
    print(CLIENT_SECRET)
    auth_url = (
        "https://auth.atlassian.com/authorize?"
        f"audience=api.atlassian.com"
        f"&client_id={CLIENT_ID}"
        f"&scope=read%3Ajira-work%20write%3Ajira-work%20offline_access"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code&prompt=consent"
    )
    return RedirectResponse(auth_url)


# Step 2: Handle callback and exchange code for tokens
@app.get("/jira/callback")
async def jira_callback(code: str):
    token_url = "https://auth.atlassian.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(token_url, json=data)
        token_data = res.json()

    if "access_token" not in token_data:
        return JSONResponse({"error": "Failed to get access token", "details": token_data}, status_code=400)

    access_token = token_data["access_token"]

    # Get Jira cloud site (cloudid)
    async with httpx.AsyncClient() as client:
        res2 = await client.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        resources = res2.json()

    if not resources:
        return {"error": "No Jira instances found for this user"}

    cloudid = resources[0]["id"]

    # Save tokens in memory
    user_tokens["access_token"] = access_token
    user_tokens["cloudid"] = cloudid

    # ✅ Redirect back to frontend instead of JSON dump
    return RedirectResponse("http://localhost:3000/generated-files?connected=jira")


# Step 3: Fetch Jira projects
@app.get("/jira/projects")
async def get_projects():
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.atlassian.com/ex/jira/{user_tokens['cloudid']}/rest/api/3/project",
            headers={"Authorization": f"Bearer {user_tokens['access_token']}"}
        )
    return res.json()


# Step 4: Create Jira issues
@app.post("/jira/create-issues")
async def create_issues(request: Request):
    data = await request.json()
    project_key = data["projectKey"]
    test_cases = data["testCases"]

    created_issues = []
    async with httpx.AsyncClient() as client:
        for tc in test_cases:
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": tc["summary"],
                    "description": tc["description"],
                    "issuetype": {"name": "Task"}
                }
            }
            res = await client.post(
                f"https://api.atlassian.com/ex/jira/{user_tokens['cloudid']}/rest/api/2/issue",
                headers={
                    "Authorization": f"Bearer {user_tokens['access_token']}",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            created_issues.append(res.json())

    return created_issues  # Return array directly for simplicity

# uvicorn main:app --reload --host 0.0.0.0 --port 8000

