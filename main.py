from fastapi import FastAPI, HTTPException, status
import model
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("url")
key = os.getenv("key")

app = FastAPI()
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

def user_exist(supabase, username, email):
    # Vérifie si l'email ou l'identifiant existe déjà dans la base de données
    response = supabase.table('user').select('*').or_(
        f'username.eq.{username}, email.eq.{email}'
    ).execute()
    if response.data:
        return True
    return False

def get_email_by_username(supabase, username: str):
    response = supabase.table('user').select('email').eq(
        'username', username
    ).execute()
    if response.data:
        return response.data[0]['email']
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

@app.post('/register')
def signup(user_data: model.Signup):
    try:
        supabase = supabaseClient()

        # Vérifier si l'identifiant ou l'email existent déjà
        if user_exist(supabase, user_data.username, user_data.email):
            # Vérifier si c'est l'email ou le username qui est déjà pris et envoyer un message d'erreur explicite
            response = supabase.table('user').select('*').eq('username', user_data.username).execute()
            if response.data:
                raise HTTPException(status_code=409, detail="L'identifiant est déjà utilisé.")
            
            response = supabase.table('user').select('*').eq('email', user_data.email).execute()
            if response.data:
                raise HTTPException(status_code=409, detail="L'email est déjà utilisé.")
            
            # Si les deux sont déjà utilisés
            raise HTTPException(status_code=409, detail="L'identifiant et l'email sont déjà utilisés.")
        
        # Si l'email et l'identifiant sont valides, procéder à l'inscription
        response = supabase.auth.sign_up({
            'email': user_data.email,
            'password': user_data.password,
        })
        supabase.table('user').insert({'username': user_data.username, 'email': user_data.email}).execute()
        return response

    except HTTPException as e:
        # Utiliser la gestion d'erreur explicite pour HTTPException
        raise e
    except Exception as e:
        # Gérer les erreurs inattendues
        raise HTTPException(status_code=UNKNOWN_STATUS_CODE, detail="Une erreur inattendue est survenue : " + str(e))

@app.post('/verify-otp')
def verify_otp(otp_data: model.VerifyOtp):
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
def login(user_data: model.Login):
    try:
        supabase = supabaseClient()
        email = get_email_by_username(supabase, user_data.username)
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': user_data.password
        })
        return jsonable_encoder(response.session)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erreur d'authentification : " + str(e)
        )

@app.get('/users')
def get_users():
    supabase = supabaseClient()
    response = supabase.table("user").select("*").execute()
    return response.data
