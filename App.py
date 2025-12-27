import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import time as timer_module
import random 
import os

# ==============================================================================
# 1. CONFIGURATION (VERSION 46 - PRIORITÉS & EMPLACEMENT)
# ==============================================================================
st.set_page_config(page_title="Suivi V46", layout="wide", page_icon="📍")

def get_heure_fr():
    return datetime.utcnow() + timedelta(hours=1)

if 'mode_admin' not in st.session_state: st.session_state.mode_admin = False

# --- STYLE CSS (Cartes Priorités) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { background-color: #262730; }
    div[data-testid="stMetric"] { background-color: #1f2937; border: 1px solid #374151; }
    .stButton button { font-weight: bold; }
    
    /* Style Carte Priorité */
    .prio-card {
        background-color: #1a1c24;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 8px;
        border-left: 6px solid #555;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .prio-rank { font-size: 1.2rem; font-weight: bold; color: white; }
    .prio-msn { font-size: 1.4rem; font-weight: bold; color: #61dafb; }
    .prio-loc { font-size: 1.1rem; color: #f1c40f; font-weight: bold; }
    .prio-poste { color: #999; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

if not st.session_state.mode_admin:
    st.markdown("""<style>header, footer, .stDeployButton {display:none;} .block-container{padding-top:1rem;}</style>""", unsafe_allow_html=True)

# ==============================================================================
# 2. CHARGEMENT DONNÉES
# ==============================================================================
FICHIER_LOG_CSV = "Suivi_Mesure.csv"
FICHIER_CONSIGNES_CSV = "Consignes.csv"
FICHIER_OBJECTIF_TXT = "Objectif.txt" 

# Logs
try:
    df = pd.read_csv(FICHIER_LOG_CSV, sep=";", names=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "Info_Sup"], encoding="utf-8")
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Heure"])
except:
    df = pd.DataFrame(columns=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "DateTime", "Info_Sup"])

# Consignes (Avec colonne Emplacement en plus)
try:
    df_consignes = pd.read_csv(FICHIER_CONSIGNES_CSV, sep=";", names=["Type", "MSN", "Poste", "Emplacement"], encoding="utf-8")
except:
    # Fallback si ancien format
    df_consignes = pd.DataFrame(columns=["Type", "MSN", "Poste", "Emplacement"])

# ==============================================================================
# 3. FONCTIONS MÉTIER
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

def get_statut_msn(msn_cherhe, df_logs):
    if df_logs.empty: return "⚪ À faire"
    logs_msn = df_logs[df_logs["MSN_Display"].astype(str).str.contains(str(msn_cherhe), na=False)]
    if logs_msn.empty: return "⚪ À faire"
    derniere_action = logs_msn.sort_values("DateTime").iloc[-1]["Etape"]
    if derniere_action == "FIN": return "🟢 Fini"
    return "🟡 En cours"

# ==============================================================================
# 4. SIDEBAR (Commandes & Admin)
# ==============================================================================
with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
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
        st.subheader("🔧 Intervention")
        causes_choisies = st.multiselect("Réglages :", REGLAGES_GAUCHE + REGLAGES_DROIT + REGLAGES_GENERIC)
        c_start, c_end = st.columns(2)
        if c_start.button("🛑 STOP"):
            now = get_heure_fr()
            with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};MAINTENANCE;System;INCIDENT_EN_COURS;{' + '.join(causes_choisies)}")
            st.rerun()
        if c_end.button("✅ REPRISE"):
            now = get_heure_fr()
            with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};MAINTENANCE;System;INCIDENT_FINI;Reprise")
            st.rerun()

    # --- CHEF D'ÉQUIPE (GESTION CONSIGNES V46) ---
    elif role == "Chef d'Équipe":
        st.subheader("👑 Gestion Shift")
        
        st.markdown("### 📋 Ajouter Ordre de Prod")
        with st.form("form_consigne"):
            c_type = st.selectbox("Type", ["Série", "Rework", "MIP"])
            c_msn = st.text_input("Numéro MSN")
            c_poste = st.selectbox("Pour quel poste ?", ["Poste_01", "Poste_02", "Poste_03"])
            c_loc = st.text_input("📍 Emplacement (Où est la pièce ?)", placeholder="Ex: Étagère 4, Zone Sol...")
            
            if st.form_submit_button("Ajouter à la liste"):
                if c_msn and c_loc:
                    # Enregistrement avec Emplacement
                    with open(FICHIER_CONSIGNES_CSV, "a", encoding="utf-8") as f:
                        f.write(f"\n{c_type};MSN-{c_msn};{c_poste};{c_loc}")
                    st.success("Ajouté !")
                    st.rerun()
                else:
                    st.error("MSN et Emplacement obligatoires !")

        if st.button("🗑️ Effacer toutes les consignes"):
            open(FICHIER_CONSIGNES_CSV, "w", encoding="utf-8").close()
            st.rerun()
            
        st.divider()
        if st.button("⚠️ RAZ Logs Production"):
            open(FICHIER_LOG_CSV, "w", encoding="utf-8").close()
            st.rerun()
            
    st.divider()
    st.checkbox("🔓 Mode Admin", key="mode_admin")

# ==============================================================================
# 5. DASHBOARD PRINCIPAL
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

try:
    with open(FICHIER_OBJECTIF_TXT, "r", encoding="utf-8") as f: target = int(f.read().strip())
except: target = 35
cadence_par_shift = target / 9.0 
delta = nb_realise - (shifts_ecoules * cadence_par_shift)
now = get_heure_fr() 

# HEADER
st.title(f"📍 PRIORITÉS ATELIER | {nom_shift_actuel}")
if delta >= 0: msg, clr = f"🚀 AVANCE : {delta:+.1f}", "#2ecc71"
else: msg, clr = f"🐢 RETARD : {delta:+.1f}", "#e74c3c"
st.markdown(f"<div style='padding:10px;border-radius:5px;background-color:{clr};color:white;text-align:center;font-weight:bold;'>{msg}</div>", unsafe_allow_html=True)

# --- SECTION CONSIGNES (PRIORITÉS) ---
st.write("")
st.subheader("📋 ORDRE DE PASSAGE & EMPLACEMENTS")

col_serie, col_mip, col_rework = st.columns(3)

def afficher_colonne_prio(type_col, couleur_bordure):
    if not df_consignes.empty:
        # Filtrer par type
        items = df_consignes[df_consignes["Type"] == type_col]
        # Afficher dans l'ordre du fichier (1er = Prio 1)
        rank = 1
        for index, row in items.iterrows():
            statut = get_statut_msn(row['MSN'], df)
            
            # Gestion visuelle du statut
            if statut == "🟢 Fini": opacity = "0.4" # Grisé si fini
            elif statut == "🟡 En cours": opacity = "1.0; border: 2px solid #f1c40f" 
            else: opacity = "1.0"
            
            # Carte HTML
            st.markdown(f"""
            <div class="prio-card" style="border-left: 6px solid {couleur_bordure}; opacity: {opacity};">
                <div style="display:flex; justify-content:space-between;">
                    <span class="prio-rank">#{rank}</span>
                    <span class="prio-msn">{row['MSN']}</span>
                </div>
                <div class="prio-loc">📍 {row.get('Emplacement', 'Non précisé')}</div>
                <div class="prio-poste">Pour: {row['Poste']} — {statut}</div>
            </div>
            """, unsafe_allow_html=True)
            rank += 1
    else:
        st.caption("Aucune consigne.")

with col_serie:
    st.markdown("### 🟦 SÉRIE (Priorités)")
    afficher_colonne_prio("Série", "#3498db")

with col_mip:
    st.markdown("### 🟧 MIP (Priorités)")
    afficher_colonne_prio("MIP", "#e67e22")

with col_rework:
    st.markdown("### 🟥 REWORK (Priorités)")
    afficher_colonne_prio("Rework", "#c0392b")

st.divider()

# --- ÉTAT DES POSTES ---
st.subheader("📡 État des Postes (Live)")
cols = st.columns(3)
TEMPS_RESTANT = { "PHASE_SETUP": 245, "STATION_BRAS": 210, "STATION_TRK1": 175, "STATION_TRK2": 85, "PHASE_RAPPORT": 45, "PHASE_DESETUP": 25, "FIN": 0 }

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
                st.markdown(f"⏱️ Arrêt : **{int((now - row_abs['DateTime']).total_seconds() / 60)} min**")
            
            elif not info_prod.empty:
                row_prod = info_prod.iloc[0]
                if row_prod.get('Progression', 0) < 100:
                    icon = "🟨" if row_prod['Etape'] == "PHASE_SETUP" else ("🟪" if row_prod['Etape'] == "PHASE_DESETUP" else "🟦")
                    if row_prod['Type'] == "Rework": icon = "🟥"
                    st.markdown(f"### {icon} {p}"); st.markdown(f"## **{row_prod['MSN_Display']}**")
                    st.progress(int(row_prod.get('Progression', 0)))
                    reste = TEMPS_RESTANT.get(row_prod['Etape'], 30)
                    sortie = now + timedelta(minutes=reste)
                    st.caption(f"📍 {row_prod['Etape']}"); st.markdown(f"⏳ Reste : **{reste} min**")
                    st.markdown(f"🏁 Sortie : **{sortie.strftime('%H:%M')}**")
                else:
                    st.markdown(f"### 🟦 {p}"); st.success("✅ Poste Libre")
            else: st.markdown(f"### ⬜ {p}"); st.info("En attente")

timer_module.sleep(10); st.rerun()
