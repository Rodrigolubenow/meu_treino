import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import requests

st.set_page_config(page_title="Meu Treino", page_icon="💪", layout="wide")

# --- Firebase Admin (para Firestore/Storage, ações privilegiadas) ---
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase_service_account"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

API_KEY = st.secrets["firebase_web"]["apiKey"]

# --- Funções de Auth (REST do Firebase) ---
def sign_in_with_password(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()  # contém idToken, refreshToken, localId etc.

def sign_up(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

# --- UI de login ---
def login_view():
    st.title("Meu Treino 💪")
    tab_login, tab_signup = st.tabs(["Entrar", "Criar conta"])

    with tab_login:
        email = st.text_input("E-mail", key="login_email")
        pwd = st.text_input("Senha", type="password", key="login_pwd")
        if st.button("Entrar"):
            try:
                data = sign_in_with_password(email, pwd)
                st.session_state["auth"] = {
                    "email": email,
                    "localId": data["localId"],
                    "idToken": data["idToken"],
                    "refreshToken": data["refreshToken"],
                }
                st.rerun()
            except requests.HTTPError as e:
                st.error(f"Erro ao entrar: {e.response.json().get('error', {}).get('message', 'desconhecido')}")

    with tab_signup:
        email2 = st.text_input("E-mail", key="signup_email")
        pwd2 = st.text_input("Senha", type="password", key="signup_pwd")
        if st.button("Criar conta"):
            try:
                data = sign_up(email2, pwd2)
                st.success("Conta criada! Agora faça login.")
            except requests.HTTPError as e:
                st.error(f"Erro ao criar conta: {e.response.json().get('error', {}).get('message', 'desconhecido')}")

# --- Página autenticada ---
def home_view():
    st.sidebar.write(f"Usuário: {st.session_state['auth']['email']}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    st.header("Treino atual")
    # exemplo: carregar documento do usuário no Firestore
    uid = st.session_state["auth"]["localId"]
    user_doc = db.collection("users").document(uid).get()
    user_data = user_doc.to_dict() or {}

    st.write("Dados do usuário:", user_data)

    st.subheader("Criar exercício")
    with st.form("novo_exercicio"):
        grupo = st.selectbox("Grupo", ["A", "B", "C"])
        nome = st.text_input("Nome do exercício")
        carga = st.number_input("Carga (kg)", min_value=0.0, step=2.5)
        youtube = st.text_input("Link do YouTube (opcional)")
        submitted = st.form_submit_button("Salvar")
        if submitted:
            db.collection("users").document(uid).collection("exercicios").add({
                "grupo": grupo,
                "nome": nome,
                "carga": float(carga),
                "youtube": youtube,
                "done": False,
            })
            st.success("Exercício salvo!")
            st.rerun()

    st.subheader("Meus exercícios")
    q = db.collection("users").document(uid).collection("exercicios").stream()
    for doc in q:
        ex = doc.to_dict()
        cols = st.columns([3,1,1])
        with cols[0]:
            st.write(f"**{ex['nome']}** (Grupo {ex['grupo']}) — {ex['carga']} kg")
            if ex.get("youtube"):
                st.write(f"[Vídeo]({ex['youtube']})")
        with cols[1]:
            if st.button("Concluir", key=f"done_{doc.id}"):
                db.collection("users").document(uid).collection("exercicios").document(doc.id).update({"done": True})
                st.rerun()
        with cols[2]:
            if st.button("Excluir", key=f"del_{doc.id}"):
                db.collection("users").document(uid).collection("exercicios").document(doc.id).delete()
                st.rerun()

# --- Roteamento simples ---
if "auth" not in st.session_state:
    login_view()
else:
    home_view()