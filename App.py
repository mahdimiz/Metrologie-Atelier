import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import time as timer_module
import random 
import os

# ==============================================================================
# 1. CONFIGURATION & STYLE (VERSION 41 - TEST HEURE)
# ==============================================================================
st.set_page_config(page_title="Suivi V41", layout="wide", page_icon="🇫🇷")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { background-color: #262730; }
    div[data-testid="stMetric"] {
        background-color: #1f2937; padding: 10px; border-radius: 8px;
        border: 1px solid #374151; text-align: center;
    }
    div[data-testid="stMetricValue"] { font-size: 2.5rem !important; color: white; }
    div[data-testid="stMetricLabel"] { color: #9ca3af; font-size: 1rem; }
    .stButton button { font-weight: bold; }
</style>
""", unsafe_allow_html=True)

FICHIER_LOG_CSV = "Suivi_Mesure.csv"
FICHIER_OBJECTIF_TXT = "Objectif.txt" 

# --- FONCTION MAGIQUE : HEURE FRANCE (HIVER UTC+1) ---
def get_heure_fr():
    # On prend l'heure mondiale (UTC) et on ajoute 1h pour la France
    return datetime.utcnow() + timedelta(hours=1)

# Chargement données
try:
    df = pd.read_csv(FICHIER_LOG_CSV, sep=";", names=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "Info_Sup"], encoding="utf-8")
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Heure"])
except:
    try:
        df = pd.read_csv(FICHIER_LOG_CSV, sep=";", names=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape"], encoding="utf-8")
        df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Heure"])
        df["Info_Sup"] = ""
    except:
        df = pd.DataFrame(columns=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "DateTime", "Info_Sup"])

# ==============================================================================
# 2. LISTES & FONCTIONS
# ==============================================================================
REGLAGES_GAUCHE = ["🔧 Capot Gauche (ST1)", "🔧 PAF", "🔧 Cornière SSAV Gauche", "🔧 Bandeau APF Gauche"]
REGLAGES_DROIT = ["🔧 Capot Droit (ST2)", "🔧 Cornière SSAV Droite", "🔧 Bandeau APF Droit"]
REGLAGES_GENERIC = ["⚠️ SO3 - Pipes Arrière", "💻 Bug Informatique", "🛑 Problème Mécanique", "📏 Calibrage Tracker"]

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
    df_clean = dataframe[~dataframe["Etape"].str.contains("INCIDENT")]
    actions_poste = df_clean[df_clean["Poste"] == poste_choisi].sort_values("DateTime")
    if actions_poste.empty: return "Inconnu"
    derniere_etape = actions_poste.iloc[-1]["Etape"]
    if derniere_etape in ["PHASE_SETUP", "STATION_BRAS", "STATION_TRK1"]: return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2", "PHASE_RAPPORT"]: return "DROIT"
    else: return "GENERIC"

# ==============================================================================
# 3. INTERFACE (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("🎛️ COMMANDES")
    
    # --- DIAGNOSTIC HEURE (VISIBLE POUR VERIFIER) ---
    now_debug = get_heure_fr()
    st.markdown(f"🕒 **Heure France : {now_debug.strftime('%H:%M')}**")
    st.caption("Si cette heure est fausse, contactez le dev.")
    st.divider()

    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe"])
    st.divider()
    sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
    
    # --- OPÉRATEUR ---
    if role == "Opérateur":
        st.subheader("🔨 Production")
        sim_type = st.radio("Type", ["Série", "Rework", "MIP"], horizontal=True)
        col_msn, col_rand = st.columns([3, 1])
        if "current_msn" not in st.session_state: st.session_state.current_msn = "MSN-001"
        if col_rand.button("🎲"): 
            st.session_state.current_msn = f"MSN-{random.randint(100, 999)}"
            st.rerun()
        sim_msn = col_msn.text_input("MSN", st.session_state.current_msn)
        
        prefix = "S" if sim_type == "Série" else ("R" if sim_type == "Rework" else "M")
        nom_se_complet = f"{prefix}-SE-{sim_msn}"
        st.info(f"Cycle : {sim_type} - {sim_msn}")

        if st.button("🟡 Setup / Montage", use_container_width=True):
            now = get_heure_fr()
            with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};{sim_msn};PHASE_SETUP")
            st.rerun()
        if sim_type == "Série":
            c1, c2 = st.columns(2)
            if c1.button("🔵 Bras"):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};{sim_msn};STATION_BRAS")
                st.rerun()
            if c2.button("🔵 Trk 1"):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};{sim_msn};STATION_TRK1")
                st.rerun()
            if st.button("🔵 Track 2", use_container_width=True):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};{sim_msn};STATION_TRK2")
                st.rerun()
        else:
            if st.button("🔵 Tracker (Unique)", use_container_width=True):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};{sim_msn};STATION_TRK1")
                st.rerun()
        st.write("")
        if st.button("🟣 Fin / Démont.", use_container_width=True):
            now = get_heure_fr()
            with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};{sim_msn};PHASE_DESETUP")
            st.rerun()
        if st.button("✅ LIBÉRER", type="primary", use_container_width=True):
            now = get_heure_fr()
            with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};Aucun;Aucun;FIN")
            st.rerun()

    # --- RÉGLEUR ---
    elif role == "Régleur":
        st.subheader("🔧 Intervention Technique")
        contexte = deviner_contexte_poste(sim_poste, df)
        if contexte == "GAUCHE":
            liste_intelligente = REGLAGES_GAUCHE + REGLAGES_GENERIC
            st.info("📍 Poste en ST1 (Gauche) détecté.")
        elif contexte == "DROIT":
            liste_intelligente = REGLAGES_DROIT + REGLAGES_GENERIC
            st.info("📍 Poste en ST2 (Droit) détecté.")
        else:
            liste_intelligente = REGLAGES_GAUCHE + REGLAGES_DROIT + REGLAGES_GENERIC
            st.info("❓ Position inconnue.")
        causes_choisies = st.multiselect("Sélectionnez les réglages :", liste_intelligente)
        c_start, c_end = st.columns(2)
        if c_start.button("🛑 DÉBUT (Arrêt)", type="primary"):
            if not causes_choisies: st.error("⚠️ Cochez une cause !")
            else:
                cause_str = " + ".join(causes_choisies)
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};MAINTENANCE;System;INCIDENT_EN_COURS;{cause_str}")
                st.toast(f"Début : {cause_str}")
                st.rerun()
        if c_end.button("✅ FIN (Reprise)"):
            now = get_heure_fr()
            with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};MAINTENANCE;System;INCIDENT_FINI;Reprise")
            st.toast("Intervention terminée !")
            st.rerun()

    # --- CHEF ---
    elif role == "Chef d'Équipe":
        st.subheader("👑 Admin")
        sim_mode = st.checkbox("Simu", value=False)
        if sim_mode:
            nb_pieces_simu = st.number_input("Nb Pièces", value=10)
            shift_simu = st.slider("Avancement", 0.0, 9.0, 4.5)
        if st.button("⚠️ RAZ CSV"):
            open(FICHIER_LOG_CSV, "w", encoding="utf-8").close()
            st.rerun()
            
    # --- BOUTON DE SAUVEGARDE ---
    st.divider()
    st.caption("💾 Sauvegarde Sécurité")
    try:
        with open(FICHIER_LOG_CSV, "rb") as f:
            st.download_button(label="📥 Télécharger CSV", data=f, file_name="Suivi_Mesure_Backup.csv", mime="text/csv")
    except: pass

# ==============================================================================
# 4. CALCULS ET TRAITEMENT
# ==============================================================================
debut_semaine = get_start_of_week()
nom_shift_actuel, shifts_ecoules = get_current_shift_info()
mapping_etapes = {"PHASE_SETUP": 5, "STATION_BRAS": 15, "STATION_TRK1": 30, "STATION_TRK2": 65, "PHASE_RAPPORT": 90, "PHASE_DESETUP": 95, "FIN": 100}

if not df.empty:
    df = df[df["DateTime"] >= debut_semaine]
    df["Type"] = df["SE_Unique"].apply(analyser_type)
    df["Progression"] = df["Etape"].map(mapping_etapes).fillna(0)
    
    df_prod_pure = df[~df["Etape"].str.contains("INCIDENT")].copy()
    etat_global = df_prod_pure.sort_values("DateTime").groupby("SE_Unique").last().reset_index()
    last_actions_absolute = df.sort_values("DateTime").groupby("Poste").last().reset_index()
    last_actions_prod = df_prod_pure.sort_values("DateTime").groupby("Poste").last().reset_index()

    pieces_terminees = etat_global[etat_global["Progression"] >= 95]
    nb_realise = pieces_terminees[pieces_terminees["Type"] == "Série"].shape[0]
    nb_rework = pieces_terminees[pieces_terminees["Type"] == "Rework"].shape[0]
    nb_mip = pieces_terminees[pieces_terminees["Type"] == "MIP"].shape[0]
else:
    nb_realise = 0; nb_rework = 0; nb_mip = 0; last_actions_absolute = pd.DataFrame(); last_actions_prod = pd.DataFrame()

# --- CALCUL DELTA ---
try:
    with open(FICHIER_OBJECTIF_TXT, "r", encoding="utf-8") as f: target = int(f.read().strip())
except: target = 35

cadence_par_shift = target / 9.0 

if 'sim_mode' in locals() and sim_mode: delta = nb_pieces_simu - (shift_simu * cadence_par_shift); affichage = nb_pieces_simu
else: delta = nb_realise - (shifts_ecoules * cadence_par_shift); affichage = nb_realise

# --- MESSAGES FUN & MOTIVANTS ---
if delta >= 0.5:
    msg, clr, icn, brd = f"🚀 WOOOW ! On est des fusées ! ({delta:+.1f})", "#2ecc71", "🔥", "#27ae60"
elif delta >= -0.5:
    msg, clr, icn, brd = f"😎 ZEN. Tout roule comme sur des roulettes. ({delta:+.1f})", "#3498db", "✅", "#2980b9"
elif delta >= -2.0:
    msg, clr, icn, brd = f"🐢 Oups, petit coup de mou ? On se remotive ! ({delta:+.1f})", "#f39c12", "⚠️", "#d35400"
elif delta >= -4.0:
    msg, clr, icn, brd = f"🔥 C'est le moment de briller ! On remonte ça ensemble ! ({delta:+.1f})", "#e74c3c", "💪", "#c0392b"
else:
    msg, clr, icn, brd = f"🚨 Houston, on a un problème ! Réunion de crise ! ({delta:+.1f})", "#8b0000", "🆘", "#ff0000"

TEMPS_RESTANT = { "PHASE_SETUP": 245, "STATION_BRAS": 210, "STATION_TRK1": 175, "STATION_TRK2": 85, "PHASE_RAPPORT": 45, "PHASE_DESETUP": 25, "FIN": 0 }

# ==============================================================================
# 5. DASHBOARD
# ==============================================================================
# Utilisation de get_heure_fr() pour l'affichage
now = get_heure_fr() 

st.title(f"✅ V41 HEURE FRANCE | {nom_shift_actuel}")
st.markdown(f"<div style='padding:15px;border-radius:10px;background-color:{clr};border:2px solid {brd};color:white;text-align:center;margin-bottom:20px;'><h3>{icn} {msg}</h3></div>", unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🎯 Objectif", target); k2.metric("📊 Réalisé", affichage); k3.metric("🔴 Reworks", nb_rework); k4.metric("🟠 MIPs", nb_mip); k5.metric("🕒 Heure", now.strftime("%H:%M"))

st.subheader("📡 État des Postes")
cols = st.columns(3)

# Logique limite shift
day_num = now.weekday(); limite_shift_actuel = None; message_report = "???"
if day_num < 4: 
    if time(6,30) <= now.time() < time(14,50): limite_shift_actuel = now.replace(hour=14, minute=50, second=0); message_report = "⏭️ Shift Soir"
    elif now.time() >= time(14,50): limite_shift_actuel = (now + timedelta(days=1)).replace(hour=0, minute=9, second=0); message_report = "💤 Demain Matin"
    else: limite_shift_actuel = now - timedelta(minutes=1); message_report = "💤 Demain Matin"
elif day_num == 4: 
    if time(6,30) <= now.time() < time(15,50): limite_shift_actuel = now.replace(hour=15, minute=50, second=0); message_report = "💤 Lundi"
    else: limite_shift_actuel = now - timedelta(minutes=1); message_report = "💤 Lundi"
else: limite_shift_actuel = now - timedelta(minutes=1); message_report = "💤 Lundi"

for i, p in enumerate(["Poste_01", "Poste_02", "Poste_03"]):
    info_abs = last_actions_absolute[last_actions_absolute["Poste"] == p] if not last_actions_absolute.empty else pd.DataFrame()
    info_prod = last_actions_prod[last_actions_prod["Poste"] == p] if not last_actions_prod.empty else pd.DataFrame()

    with cols[i]:
        with st.container(border=True):
            if info_prod.empty and info_abs.empty:
                st.markdown(f"### ⬜ {p}"); st.info("En attente")
                continue

            if not info_abs.empty and info_abs.iloc[0]['Etape'] == "INCIDENT_EN_COURS":
                row_abs = info_abs.iloc[0]
                msn_display = "MAINTENANCE"
                if not info_prod.empty: msn_display = info_prod.iloc[0]['MSN_Display']
                st.markdown(f"### 🟠 {p}"); st.markdown(f"## **{msn_display}**"); st.warning(f"🔧 {row_abs.get('Info_Sup', '')}")
                st.markdown(f"⏱️ Arrêt : **{int((now - row_abs['DateTime']).total_seconds

