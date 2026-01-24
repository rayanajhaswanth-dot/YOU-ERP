from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from database import get_supabase
from auth import get_password_hash, verify_password, create_access_token, get_current_user, TokenData
from datetime import datetime, timezone
import uuid

router = APIRouter()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "pa"
    politician_id: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/register")
async def register(data: RegisterRequest):
    supabase = get_supabase()
    
    existing_user = supabase.table('users').select('*').eq('email', data.email).execute()
    if existing_user.data:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    politician_exists = supabase.table('politicians').select('id').eq('id', data.politician_id).execute()
    if not politician_exists.data:
        raise HTTPException(status_code=400, detail="Invalid politician_id")
    
    hashed_password = get_password_hash(data.password)
    user_id = str(uuid.uuid4())
    
    user_data = {
        'id': user_id,
        'email': data.email,
        'password_hash': hashed_password,
        'full_name': data.full_name,
        'role': data.role,
        'politician_id': data.politician_id,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('users').insert(user_data).execute()
    
    return {"message": "User registered successfully", "user_id": user_id}

@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    supabase = get_supabase()
    
    user_result = supabase.table('users').select('*').eq('email', data.email).execute()
    
    if not user_result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    user = user_result.data[0]
    
    # Check if password_hash exists (for seeded users with password)
    if 'password_hash' in user:
        if not verify_password(data.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid email or password")
    else:
        # For users without password_hash, accept any password (development mode)
        pass
    
    token_payload = {
        "user_id": user['id'],
        "email": user['email'],
        "role": user.get('role', 'politician').lower(),
        "politician_id": user.get('politician_id')
    }
    
    access_token = create_access_token(token_payload)
    
    user_info = {
        "id": user['id'],
        "email": user['email'],
        "full_name": user.get('full_name', user['email'].split('@')[0].title()),
        "role": user.get('role', 'politician').lower(),
        "politician_id": user.get('politician_id')
    }
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_info
    )

@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    supabase = get_supabase()
    user_result = supabase.table('users').select('id, email, full_name, role, politician_id').eq('id', current_user.user_id).execute()
    
    if not user_result.data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_result.data[0]