import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import time as timer_module
import random 
import os

# ==============================================================================
# 1. CONFIGURATION (VERSION 53 - LOGIQUE PURE)
# ==============================================================================
st.set_page_config(page_title="Suivi V53", layout="wide", page_icon="🏭")

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
    div[data-testid="stMetricValue"] { font-size: 2.8rem !important; font-weight: bold; color: white; }
    div[data-testid="stMetricLabel"] { color: #9ca3af; font-size: 1.1rem !important; }
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
</style>
""", unsafe_allow_html=True)

if not st.session_state.mode_admin:
    st.markdown("""<style>header, footer, .stDeployButton {display:none;} .block-container{padding-top:1rem;}</style>""", unsafe_allow_html=True)

# ==============================================================================
# 2. DONNÉES & FONCTIONS MÉTIER
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

REGLAGES_GAUCHE = ["🔧 Capot Gauche (ST1)", "🔧 PAF", "🔧 Cornière SSAV Gauche", "🔧 Bandeau APF Gauche"]
REGLAGES_DROIT = ["🔧 Capot Droit (ST2)", "🔧 Cornière SSAV Droite", "🔧 Bandeau APF Droit"]
REGLAGES_GENERIC = ["⚠️ SO3 - Pipes Arrière", "💻 Bug Informatique", "🛑 Problème Mécanique", "📏 Calibrage Tracker"]

def get_start_of_week():
    now = get_heure_fr()
    today_weekday = now.weekday() 
    monday_six_thirty = now.replace(hour=6, minute=30, second=0, microsecond=0) - timedelta(days=today_weekday)
    if today_weekday == 0 and now.time() < time(6, 30): monday_six_thirty -= timedelta(days=7)
    return monday_six_thirty

# C'EST ICI QUE SE FAIT LE CALCUL DES SHIFTS PASSÉS (LA BASE DE TOUT)
def get_current_shift_info():
    now = get_heure_fr()
    day = now.weekday() 
    t = now.time()
    nom_shift = "💤 Hors Shift"
    shifts_passes = 0.0
    
    # Calcul des jours complets passés (Lundi, Mardi...) x 2 shifts
    if day < 4: shifts_passes = day * 2
    elif day == 4: shifts_passes = 8
    else: shifts_passes = 9

    # Ajout du shift en cours
    if day < 4: # Lundi-Jeudi
        if time(6,30) <= t < time(14,50): 
            nom_shift = "🌅 Shift Matin"
            shifts_passes += 0.5 # On compte la moitié du shift car en cours
        elif time(14,50) <= t or t <= time(0,9): 
            nom_shift = "🌙 Shift Soir"
            shifts_passes += 1.5 # Matin (1) + moitié Soir (0.5)
        else:
            shifts_passes += 2.0 # Journée finie
    elif day == 4: # Vendredi
        if time(6,30) <= t < time(15,50): 
            nom_shift = "🌅 Shift Matin (Vendredi)"
            shifts_passes += 0.5
        else:
            shifts_passes += 1.0 # Semaine finie
            
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

def get_info_msn(msn_cherhe, df_logs):
    if df_logs.empty: return "⚪ À faire", "⚡ Premier Dispo"
    logs_msn = df_logs[df_logs["MSN_Display"].astype(str).str.contains(str(msn_cherhe), na=False)]
    if logs_msn.empty: return "⚪ À faire", "⚡ Premier Dispo"
    last_log = logs_msn.sort_values("DateTime").iloc[-1]
    qui = last_log["Poste"]
    if last_log["Etape"] == "FIN": return "🟢 Fini", f"✅ Fait par {qui}"
    return "🟡 En cours", f"🛠️ Pris par {qui}"

# ==============================================================================
# 4. SIDEBAR
# ==============================================================================
sim_mode = False; nb_pieces_simu = 0

with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
    st.divider()
    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe", "RDZ (Responsable)"])
    st.divider()
    
# ------------------------------------------------
    # 🟢 OPÉRATEUR (AVEC SÉCURITÉ ANTI-DOUBLON)
    # ------------------------------------------------
    if role == "Opérateur":
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
        st.subheader("🔨 Production")

        # 1. VERIF : MON POSTE EST-IL OCCUPÉ ?
        poste_occupe = False
        msn_en_cours = ""
        se_unique_en_cours = ""
        type_en_cours = "Série"

        if not df.empty:
            df_poste = df[df["Poste"] == sim_poste].sort_values("DateTime")
            if not df_poste.empty:
                last_action = df_poste.iloc[-1]
                if last_action["Etape"] != "FIN":
                    poste_occupe = True
                    msn_en_cours = str(last_action["MSN_Display"]).replace("MSN-", "")
                    se_unique_en_cours = last_action["SE_Unique"]
                    if se_unique_en_cours.startswith("R"): type_en_cours = "Rework"
                    elif se_unique_en_cours.startswith("M"): type_en_cours = "MIP"

        # --- CAS 1 : POSTE OCCUPÉ ---
        if poste_occupe:
            st.warning(f"⚠️ **EN COURS : MSN-{msn_en_cours}**")
            st.caption("Terminez ce cycle pour en commencer un autre.")
            sim_msn = msn_en_cours
            nom_se_complet = se_unique_en_cours
            sim_type = type_en_cours

            c1, c2 = st.columns(2)
            if c1.button("🔵 Bras"):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};MSN-{sim_msn};STATION_BRAS")
                st.rerun()
            if c2.button("🔵 Trk 1"):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};MSN-{sim_msn};STATION_TRK1")
                st.rerun()
            if st.button("🔵 Track 2", use_container_width=True):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};MSN-{sim_msn};STATION_TRK2")
                st.rerun()
            st.write("")
            if st.button("🟣 Fin / Démont.", use_container_width=True):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};MSN-{sim_msn};PHASE_DESETUP")
                st.rerun()
            if st.button("✅ LIBÉRER (FINI)", type="primary", use_container_width=True):
                now = get_heure_fr()
                with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};Aucun;Aucun;FIN")
                st.rerun()

        # --- CAS 2 : POSTE LIBRE ---
        else:
            st.success("✅ Poste Libre")
            sim_type = st.radio("Type", ["Série", "Rework", "MIP"], horizontal=True)
            
            # Choix MSN
            if not df_consignes.empty:
                liste_msn = df_consignes["MSN"].unique().tolist()
                st.markdown("👇 **Prendre dans la liste :**")
                selection_msn = st.selectbox("Sélection MSN", liste_msn)
                sim_msn = selection_msn.replace("MSN-", "")
            else:
                col_msn, col_rand = st.columns([3, 1])
                if "current_msn" not in st.session_state: st.session_state.current_msn = "MSN-001"
                if col_rand.button("🎲"): st.session_state.current_msn = f"MSN-{random.randint(100, 999)}"; st.rerun()
                st.warning("⚠️ Aucune consigne, saisie manuelle.")
                sim_msn = col_msn.text_input("Saisie MSN", st.session_state.current_msn)

            # --- VERROU GLOBAL ---
            msn_deja_pris = False
            qui_a_le_msn = ""
            
            if not df.empty:
                df_msn_check = df[df["MSN_Display"] == f"MSN-{sim_msn}"].sort_values("DateTime")
                if not df_msn_check.empty:
                    last_check = df_msn_check.iloc[-1]
                    if last_check["Etape"] != "FIN" and last_check["Poste"] != sim_poste:
                        msn_deja_pris = True
                        qui_a_le_msn = last_check["Poste"]

            prefix = "S" if sim_type == "Série" else ("R" if sim_type == "Rework" else "M")
            nom_se_complet = f"{prefix}-SE-MSN-{sim_msn}"
            
            st.markdown("---")
            
            if msn_deja_pris:
                # 🛑 C'EST ICI QUE CA BLOQUE LE BOUTON
                st.error(f"⛔ STOP ! {qui_a_le_msn} travaille déjà dessus !")
                st.caption("Impossible de démarrer ce MSN.")
            else:
                if st.button("🟡 DÉMARRER (Setup)", use_container_width=True, type="primary"):
                    now = get_heure_fr()
                    with open(FICHIER_LOG_CSV, "a", encoding="utf-8") as f: f.write(f"\n{now.strftime('%Y-%m-%d')};{now.strftime('%H:%M:%S')};{sim_poste};{nom_se_complet};MSN-{sim_msn};PHASE_SETUP")
                    st.rerun()

    # RÉGLEUR
    elif role == "Régleur":
        pwd = st.text_input("🔑 Code PIN Régleur", type="password")
        if pwd == MOT_DE_PASSE_REGLEUR:
            st.success("Accès autorisé")
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
        elif pwd: st.error("⛔ Code Faux !")

    # CHEF D'ÉQUIPE (SIMULATION SIMPLIFIÉE)
    elif role == "Chef d'Équipe":
        pwd = st.text_input("🔑 Code PIN Chef", type="password")
        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")
            st.subheader("👑 Pilotage & Simu")
            
            # SIMULATION SIMPLIFIEE : On demande juste le nombre de pièces
            sim_mode = st.checkbox("🔮 Activer Simulation", value=False)
            if sim_mode:
                st.markdown("### 🧮 Test de Résultat")
                st.caption("Si on atteint ce nombre de pièces MAINTENANT, est-on bon ?")
                nb_pieces_simu = st.number_input("Nombre de pièces total :", value=10)
                
            st.divider()
            if st.button("⚠️ RAZ Logs Production"):
                open(FICHIER_LOG_CSV, "w", encoding="utf-8").close()
                st.rerun()
        elif pwd: st.error("⛔ Code Faux !")

    # RDZ
    elif role == "RDZ (Responsable)":
        pwd = st.text_input("🔑 Code PIN RDZ", type="password")
        if pwd == MOT_DE_PASSE_CHEF: 
            st.success("Accès autorisé")
            st.subheader("📋 Gestion Consignes")
            with st.form("form_consigne"):
                c_type = st.selectbox("Type", ["Série", "Rework", "MIP"])
                c_msn = st.text_input("Numéro MSN")
                c_loc = st.text_input("📍 Emplacement", placeholder="Ex: Étagère 4...")
                if st.form_submit_button("Ajouter Priorité"):
                    already_exists = False
                    if not df_consignes.empty:
                        if f"MSN-{c_msn}" in df_consignes["MSN"].values: already_exists = True
                    if already_exists: st.error(f"⚠️ {c_msn} existe déjà !")
                    elif c_msn and c_loc:
                        with open(FICHIER_CONSIGNES_CSV, "a", encoding="utf-8") as f:
                            f.write(f"\n{c_type};MSN-{c_msn};Indifférent;{c_loc}")
                        st.success("Ajouté !")
                        st.rerun()
                    else: st.error("Infos manquantes !")
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
        elif pwd: st.error("⛔ Code Faux !")

    st.divider()
    st.checkbox("🔓 Mode Admin", key="mode_admin")

# ==============================================================================
# 5. CALCULS (LE COEUR DU SYSTÈME)
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

# --- LE CALCUL MAGIQUE QUE TU VOULAIS ---
# 1. On calcule la vitesse requise par shift (ex: 35 / 9 = 3.88)
cadence_par_shift = target / 9.0 

# 2. On regarde si on est en simulation ou en réel
if sim_mode:
    # Mode SIMULATION : On compare "Nombre Simulés" vs "Temps RÉEL écoulé"
    # Question : "Si j'ai fait 10 pièces MAINTENANT, suis-je bon ?"
    delta = nb_pieces_simu - (shifts_ecoules * cadence_par_shift)
    affichage_realise = nb_pieces_simu
    titre_mode = "🔮 SIMULATION (TEST)"
    couleur_bandeau = "#9b59b6"
else:
    # Mode RÉEL : On compare "Nombre Vrai" vs "Temps RÉEL écoulé"
    delta = nb_realise - (shifts_ecoules * cadence_par_shift)
    affichage_realise = nb_realise
    titre_mode = f"📍 PILOTAGE LIVE | {nom_shift_actuel}"
    couleur_bandeau = "#2ecc71" if delta >= 0 else "#e74c3c"

now = get_heure_fr() 

# HEADER
st.title(titre_mode)

if sim_mode: msg = f"Avec {int(nb_pieces_simu)} pièces MAINTENANT 👉 DELTA : {delta:+.1f}"
else: msg = f"🚀 AVANCE : {delta:+.1f}" if delta >= 0 else f"🐢 RETARD : {delta:+.1f}"

st.markdown(f"<div style='padding:10px;border-radius:5px;background-color:{couleur_bandeau};color:white;text-align:center;font-weight:bold;'>{msg}</div>", unsafe_allow_html=True)

if not sim_mode:
    st.write("")
    st.subheader("📋 ORDRE DE PASSAGE & EMPLACEMENTS")
    col_serie, col_mip, col_rework = st.columns(3)
    def afficher_colonne_prio(type_col, couleur_bordure):
        if not df_consignes.empty:
            items = df_consignes[df_consignes["Type"] == type_col]
            rank = 1
            for index, row in items.iterrows():
                txt_statut, txt_qui = get_info_msn(row['MSN'], df)
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
k2.metric("📊 Réalisé", affichage_realise)
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
                    
                    if reste >= 60: str_duree = f"{reste // 60}h{reste % 60:02d}"
                    else: str_duree = f"{reste} min"
                    
                    st.caption(f"📍 {row_prod['Etape']}"); st.markdown(f"⏳ Reste : **{str_duree}**")
                    st.markdown(f"🏁 Sortie : **{sortie.strftime('%H:%M')}**")
                else:
                    st.markdown(f"### 🟦 {p}"); st.success("✅ Poste Libre")
            else: st.markdown(f"### ⬜ {p}"); st.info("En attente")

timer_module.sleep(10); st.rerun()
