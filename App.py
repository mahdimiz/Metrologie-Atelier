import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import time as timer_module
import random 
import os

# ==============================================================================
# 1. CONFIGURATION (VERSION 50 - "PREMIER DISPO")
# ==============================================================================
st.set_page_config(page_title="Suivi V50", layout="wide", page_icon="🏭")

def get_heure_fr():
    return datetime.utcnow() + timedelta(hours=1)

if 'mode_admin' not in st.session_state: st.session_state.mode_admin = False

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: white; }
    [data-testid="stSidebar"] { background-color: #262730; }
    
    /* KPI */
    div[data-testid="stMetric"] {
        background-color: #1f2937; padding: 15px; border-radius: 10px;
        border: 1px solid #374151; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    div[data-testid="stMetricValue"] { font-size: 2.8rem !important; font-weight: bold; color: white; }
    div[data-testid="stMetricLabel"] { color: #9ca3af; font-size: 1.1rem !important; }
    .stButton button { font-weight: bold; }
    
    /* Carte Priorité */
    .prio-card {
        background-color: #1a1c24; padding: 12px; margin-bottom: 8px;
        border-radius: 8px; border-left: 6px solid #555;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    .prio-rank { font-size: 1.2rem; font-weight: bold; color: white; }
    .prio-msn { font-size: 1.4rem; font-weight: bold; color: #61dafb; }
    .prio-loc { font-size: 1.1rem; color: #f1c40f; font-weight: bold; }
    .prio-info { color: #ccc; font-size: 0.95rem; margin-top: 5px;}
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

try:
    df = pd.read_csv(FICHIER_LOG_CSV, sep=";", names=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "Info_Sup"], encoding="utf-8")
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Heure"])
except:
    df = pd.DataFrame(columns=["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "DateTime", "Info_Sup"])

try:
    df_consignes = pd.read_csv(FICHIER_CONSIGNES_CSV, sep=";", names=["Type", "MSN", "Poste", "Emplacement"], encoding="utf-8")
except:
    df_consignes = pd.DataFrame(columns=["Type", "MSN", "Poste", "Emplacement"])

# ==============================================================================
# 3. FONCTIONS INTELLIGENTES
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

# NOUVELLE INTELLIGENCE : Trouve le statut ET qui travaille dessus
def get_info_msn(msn_cherhe, df_logs):
    if df_logs.empty: return "⚪ À faire", "⚡ Premier Dispo"
    
    logs_msn = df_logs[df_logs["MSN_Display"].astype(str).str.contains(str(msn_cherhe), na=False)]
    if logs_msn.empty:
        return "⚪ À faire", "⚡ Premier Dispo"
    
    last_log = logs_msn.sort_values("DateTime").iloc[-1]
    qui = last_log["Poste"]
    
    if last_log["Etape"] == "FIN":
        return "🟢 Fini", f"✅ Fait par {qui}"
    else:
        return "🟡 En cours", f"🛠️ Pris par {qui}"

# ==============================================================================
# 4. SIDEBAR
# ==============================================================================
sim_mode = False; nb_pieces_simu = 0; shift_simu = 0.0

with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
    st.divider()

    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe", "RDZ (Responsable)"])
    st.divider()
    
    # --- OPÉRATEUR ---
    if role == "Opérateur":
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
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
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
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

    # --- CHEF D'ÉQUIPE ---
    elif role == "Chef d'Équipe":
        st.subheader("👑 Pilotage & Simu")
        sim_mode = st.checkbox("🔮 Activer Simulation", value=False)
        if sim_mode:
            st.markdown("### 🧮 Calculateur")
            nb_pieces_simu = st.number_input("Si on finit : X pièces", value=10)
            shift_simu = st.slider("Heures Shift", 0.0, 9.0, 9.0)
        st.divider()
        if st.button("⚠️ RAZ Logs Production"):
            open(FICHIER_LOG_CSV, "w", encoding="utf-8").close()
            st.rerun()

    # --- RDZ (VERSION 50 - SANS POSTE) ---
    elif role == "RDZ (Responsable)":
        st.subheader("📋 Gestion Consignes")
        
        # FORMULAIRE SIMPLIFIÉ (PLUS DE QUESTION DE POSTE)
        with st.form("form_consigne"):
            c_type = st.selectbox("Type", ["Série", "Rework", "MIP"])
            c_msn = st.text_input("Numéro MSN")
            c_loc = st.text_input("📍 Emplacement", placeholder="Ex: Étagère 4...")
            
            # Plus de sélection de poste ici, c'est pour "Indifférent"
            if st.form_submit_button("Ajouter Priorité"):
                already_exists = False
                if not df_consignes.empty:
                    if f"MSN-{c_msn}" in df_consignes["MSN"].values:
                        already_exists = True
                
                if already_exists:
                    st.error(f"⚠️ Le MSN-{c_msn} est déjà dans la liste !")
                elif c_msn and c_loc:
                    with open(FICHIER_CONSIGNES_CSV, "a", encoding="utf-8") as f:
                        # On écrit "Indifférent" dans la colonne Poste
                        f.write(f"\n{c_type};MSN-{c_msn};Indifférent;{c_loc}")
                    st.success("Ajouté !")
                    st.rerun()
                else:
                    st.error("Infos manquantes !")

        st.divider()
        st.markdown("**🗑️ Suppression :**")
        if not df_consignes.empty:
            df_consignes['Label'] = df_consignes['MSN'] + " (" + df_consignes['Type'] + ")"
            to_delete = st.multiselect("Effacer :", df_consignes['Label'].unique())
            if st.button("Supprimer Sélection"):
                df_new = df_consignes[~df_consignes['Label'].isin(to_delete)]
                df_new.drop(columns=['Label'], inplace=True, errors='ignore')
                df_new.to_csv(FICHIER_CONSIGNES_CSV, sep=";", index=False, header=False)
                st.success("Supprimé !")
                st.rerun()
        else: st.caption("Liste vide.")

        if st.button("🔥 Tout effacer (Danger)"):
            open(FICHIER_CONSIGNES_CSV, "w", encoding="utf-8").close()
            st.rerun()

    st.divider()
    st.checkbox("🔓 Mode Admin", key="mode_admin")

# ==============================================================================
# 5. DASHBOARD
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

if sim_mode:
    delta = nb_pieces_simu - (shift_simu * cadence_par_shift)
    affichage_realise = nb_pieces_simu
    titre_mode = "🔮 SIMULATION"
    couleur_bandeau = "#9b59b6"
else:
    delta = nb_realise - (shifts_ecoules * cadence_par_shift)
    affichage_realise = nb_realise
    titre_mode = f"📍 PRIORITÉS ATELIER | {nom_shift_actuel}"
    couleur_bandeau = "#2ecc71" if delta >= 0 else "#e74c3c"

now = get_heure_fr() 
st.title(titre_mode)

if sim_mode: msg = f"SI on fait {int(nb_pieces_simu)} pièces en {shift_simu}h 👉 DELTA : {delta:+.1f}"
else: msg = f"🚀 AVANCE : {delta:+.1f}" if delta >= 0 else f"🐢 RETARD : {delta:+.1f}"

st.markdown(f"<div style='padding:10px;border-radius:5px;background-color:{couleur_bandeau};color:white;text-align:center;font-weight:bold;'>{msg}</div>", unsafe_allow_html=True)

if not sim_mode:
    st.write("")
    st.subheader("📋 ORDRE DE PASSAGE & EMPLACEMENTS")
    col_serie, col_mip, col_rework = st.columns(3)
    
    # FONCTION AFFICHAGE INTELLIGENTE
    def afficher_colonne_prio(type_col, couleur_bordure):
        if not df_consignes.empty:
            items = df_consignes[df_consignes["Type"] == type_col]
            rank = 1
            for index, row in items.iterrows():
                # On utilise la nouvelle fonction qui retourne aussi le poste
                txt_statut, txt_qui = get_info_msn(row['MSN'], df)
                
                # Style dynamique
                if txt_statut == "🟢 Fini": opacity = "0.4"
                elif txt_statut == "🟡 En cours": opacity = "1.0; border: 2px solid #f1c40f"
                else: opacity = "1.0"
                
                st.markdown(f"""
                <div class="prio-card" style="border-left: 6px solid {couleur_bordure}; opacity: {opacity};">
                    <div style="display:flex; justify-content:space-between;">
                        <span class="prio-rank">#{rank}</span>
                        <span class="prio-msn">{row['MSN']}</span>
                    </div>
                    <div class="prio-loc">📍 {row.get('Emplacement', 'Non précisé')}</div>
                    <div class="prio-info">{txt_statut} | {txt_qui}</div>
                </div>
                """, unsafe_allow_html=True)
                rank += 1
        else: st.caption("Aucune consigne.")

    with col_serie:
        st.markdown("### 🟦 SÉRIE"); afficher_colonne_prio("Série", "#3498db")
    with col_mip:
        st.markdown("### 🟧 MIP"); afficher_colonne_prio("MIP", "#e67e22")
    with col_rework:
        st.markdown("### 🟥 REWORK"); afficher_colonne_prio("Rework", "#c0392b")

st.divider()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🎯 Objectif", target)
k2.metric("📊 Réalisé (Simu)" if sim_mode else "📊 Réalisé (Vrai)", affichage_realise)
k3.metric("🔴 Reworks", nb_rework)
k4.metric("🟠 MIPs", nb_mip)
k5.metric("🕒 Heure", now.strftime("%H:%M"))

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
