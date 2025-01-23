from fastapi import FastAPI, HTTPException, status,Depends
import model
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from typing import Annotated
import base64
from datetime import datetime
import uuid
from model import UpdateUserProfile

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

supabaseDep = Annotated[Client, Depends(supabaseClient)]

def user_exist(supabase: supabaseDep, username,email):
    response = supabase.table('user').select('*').or_(
    f'username.eq.{username}, email.eq.{email}'
    ).execute()
    if response.data:
        return True
    else:
        return False
    
def get_email_by_username(supabase: supabaseDep, username: str):
    response = supabase.table('user').select('email').eq(
    'username', username
    ).execute()
    if response.data:
        return response.data[0]['email']
    raise HTTPException(status_code=404, detail="Utilisateur non trouvé")


@app.post('/register')
def signup(supabase: supabaseDep,user_data:model.Signup):
    try:
        
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
def verify_otp( supabase: supabaseDep,otp_data: model.VerifyOtp):
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
def Login(supabase: supabaseDep,user_data: model.Login):
    try: 

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

@app.get('/users')
def get_users( supabase: supabaseDep):
    response= supabase.table("user").select("*").execute()
    return response.data     

@app.get('/user')
def get_users(supabase: supabaseDep,username: str):
    response= supabase.table("user").select("*").eq('username', username).execute()
    return response.data[0]

@app.put("/update-user")
async def update_user(supabase: supabaseDep, data: UpdateUserProfile):
    try:
        # Préparer les données à mettre à jour
        update_data = {
            "name": data.name,
            "phone": data.phone,
            "description": data.description,
            "profile_picture_url": data.profile_picture_url,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Mettre à jour l'utilisateur dans la base de données
        response = supabase.table("user").update(update_data).eq("username", data.username).execute()
        
        if response.data:
            return {
                "status": "success",
                "data": response.data[0] if response.data else None
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de mettre à jour l'utilisateur"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/profile-picture/{username}")
async def get_profile_picture(supabase: supabaseDep, username: str):
    try:
        response = supabase.table("user").select("profile_picture_url").eq("username", username).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"profile_picture_url": response.data[0]["profile_picture_url"]}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/update-profile-picture")
async def update_profile_picture(supabase: supabaseDep, data: model.UpdateProfilePicture):
    try:
        # Decode base64 image
        image_data = base64.b64decode(data.file_data)
        
        # Generate unique filename
        file_ext = "jpg"  # You might want to make this dynamic based on the actual image type
        filename = f"{data.username}_{uuid.uuid4()}.{file_ext}"
        
        # Upload to Supabase Storage
        storage_response = supabase.storage.from_("profile-pictures").upload(
            filename,
            image_data,
            {"content-type": "image/jpeg"}
        )
        
        # Get public URL
        file_url = supabase.storage.from_("profile-pictures").get_public_url(filename)
        
        # Update user profile in database
        response = supabase.table("user").update(
            {"profile_picture_url": file_url, "updated_at": datetime.utcnow().isoformat()}
        ).eq("username", data.username).execute()
        
        return {"status": "success", "profile_picture_url": file_url}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.delete("/remove-profile-picture")
async def remove_profile_picture(supabase: supabaseDep, data: model.RemoveProfilePicture):
    try:
        # Récupérer l'URL actuelle de la photo de profil
        user = supabase.table("user").select("profile_picture_url").eq("username", data.username).execute()
        
        if user.data and user.data[0].get("profile_picture_url"):
            current_url = user.data[0]["profile_picture_url"]
            
            # Extraire le nom du fichier de l'URL
            filename = current_url.split("/")[-1]
            
            # Supprimer le fichier du stockage Supabase
            supabase.storage.from_("profile-pictures").remove([filename])
            
            # Mettre à jour l'utilisateur dans la base de données
            response = supabase.table("user").update({
                "profile_picture_url": None,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("username", data.username).execute()
            
            return {"status": "success", "message": "Photo de profil supprimée avec succès"}
        else:
            return {"status": "success", "message": "Aucune photo de profil à supprimer"}
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )        
        
    # return {
    #     "message": "Connexion réussie",
    #     "access_token": response['data']['access_token'],
    #     "user": response['data']['user']
    # }
