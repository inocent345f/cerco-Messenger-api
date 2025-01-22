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

# Vérification si l'utilisateur ou l'email existe déjà
def user_exist(supabase, username, email):
    username_exists = supabase.table('user').select('*').eq('username', username).execute().data
    email_exists = supabase.table('user').select('*').eq('email', email).execute().data
    
    if username_exists:
        return "username"
    if email_exists:
        return "email"
    return None
    
def get_email_by_username(supabase, username: str):
    response = supabase.table('user').select('email').eq('username', username).execute()
    if response.data:
        return response.data[0]['email']
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

@app.post('/register')
def signup(user_data: model.Signup):
    try:
        supabase = supabaseClient()

        # Vérification si l'identifiant ou l'email existent déjà
        existing_field = user_exist(supabase, user_data.username, user_data.email)
        if existing_field == "username":
            raise HTTPException(status_code=409, detail="L'identifiant est déjà utilisé. Veuillez choisir un autre identifiant.")
        elif existing_field == "email":
            raise HTTPException(status_code=409, detail="L'email est déjà utilisé. Veuillez en utiliser un autre.")

        # Validation du mot de passe (longueur minimale de 6 caractères)
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Le mot de passe doit comporter au moins 6 caractères.")

        # Enregistrement de l'utilisateur
        response = supabase.auth.sign_up({
            'email': user_data.email,
            'password': user_data.password,
        })
        supabase.table('user').insert({'username': user_data.username, 'email': user_data.email}).execute()
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=UNKNOWN_STATUS_CODE, detail="Une erreur inattendue est survenue. Vérifiez votre connexion et réessayez.")

@app.post('/verify-otp')
def verify_otp(otp_data: model.VerifyOtp):
    try:
        supabase = supabaseClient()
        supabase.auth.verify_otp(jsonable_encoder(otp_data))
        return {"message": "Email vérifié avec succès"}
    except Exception as e:
        if 'Token has expired or is invalid' in str(e):
            raise HTTPException(status_code=WRONG_STATUS_CODE, detail="Le code OTP est invalide ou a expiré.")
        else:
            raise HTTPException(status_code=UNKNOWN_STATUS_CODE, detail="Une erreur inattendue est survenue pendant la vérification OTP.")

@app.post('/login')
def Login(user_data: model.Login):
    try:
        supabase = supabaseClient()
        email = get_email_by_username(supabase, user_data.username)
        
        # Vérification des identifiants de connexion
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': user_data.password
        })
        return jsonable_encoder(response.session)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides ou utilisateur non trouvé. Vérifiez votre identifiant et mot de passe."
        )

@app.get('/users')
def get_users():
    supabase = supabaseClient()
    response = supabase.table("user").select("*").execute()
    return response.data
