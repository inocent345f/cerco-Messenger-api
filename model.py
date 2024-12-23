from pydantic import BaseModel

class Signup(BaseModel):
    username: str
    email: str
    password : str
    
class Login(BaseModel):
    username: str
    password: str
    

class VerifyOtp(BaseModel):
    type: str
    token: str
    email: str
