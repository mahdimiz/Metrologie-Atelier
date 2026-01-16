import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import time as timer_module
import random

# ==============================================================================
# 1. CONFIGURATION (MODE LOCAL / MÉMOIRE)
# ==============================================================================
st.set_page_config(page_title="Suivi V78 Local", layout="wide", page_icon="💻")

# 🔑 MOTS DE PASSE
MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

def get_heure_fr():
    return datetime.utcnow() + timedelta(hours=1)

if 'mode_admin' not in st.session_state: st.session_state.mode_admin = False

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { background-color: #262730; }
    div[data-testid="stMetric"] {
        background-color: #1f2937; padding: 15px; border-radius: 10px;
        border: 1px solid #374151; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    div[data-testid="stMetricValue"] { font-size: 2.2rem !important; font-weight: bold; color: #61dafb; }
    div[data-testid="stMetricLabel"] { color: #9ca3af; font-size: 1.0rem !important; }
    .stButton button { font-weight: bold; }
    .prio-card {
        background-color: #1a1c24; padding: 12px; margin-bottom: 8px;
        border-radius: 8px; border-left: 6px solid #555;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .prio-rank { font-size: 1.2rem; font-weight: bold; color: white; }
    .prio-msn { font-size: 1.4rem; font-weight: bold; color: #61dafb; }
    .prio-loc { font-size: 1.1rem; color: #f1c40f; font-weight: bold; }
    .prio-info { color: #ccc; font-size: 0.95rem; margin-top: 5px;}
    
    @keyframes blink { 50% { opacity: 0.5; } }
    .blink-red {
        animation: blink 1s linear infinite;
        color: #ff4b4b; font-weight: bold; font-size: 1.2rem;
        border: 2px solid #ff4b4b; padding: 10px; border-radius: 5px;
        text-align: center; margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.mode_admin:
    st.markdown("""<style>header, footer, .stDeployButton {display:none;} .block-container{padding-top:1rem;}</style>""", unsafe_allow_html=True)

# ==============================================================================
# 2. GESTION DES DONNÉES (EN MÉMOIRE LOCALE - SESSION_STATE)
# ==============================================================================

# Initialisation des "bases de données" virtuelles
COLS_LOGS = ["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "Info_Sup"]
COLS_CONSIGNES = ["Type", "MSN", "Poste", "Emplacement"]
COLS_PANNES = ["Zone", "Nom"]
COLS_OBJ = ["Valeur"]

if "db_logs" not in st.session_state:
    st.session_state.db_logs = pd.DataFrame(columns=COLS_LOGS)

if "db_consignes" not in st.session_state:
    st.session_state.db_consignes = pd.DataFrame(columns=COLS_CONSIGNES)

if "db_pannes" not in st.session_state:
    data_defaut = [["GAUCHE", "🔧 Capot Gauche (ST1)"], ["GAUCHE", "🔧 PAF"], 
                   ["DROIT", "🔧 Capot Droit (ST2)"], ["GENERIC", "⚠️ SO3 - Pipes"]]
    st.session_state.db_pannes = pd.DataFrame(data_defaut, columns=COLS_PANNES)

if "db_objectif" not in st.session_state:
    st.session_state.db_objectif = pd.DataFrame([[35]], columns=COLS_OBJ)

# Fonctions de lecture/écriture simplifiées
def safe_read(key_name):
    return st.session_state[key_name]

def append_row(key_name, new_row_list, cols):
    df_new = pd.DataFrame([new_row_list], columns=cols)
    st.session_state[key_name] = pd.concat([st.session_state[key_name], df_new], ignore_index=True)

def overwrite_data(key_name, df_to_write):
    st.session_state[key_name] = df_to_write

# --- CHARGEMENT ---
df = safe_read("db_logs")
if not df.empty:
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Heure"], errors='coerce')
    df = df.dropna(subset=["DateTime"]) 
else:
    df["DateTime"] = pd.to_datetime([])

df_consignes = safe_read("db_consignes")
df_pannes = safe_read("db_pannes")
df_obj = safe_read("db_objectif")
VAL_OBJECTIF = int(df_obj.iloc[0]["Valeur"]) if not df_obj.empty else 35

# --- HELPERS LISTES PANNES ---
def get_liste_pannes(zone):
    if df_pannes.empty: return []
    return df_pannes[df_pannes["Zone"] == zone]["Nom"].tolist()

REGLAGES_GAUCHE = get_liste_pannes("GAUCHE")
REGLAGES_DROIT = get_liste_pannes("DROIT")
REGLAGES_GENERIC = get_liste_pannes("GENERIC")

# --- FONCTIONS CALCULS ---
def get_start_of_week():
    now = get_heure_fr()
    today_weekday = now.weekday() 
    monday_six_thirty = now.replace(hour=6, minute=30, second=0, microsecond=0) - timedelta(days=today_weekday)
    if today_weekday == 0 and now.time() < time(6, 30): monday_six_thirty -= timedelta(days=7)
    return monday_six_thirty

def get_current_shift_info():
    now = get_heure_fr()
    day = now.weekday() 
    t = now.time()
    nom_shift = "💤 Hors Shift"
    shifts_passes = 0.0
    if day < 4: shifts_passes = day * 2
    elif day == 4: shifts_passes = 8
    else: shifts_passes = 9
    if day < 4: 
        if time(6,30) <= t < time(14,50): nom_shift, shifts_passes = "🌅 Shift Matin", shifts_passes + 0.5
        elif time(14,50) <= t or t <= time(0,9): nom_shift, shifts_passes = "🌙 Shift Soir", shifts_passes + 1.5
        else: shifts_passes += 2.0 
    elif day == 4: 
        if time(6,30) <= t < time(15,50): nom_shift, shifts_passes = "🌅 Shift Matin (Vendredi)", shifts_passes + 0.5
        else: shifts_passes += 1.0 
    return nom_shift, min(shifts_passes, 9.0)

def analyser_type(se_name):
    if not isinstance(se_name, str) or len(se_name) < 1: return "Inconnu"
    if se_name[0].upper() == "S": return "Série"
    if se_name[0].upper() == "R": return "Rework"
    if se_name[0].upper() == "M": return "MIP"
    return "Autre"

def deviner_contexte_poste(poste_choisi, dataframe):
    if dataframe.empty: return "Inconnu"
    df_clean = dataframe[~dataframe["Etape"].str.contains("INCIDENT|APPEL", na=False)]
    actions_poste = df_clean[df_clean["Poste"] == poste_choisi].sort_values("DateTime")
    if actions_poste.empty: return "Inconnu"
    derniere_etape = actions_poste.iloc[-1]["Etape"]
    if derniere_etape in ["PHASE_SETUP", "STATION_BRAS", "STATION_TRK1"]: return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2", "PHASE_RAPPORT"]: return "DROIT"
    else: return "GENERIC"

def get_info_msn(msn_cherhe, df_logs):
    if df_logs.empty: return "⚪ À faire", "⚡ Premier Dispo"
    logs_msn = df_logs[df_logs["MSN_Display"].astype(str).str.contains(str(msn_cherhe), na=False)]
    if logs_msn.empty: return "⚪ À faire", "⚡ Premier Dispo"
    last_log = logs_msn.sort_values("DateTime").iloc[-1]
    qui = last_log["Poste"]
    if last_log["Etape"] == "FIN": return "🟢 Fini", f"✅ Fait par {qui}"
    return "🟡 En cours", f"🛠️ Pris par {qui}"
    
def calculer_kpi_pannes(dataframe):
    if dataframe.empty: return pd.DataFrame()
    df_maint = dataframe[dataframe['Etape'].isin(['APPEL_REGLAGE', 'INCIDENT_EN_COURS', 'INCIDENT_FINI'])].sort_values('DateTime')
    rapports = []
    
    for poste in df_maint['Poste'].unique():
        logs_poste = df_maint[df_maint['Poste'] == poste].sort_values('DateTime')
        current_cycle = {}
        for index, row in logs_poste.iterrows():
            etape = row['Etape']
            msn_brut = str(row['MSN_Display'])
            msn_clean = msn_brut.replace("MSN-", "") if "MSN-" in msn_brut else msn_brut
            
            if etape == 'APPEL_REGLAGE':
                current_cycle = {'Poste': poste, 'MSN': msn_clean, 'Cause': row['Info_Sup'], 'Heure_Appel': row['DateTime'], 'Heure_Debut': None, 'Heure_Fin': None}
            elif etape == 'INCIDENT_EN_COURS':
                if not current_cycle:
                    current_cycle = {'Poste': poste, 'MSN': msn_clean, 'Cause': row['Info_Sup'], 'Heure_Appel': row['DateTime'], 'Heure_Debut': row['DateTime'], 'Heure_Fin': None}
                else:
                    current_cycle['Heure_Debut'] = row['DateTime']
            elif etape == 'INCIDENT_FINI':
                if current_cycle and current_cycle.get('Heure_Debut'):
                    current_cycle['Heure_Fin'] = row['DateTime']
                    attente = (current_cycle['Heure_Debut'] - current_cycle['Heure_Appel']).total_seconds() / 60
                    reglage = (current_cycle['Heure_Fin'] - current_cycle['Heure_Debut']).total_seconds() / 60
                    rapports.append({
                        "Date": current_cycle['Heure_Appel'].strftime("%d/%m"),
                        "Heure": current_cycle['Heure_Appel'].strftime("%H:%M"),
                        "Poste": poste,
                        "MSN": current_cycle.get('MSN', '?'),
                        "Cause": current_cycle['Cause'],
                        "Attente (min)": int(attente),
                        "Réglage (min)": int(reglage),
                        "Total (min)": int(attente + reglage)
                    })
                    current_cycle = {} 
    return pd.DataFrame(rapports)


# ==============================================================================
# 4. SIDEBAR
# ==============================================================================
sim_mode = False; nb_pieces_simu = 0
acces_chef_ok = False 

with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
    st.divider()
    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe", "RDZ (Responsable)"])
    st.divider()
    
    # 🟢 OPÉRATEUR
    if role == "Opérateur":
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
        st.subheader("🔨 Production")

        poste_occupe = False; msn_en_cours = ""; se_unique_en_cours = ""; type_en_cours = "Série"; etat_appel = False

        if not df.empty:
            df_poste = df[df["Poste"] == sim_poste].sort_values("DateTime")
            if not df_poste.empty:
                last_action = df_poste.iloc[-1]
                if last_action["Etape"] == "APPEL_RE
