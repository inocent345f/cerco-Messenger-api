from pydantic import BaseModel
from typing import Optional

class Signup(BaseModel):
    username: str
    email: str
    password: str
    profile_picture: Optional[str] = None
    
class Login(BaseModel):
    username: str
    password: str
    
class VerifyOtp(BaseModel):
    type: str
    token: str
    email: str

class UpdateProfilePicture(BaseModel):
    username: str
    file_data: str  # Base64 encoded image data

class UpdateUserProfile(BaseModel):
    username: str
    name: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    profile_picture_url: Optional[str] = None

class RemoveProfilePicture(BaseModel):
    username: str

