import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate("firebase_service_account.json")
firebase_admin.initialize_app(cred)

print("✅ Firebase conectado com sucesso!")