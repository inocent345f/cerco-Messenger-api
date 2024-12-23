from fastapi import FastAPI, HTTPException, status
from typing import Union
import model
from fastapi.encoders import jsonable_encoder
from typing import Annotated
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

url= os.getenv("url")
key = os.getenv("key")

app =  FastAPI()
WRONG_STATUS_CODE = 400
UNKNOWN_STATUS_CODE = 500

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

def supabaseClient():
    supabase: Client = create_client(url, key)
    return supabase

#supabaseDep = Annotated[Client, Depends(supabaseClient)]

def user_exist(supabase, username,email):
    response = supabase.table('user').select('*').or_(
    f'username.eq.{username}, email.eq.{email}'
    ).execute()
    if response.data:
        return True
    else:
        return False
    
def get_email_by_username(supabase, username: str):
    response = supabase.table('user').select('email').eq(
    'username', username
    ).execute()
    if response.data:
        return response.data[0]['email']
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")


@app.post('/register')
def signup(user_data:model.Signup):
    try:
        supabase = supabaseClient()
        if user_exist(supabase,user_data.username, user_data.email):
            raise HTTPException(status_code=404, detail="l'utilisarteur existe déja")
        response = supabase.auth.sign_up({
            'email': user_data.email,
            'password': user_data.password,
        })
        supabase.table('user').insert({'username': user_data.username, 'email': user_data.email}).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@app.post('/verify-otp')
def verify_otp( otp_data: model.VerifyOtp):
    try:
        supabase = supabaseClient()
        supabase.auth.verify_otp(jsonable_encoder(otp_data))
        return {"message": "Email vérifié avec succès"}
    except Exception as e:
        if 'Token has expired or is invalid' in str(e):
            raise HTTPException(status_code=WRONG_STATUS_CODE, detail=str(e))
        else:
            raise HTTPException(status_code=UNKNOWN_STATUS_CODE, detail=str(e))
        
        
@app.post('/login')
def Login(user_data: model.Login):
    try: 
        supabase = supabaseClient()
        email = get_email_by_username(supabase, user_data.username)
        response =  supabase.auth.sign_in_with_password({
            'email': email, 
            'password': user_data.password
        })
        return jsonable_encoder(response.session)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
        
        
    # return {
    #     "message": "Connexion réussie",
    #     "access_token": response['data']['access_token'],
    #     "user": response['data']['user']
    # }