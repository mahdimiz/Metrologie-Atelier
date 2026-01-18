import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import time as timer_module
import random

# ==============================================================================
# 1. CONFIGURATION (MODE CLAIR FORCÉ ☀️)
# ==============================================================================
st.set_page_config(page_title="Suivi V78 Local", layout="wide", page_icon="💻")

# 🔑 MOTS DE PASSE
MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

def get_heure_fr():
    return datetime.utcnow() + timedelta(hours=1)

if 'mode_admin' not in st.session_state: st.session_state.mode_admin = False

# --- CSS "CLEAN LIGHT" ---
st.markdown("""
<style>
    .stApp { background-color: #FFFFFF !important; color: #31333F !important; }
    [data-testid="stSidebar"] { background-color: #F0F2F6 !important; border-right: 1px solid #E0E0E0; }
    [data-testid="stSidebar"] * { color: #31333F !important; }
    div[data-testid="stMetric"] { background-color: #F9FAFB !important; border: 1px solid #E5E7EB; border-radius: 8px; padding: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    div[data-testid="stMetricValue"] { color: #0068C9 !important; }
    div[data-testid="stMetricLabel"] { color: #6B7280 !important; }
    .prio-card { background-color: #FFFFFF !important; color: #31333F !important; padding: 15px; margin-bottom: 10px; border-radius: 8px; border: 1px solid #E5E7EB; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .prio-rank { font-size: 1.2rem; font-weight: bold; color: #31333F !important; }
    .prio-msn { font-size: 1.4rem; font-weight: bold; color: #0068C9 !important; }
    .prio-loc { font-size: 1.1rem; color: #D97706 !important; font-weight: bold; }
    .prio-info { color: #6B7280 !important; font-size: 0.95rem; margin-top: 5px; }
    .stButton button { font-weight: bold; border-radius: 8px; height: 3.5em; border: 1px solid #D1D5DB; color: #31333F !important; background-color: #FFFFFF; }
    .stButton button:hover { border-color: #0068C9; color: #0068C9 !important; }
    button[kind="primary"] { background-color: #FF4B4B !important; color: white !important; border: none !important; }
    @keyframes blink { 50% { opacity: 0.5; } }
    .blink-red { animation: blink 1s linear infinite; color: #DC2626 !important; background-color: #FEE2E2 !important; font-weight: bold; font-size: 1.2rem; border: 2px solid #DC2626; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; }
    
    /* Style spécial pour la liste ordonnée des appels */
    .appel-card {
        border-left: 5px solid #DC2626;
        background-color: #FEF2F2;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

if not st.session_state.mode_admin:
    st.markdown("""<style>header, footer, .stDeployButton {display:none;} .block-container{padding-top:1rem;}</style>""", unsafe_allow_html=True)

# ==============================================================================
# 2. LISTES ET DONNÉES
# ==============================================================================

LISTE_ST1 = ["🔧 Capot Gauche", "🔧 PAF", "🔧 Cornière SSAV Gauche", "🔧 Bandeaux APF", "🔧 Pipe AR 1", "🔧 Pipe AR 2", "🔧 Pipe AR 3", "🔧 Pipe AR 4", "🔧 QDP", "⚠️ Autre"]
LISTE_ST2 = ["🔧 Capot Droit", "🔧 Cornière SSAV Droite", "🔧 Bandeaux APF", "⚠️ Autre"]
LISTE_MIP = ["🔧 PAF", "🔧 Capot Gauche", "🔧 Capot Droit", "🔧 Bandeaux APF", "⚠️ Autre"]
LISTE_FULL = sorted(list(set(LISTE_ST1 + LISTE_ST2 + LISTE_MIP)))

COLS_LOGS = ["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "Info_Sup"]
COLS_CONSIGNES = ["Type", "MSN", "Poste", "Emplacement", "Moteur"]
COLS_PANNES = ["Zone", "Nom"]
COLS_OBJ = ["Valeur"]

if "db_logs" not in st.session_state: st.session_state.db_logs = pd.DataFrame(columns=COLS_LOGS)
if "db_consignes" not in st.session_state: st.session_state.db_consignes = pd.DataFrame(columns=COLS_CONSIGNES)
if "db_pannes" not in st.session_state:
    data_defaut = [["GAUCHE", "🔧 Capot Gauche (ST1)"], ["GAUCHE", "🔧 PAF"], ["DROIT", "🔧 Capot Droit (ST2)"], ["GENERIC", "⚠️ SO3 - Pipes"]]
    st.session_state.db_pannes = pd.DataFrame(data_defaut, columns=COLS_PANNES)
if "db_objectif" not in st.session_state: st.session_state.db_objectif = pd.DataFrame([[35]], columns=COLS_OBJ)

def safe_read(key_name): return st.session_state[key_name]
def append_row(key_name, new_row_list, cols):
    df_new = pd.DataFrame([new_row_list], columns=cols)
    st.session_state[key_name] = pd.concat([st.session_state[key_name], df_new], ignore_index=True)
def overwrite_data(key_name, df_to_write): st.session_state[key_name] = df_to_write

df = safe_read("db_logs")
if not df.empty:
    df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Heure"], errors='coerce')
    df = df.dropna(subset=["DateTime"]) 
else: df["DateTime"] = pd.to_datetime([])

df_consignes = safe_read("db_consignes")
df_obj = safe_read("db_objectif")
VAL_OBJECTIF = int(df_obj.iloc[0]["Valeur"]) if not df_obj.empty else 35

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
    if se_name == "MAINTENANCE": return "Inconnu"
    if se_name[0].upper() == "S": return "Série"
    if se_name[0].upper() == "R": return "Rework"
    if se_name[0].upper() == "M": return "MIP"
    return "Autre"

def detecter_zone_automatique(poste_choisi, dataframe):
    if dataframe.empty: return "INCONNU"
    df_clean = dataframe[dataframe["Poste"] == poste_choisi].sort_values("DateTime")
    if df_clean.empty: return "INCONNU"
    logs_production = df_clean[~df_clean["Etape"].str.contains("INCIDENT|APPEL", na=False)]
    if logs_production.empty: return "INCONNU"
    derniere_etape = logs_production.iloc[-1]["Etape"]
    if derniere_etape in ["PHASE_PREP_MAT", "STATION_BRAS", "STATION_TRK1"]: return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2"]: return "DROIT"
    else: return "GENERIC"

def get_info_msn(msn_cherhe, df_logs):
    if df_logs.empty: return "⚪ À faire", "⚡ Premier Dispo"
    df_temp = df_logs.copy()
    df_temp["REF_CLEAN"] = df_temp["MSN_Display"].astype(str).str.replace("MSN-", "").str.strip().str.upper()
    target = str(msn_cherhe).replace("MSN-", "").strip().upper()
    logs_msn = df_temp[df_temp["REF_CLEAN"] == target]
    if logs_msn.empty: return "⚪ À faire", "⚡ Premier Dispo"
    last_log = logs_msn.sort_values("DateTime").iloc[-1]
    qui = last_log["Poste"]
    if last_log["Etape"] == "FIN": return "🟢 Fini", f"✅ Fait par {qui}"
    return "🟡 En cours", f"🛠️ Pris par {qui}"

def check_regleur_busy(dataframe):
    if dataframe.empty: return False, None
    last_states = dataframe.sort_values("DateTime").groupby("Poste").last()
    busy_posts = last_states[last_states["Etape"] == "INCIDENT_EN_COURS"]
    if not busy_posts.empty:
        return True, busy_posts.index[0] 
    return False, None

def calculer_kpi_production(dataframe):
    if dataframe.empty: return pd.DataFrame()
    df_clean = dataframe.sort_values('DateTime')
    cycles = []
    groupes = df_clean.groupby("SE_Unique")
    for se_unique, groupe in groupes:
        if "FIN" in groupe["Etape"].values:
            msn = groupe.iloc[0]["MSN_Display"]
            poste = groupe.iloc[-1]["Poste"]
            start_time = groupe["DateTime"].min()
            end_time = groupe[groupe["Etape"] == "FIN"]["DateTime"].max()
            duree = (end_time - start_time).total_seconds() / 60
            cycles.append({"Date": end_time.strftime("%d/%m"), "MSN": msn, "Type": analyser_type(se_unique), "Poste": poste, "Entrée": start_time.strftime("%H:%M"), "Sortie": end_time.strftime("%H:%M"), "Durée (min)": int(duree)})
    return pd.DataFrame(cycles)

def calculer_kpi_pannes(dataframe):
    if dataframe.empty: return pd.DataFrame()
    df_maint = dataframe[dataframe['Etape'].isin(['APPEL_REGLAGE', 'INCIDENT_EN_COURS', 'INCIDENT_FINI'])].sort_values('DateTime')
    rapports = []
    for poste in df_maint['Poste'].unique():
        logs_poste = df_maint[df_maint['Poste'] == poste].sort_values('DateTime')
        current_cycle = {}
        for index, row in logs_poste.iterrows():
            etape = row['Etape']
            msn_clean = str(row['MSN_Display']).replace("MSN-", "")
            if etape == 'APPEL_REGLAGE':
                current_cycle = {'Poste': poste, 'MSN': msn_clean, 'Cause': row['Info_Sup'], 'Heure_Appel': row['DateTime'], 'Heure_Debut': None}
            elif etape == 'INCIDENT_EN_COURS':
                if not current_cycle:
                    current_cycle = {'Poste': poste, 'MSN': msn_clean, 'Cause': row['Info_Sup'], 'Heure_Appel': row['DateTime'], 'Heure_Debut': row['DateTime']}
                else:
                    current_cycle['Heure_Debut'] = row['DateTime']
            elif etape == 'INCIDENT_FINI':
                if current_cycle and current_cycle.get('Heure_Debut'):
                    current_cycle['Heure_Fin'] = row['DateTime']
                    attente = (current_cycle['Heure_Debut'] - current_cycle['Heure_Appel']).total_seconds() / 60
                    reglage = (current_cycle['Heure_Fin'] - current_cycle['Heure_Debut']).total_seconds() / 60
                    rapports.append({"Date": current_cycle['Heure_Appel'].strftime("%d/%m"), "Heure": current_cycle['Heure_Appel'].strftime("%H:%M"), "Poste": poste, "MSN": current_cycle.get('MSN', '?'), "Cause": current_cycle['Cause'], "Attente (min)": int(attente), "Réglage (min)": int(reglage), "Total (min)": int(attente + reglage)})
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
                if last_action["Etape"] == "APPEL_REGLAGE":
                    poste_occupe = True; etat_appel = True
                    prev = df_poste[df_poste["Etape"] != "APPEL_REGLAGE"]
                    if not prev.empty:
                        last_real = prev.iloc[-1]
                        msn_en_cours = str(last_real["MSN_Display"]).replace("MSN-", "")
                        se_unique_en_cours = last_real["SE_Unique"]
                elif last_action["Etape"] == "INCIDENT_EN_COURS":
                    poste_occupe = True; msn_en_cours = "MAINTENANCE"
                elif last_action["Etape"] != "FIN":
                    poste_occupe = True
                    if last_action["SE_Unique"] == "MAINTENANCE":
                        logs_reels = df_poste[df_poste["SE_Unique"] != "MAINTENANCE"]
                        if not logs_reels.empty:
                            vrai_log = logs_reels.iloc[-1]
                            msn_en_cours = str(vrai_log["MSN_Display"]).replace("MSN-", "")
                            se_unique_en_cours = vrai_log["SE_Unique"]
                        else: msn_en_cours = "INCONNU"; se_unique_en_cours = "S-INCONNU"
                    else:
                        msn_en_cours = str(last_action["MSN_Display"]).replace("MSN-", "")
                        se_unique_en_cours = last_action["SE_Unique"]
                    
                    if se_unique_en_cours.startswith("R"): type_en_cours = "Rework"
                    elif se_unique_en_cours.startswith("M"): type_en_cours = "MIP"
                    else: type_en_cours = "Série"

        if poste_occupe:
            # INTELLIGENCE MOTEUR
            is_cfm = False
            if not df_consignes.empty:
                check_cons = df_consignes[df_consignes["MSN"] == msn_en_cours]
                if not check_cons.empty and "CFM" in check_cons.iloc[0].get("Moteur", ""): is_cfm = True
            if not is_cfm and not df.empty:
                logs_piece = df[df["SE_Unique"] == se_unique_en_cours]
                if not logs_piece.empty and logs_piece["Info_Sup"].str.contains("CFM", na=False).any(): is_cfm = True

            if etat_appel: st.error("🆘 APPEL LANCÉ !"); st.info("Attendez le régleur.")
            elif msn_en_cours == "MAINTENANCE": st.warning("🔧 Régleur en cours...")
            else:
                st.warning(f"⚠️ **EN COURS : MSN-{msn_en_cours}**")
                if is_cfm: st.caption("🔧 Moteur : CFM (Capots)")
                
                # --- APPEL RÉGLEUR AUTOMATISÉ ---
                with st.expander("🚨 APPEL RÉGLEUR"):
                    liste_choix = []
                    if type_en_cours == "MIP": st.caption("Liste : MIP"); liste_choix = LISTE_MIP
                    elif type_en_cours == "Rework": st.caption("Liste : Rework"); liste_choix = LISTE_FULL
                    else: # Série
                        zone_detectee = detecter_zone_automatique(sim_poste, df)
                        if zone_detectee == "GAUCHE": st.info("📍 Zone : **Station 1 (Bras/Trk1)**"); liste_choix = LISTE_ST1
                        elif zone_detectee == "DROIT": st.info("📍 Zone : **Station 2 (Trk2)**"); liste_choix = LISTE_ST2
                        else: st.info("📍 Zone : **Générique**"); liste_choix = LISTE_FULL
                    
                    raisons_appel = st.multiselect("Quels réglages ?", liste_choix)
                    num_mat = st.text_input("📝 N° MAT (Optionnel)", placeholder="Ex: MAT-1234")
                    
                    if st.button("📢 SONNER RÉGLEUR", type="primary", use_container_width=True):
                        if not raisons_appel: st.error("⚠️ Motif requis !")
                        else:
                            now = get_heure_fr()
                            str_raisons = " + ".join(raisons_appel)
                            if num_mat: str_raisons = f"[MAT:{num_mat}] {str_raisons}"
                            new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, se_unique_en_cours, f"MSN-{msn_en_cours}", "APPEL_REGLAGE", str_raisons]
                            append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                st.markdown("---")
                sim_msn = msn_en_cours; nom_se_complet = se_unique_en_cours
                
                # --- AFFICHAGE BOUTONS ---
                st.caption("1️⃣ PRÉPARATION")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("📄 Dossier", use_container_width=True):
                        now = get_heure_fr()
                        new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DOSSIER", ""]
                        append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                with c2:        
                    if st.button("⚙️ Matériel", use_container_width=True):
                        now = get_heure_fr()
                        new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_PREP_MAT", ""]
                        append_row("db_logs", new_data, COLS_LOGS); st.rerun()

                st.caption("2️⃣ MESURE")
                if type_en_cours == "Série":
                    c3, c4 = st.columns(2)
                    with c3:
                        if st.button("🔵 Bras", use_container_width=True):
                            now = get_heure_fr()
                            new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_BRAS", ""]
                            append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                    with c4:    
                        if st.button("🔵 Trk 1", use_container_width=True):
                            now = get_heure_fr()
                            new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK1", ""]
                            append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                    c5, c6 = st.columns(2)
                    with c5:
                        if st.button("🔵 Trk 2", use_container_width=True):
                            now = get_heure_fr()
                            new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK2", ""]
                            append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                    with c6:
                        if st.button("📝 Rapport", use_container_width=True):
                            now = get_heure_fr()
                            new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_RAPPORT", ""]
                            append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                else:
                    c_mip1, c_mip2 = st.columns(2)
                    with c_mip1:
                        if st.button("🔵 Station Tracker", use_container_width=True):
                             now = get_heure_fr()
                             new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRACKER", ""]
                             append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                    with c_mip2:
                        if st.button("📝 Rapport", use_container_width=True):
                            now = get_heure_fr()
                            new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_RAPPORT", ""]
                            append_row("db_logs", new_data, COLS_LOGS); st.rerun()

                st.caption("3️⃣ FINITION")
                derniere_etape_validee = last_action["Etape"]
                if is_cfm and type_en_cours == "Série" and derniere_etape_validee == "PHASE_RAPPORT":
                    if st.button("📢 Appel Régleur (Retrait Capots)", type="primary", use_container_width=True):
                        now = get_heure_fr()
                        new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, se_unique_en_cours, f"MSN-{msn_en_cours}", "APPEL_REGLAGE", "Retrait Capots CFM"]
                        append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                
                if st.button("🛠️ Démontage", use_container_width=True):
                    now = get_heure_fr()
                    new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DEMONTAGE", ""]
                    append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                    
                st.write("")
                if st.button("✅ LIBÉRER (FINI)", type="primary", use_container_width=True):
                    now = get_heure_fr()
                    # CORRECTION MAJEURE ICI : On force l'écriture du MSN
                    new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, se_unique_en_cours, f"MSN-{msn_en_cours}", "FIN", ""]
                    append_row("db_logs", new_data, COLS_LOGS); st.rerun()
        else:
            st.success("✅ Poste Libre")
            sim_type = st.radio("Type", ["Série", "Rework", "MIP"], horizontal=True)
            liste_msn_filtrée = []
            engine_detected = "PW" 
            
            if not df_consignes.empty:
                liste_msn_filtrée = df_consignes[df_consignes["Type"] == sim_type]["MSN"].unique().tolist()
                
                # --- FILTRE : ON RETIRE CE QUI EST DÉJÀ COMMENCÉ OU FINI ---
                already_started = []
                if not df.empty:
                    # Nettoyage pour comparaison propre
                    clean_logs = df["MSN_Display"].astype(str).str.replace("MSN-", "").str.strip().str.upper().tolist()
                    already_started = clean_logs
                
                # On ne garde que les MSNs qui NE SONT PAS dans les logs
                liste_msn_filtrée = [m for m in liste_msn_filtrée if str(m).strip().upper() not in already_started]
            
            if liste_msn_filtrée:
                st.markdown(f"👇 **Prendre dans la liste ({sim_type}) :**")
                selection_msn = st.selectbox("Sélection MSN", liste_msn_filtrée)
                sim_msn = selection_msn.replace("MSN-", "")
                row_consigne = df_consignes[df_consignes["MSN"] == selection_msn]
                if not row_consigne.empty and "Moteur" in row_consigne.columns:
                    val_moteur = row_consigne.iloc[0]["Moteur"]
                    if val_moteur in ["CFM", "PW"]: engine_detected = val_moteur
            else:
                if not df_consignes.empty: st.info(f"ℹ️ Aucune consigne {sim_type} disponible (Tout est fini ou en cours).")
                if sim_type == "Série": engine_detected = st.radio("Moteur ?", ["PW", "CFM"], horizontal=True)
                col_msn, col_rand = st.columns([3, 1])
                if "current_msn" not in st.session_state: st.session_state.current_msn = "MSN-001"
                if col_rand.button("🎲"): st.session_state.current_msn = f"MSN-{random.randint(100, 999)}"; st.rerun()
                sim_msn = col_msn.text_input("Saisie MSN", st.session_state.current_msn)

            msn_deja_pris = False; qui_a_le_msn = ""
            if not df.empty:
                # Vérification plus souple
                clean_target = str(sim_msn).strip().upper()
                df_temp = df.copy()
                df_temp["REF_CLEAN"] = df_temp["MSN_Display"].astype(str).str.replace("MSN-", "").str.strip().str.upper()
                df_msn_check = df_temp[df_temp["REF_CLEAN"] == clean_target].sort_values("DateTime")
                
                if not df_msn_check.empty:
                    last_check = df_msn_check.iloc[-1]
                    if last_check["Etape"] not in ["FIN", "INCIDENT_FINI"] and last_check["Poste"] != sim_poste: msn_deja_pris = True; qui_a_le_msn = last_check["Poste"]
            
            prefix = "S" if sim_type == "Série" else ("R" if sim_type == "Rework" else "M")
            nom_se_complet = f"{prefix}-SE-MSN-{sim_msn}"
            st.markdown("---")
            if msn_deja_pris: st.error(f"⛔ STOP ! {qui_a_le_msn} travaille déjà dessus !")
            else:
                if sim_type == "Série" and engine_detected == "CFM":
                    st.warning("⚠️ **CFM DETECTÉ** : Montage capots obligatoire !")
                    if st.button("📢 Appel Régleur (Montage Capots)", type="primary", use_container_width=True):
                        now = get_heure_fr()
                        new_data_start = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DOSSIER", "Démarrage CFM"]
                        append_row("db_logs", new_data_start, COLS_LOGS)
                        new_data_appel = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "APPEL_REGLAGE", "Montage Capots CFM"]
                        append_row("db_logs", new_data_appel, COLS_LOGS)
                        st.rerun()
                else:
                    if st.button("🟡 DÉMARRER (Setup)", use_container_width=True, type="primary"):
                        now = get_heure_fr()
                        new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DOSSIER", ""]
                        append_row("db_logs", new_data, COLS_LOGS); st.rerun()

    # 🔒 RÉGLEUR
    elif role == "Régleur":
        pwd = st.text_input("🔑 Code PIN Régleur", type="password")
        st.button("🔓 Se connecter", key="btn_regleur")
        if pwd == MOT_DE_PASSE_REGLEUR:
            st.success("Accès autorisé")
            
            # --- NOTIFICATION CENTER : APPELS EN COURS (TRIÉS) ---
            st.markdown("### 📋 Liste des Appels en Cours")
            appels_en_cours_exist = False
            if not df.empty:
                # 1. On prend le dernier état connu de chaque poste
                derniers_logs = df.sort_values("DateTime").groupby("Poste").last().reset_index()
                
                # 2. On ne garde que ceux qui sont en "APPEL_REGLAGE"
                appels = derniers_logs[derniers_logs["Etape"] == "APPEL_REGLAGE"]
                
                # 3. ON TRIE PAR DATE (Plus ancien en premier)
                appels = appels.sort_values("DateTime")
                
                if not appels.empty:
                    appels_en_cours_exist = True
                    # Compteur pour l'ordre de priorité
                    rank = 1
                    for index, row in appels.iterrows():
                        heure_appel = row['DateTime'].strftime("%H:%M")
                        st.markdown(f"""
                        <div class="appel-card">
                            <span style='font-size:1.2rem; font-weight:bold;'>#{rank}</span> 
                            <span style='font-weight:bold; margin-left:10px;'>{row['Poste']}</span> 
                            <span style='color:#666; font-size:0.9rem;'>({heure_appel})</span><br>
                            <span style='color:#333; font-weight:bold;'>{row['MSN_Display']}</span><br>
                            <span style='color:#DC2626; font-style:italic;'>⚠️ {row['Info_Sup']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        rank += 1
                else: st.info("✅ Aucun appel pour le moment.")
            else: st.info("✅ Aucun appel pour le moment.")
            
            st.markdown("---")
            st.markdown("### 🛠️ Gérer une intervention")
            sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
            
            etat_poste = "VIDE"; info_sup = ""; start_time_evt = None
            if not df.empty:
                df_p = df[df["Poste"] == sim_poste].sort_values("DateTime")
                if not df_p.empty:
                    last_evt = df_p.iloc[-1]; info_sup = str(last_evt.get("Info_Sup", ""))
                    start_time_evt = last_evt["DateTime"]
                    if last_evt["Etape"] == "APPEL_REGLAGE": etat_poste = "APPEL_EN_COURS"
                    elif last_evt["Etape"] == "INCIDENT_EN_COURS": etat_poste = "INTERVENTION_EN_COURS"
                    elif last_evt["Etape"] != "FIN": etat_poste = "EN_PROD"
            if etat_poste == "VIDE": st.warning(f"🚫 {sim_poste} est vide.")
            elif etat_poste == "APPEL_EN_COURS":
                
                is_busy, busy_where = check_regleur_busy(df)
                
                st.markdown(f"<h3 style='color:red'>🚨 APPEL : {info_sup}</h3>", unsafe_allow_html=True)
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.error(f"⏳ Attente depuis : {duree} min")
                
                if is_busy:
                    st.error(f"⛔ IMPOSSIBLE : Vous êtes déjà en intervention sur **{busy_where}**. Finissez d'abord là-bas !")
                else:
                    if st.button("✅ ACCEPTER & DÉMARRER", type="primary", use_container_width=True):
                        now = get_heure_fr()
                        new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", info_sup]
                        append_row("db_logs", new_data, COLS_LOGS); st.rerun()
                        
            elif etat_poste == "INTERVENTION_EN_COURS":
                st.info(f"🔧 En cours : {info_sup}")
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.warning(f"⏱️ Temps passé : {duree} min")
                if st.button("✅ FIN RÉGLAGE (Reprise)", type="primary", use_container_width=True):
                    now = get_heure_fr()
                    new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, "MAINTENANCE", "System", "INCIDENT_FINI", "Reprise"]
                    append_row("db_logs", new_data, COLS_LOGS); st.rerun()
            elif etat_poste == "EN_PROD":
                st.info("Arrêt manuel ?")
                causes_choisies = st.multiselect("Motif :", LISTE_FULL)
                num_mat_regleur = st.text_input("📝 N° MAT (Optionnel)", placeholder="Ex: MAT-1234")
                if st.button("🛑 DÉBUT RÉGLAGE"):
                    is_busy, busy_where = check_regleur_busy(df)
                    if is_busy:
                        st.error(f"⛔ IMPOSSIBLE : Vous êtes déjà en intervention sur **{busy_where}**.")
                    elif not causes_choisies: 
                        st.error("Motif obligatoire")
                    else:
                        now = get_heure_fr()
                        str_raisons = ' + '.join(causes_choisies)
                        if num_mat_regleur: str_raisons = f"[MAT:{num_mat_regleur}] {str_raisons}"
                        new_data = [now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", str_raisons]
                        append_row("db_logs", new_data, COLS_LOGS); st.rerun()
        elif pwd: st.error("⛔ Code Faux !")

    # CHEF D'ÉQUIPE
    elif role == "Chef d'Équipe":
        pwd = st.text_input("🔑 Code PIN Chef", type="password")
        st.button("🔓 Se connecter", key="btn_chef")
        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")
            acces_chef_ok = True 
            st.subheader("🎯 Objectif Semaine")
            val_actuelle = VAL_OBJECTIF
            nouveau_obj = st.number_input("Définir l'objectif :", value=val_actuelle, step=1)
            if st.button("💾 Valider Objectif"):
                df_new_obj = pd.DataFrame([[nouveau_obj]], columns=["Valeur"])
                overwrite_data("db_objectif", df_new_obj)
                st.success(f"Objectif passé à {nouveau_obj} !"); st.rerun()
            st.divider()
            sim_mode = st.checkbox("🔮 Activer Simulation", value=False)
            if sim_mode: nb_pieces_simu = st.number_input("Nb Pièces :", value=10)
            st.divider()
            if st.button("⚠️ RAZ Logs Production"): 
                overwrite_data("db_logs", pd.DataFrame(columns=COLS_LOGS)); st.rerun()
        elif pwd: st.error("⛔ Code Faux !")

    # RDZ
    elif role == "RDZ (Responsable)":
        pwd = st.text_input("🔑 Code PIN RDZ", type="password")
        st.button("🔓 Se connecter", key="btn_rdz")
        if pwd == MOT_DE_PASSE_CHEF: 
            st.success("Accès autorisé")
            st.subheader("📋 Consignes")
            with st.form("form_consigne"):
                c_type = st.selectbox("Type", ["Série", "Rework", "MIP"])
                c_moteur = "PW"
                if c_type == "Série": c_moteur = st.radio("Moteur", ["PW", "CFM"], horizontal=True)
                c_msn = st.text_input("Numéro MSN")
                c_loc = st.text_input("📍 Emplacement", placeholder="Ex: Étagère 4...")
                if st.form_submit_button("Ajouter"):
                    if not df_consignes.empty and f"MSN-{c_msn}" in df_consignes["MSN"].values: st.error(f"⚠️ {c_msn} existe déjà !")
                    elif c_msn and c_loc:
                        append_row("db_consignes", [c_type, f"MSN-{c_msn}", "Indifférent", c_loc, c_moteur], COLS_CONSIGNES)
                        st.success("Ajouté !"); st.rerun()
                    else: st.error("Infos manquantes !")
            st.divider()
            if not df_consignes.empty:
                df_consignes['Label'] = df_consignes['MSN'] + " (" + df_consignes['Type'] + " - " + df_consignes.get('Moteur', 'PW') + ")"
                to_delete = st.multiselect("Effacer :", df_consignes['Label'].unique())
                if st.button("Supprimer Sélection"):
                    df_new = df_consignes[~df_consignes['Label'].isin(to_delete)]
                    df_new = df_new.drop(columns=['Label'], errors='ignore')
                    overwrite_data("db_consignes", df_new)
                    st.success("Supprimé !"); st.rerun()
            if st.button("🔥 Tout effacer"): 
                 overwrite_data("db_consignes", pd.DataFrame(columns=COLS_CONSIGNES)); st.rerun()
        elif pwd: st.error("⛔ Code Faux !")

    st.divider()
    st.checkbox("🔓 Mode Admin", key="mode_admin")

# ==============================================================================
# 5. DASHBOARD
# ==============================================================================
debut_semaine = get_start_of_week()
nom_shift_actuel, shifts_ecoules = get_current_shift_info()
mapping_etapes = {"PHASE_DOSSIER": 10, "PHASE_PREP_MAT": 20, "STATION_BRAS": 35, "STATION_TRK1": 50, "STATION_TRK2": 70, "STATION_TRACKER": 50, "PHASE_RAPPORT": 85, "PHASE_DEMONTAGE": 95, "FIN": 100}

if not df.empty:
    df_week = df[df["DateTime"] >= debut_semaine].copy()
    if not df_week.empty:
        df_week["Type"] = df_week["SE_Unique"].apply(analyser_type)
        df_week["Progression"] = df_week["Etape"].map(mapping_etapes).fillna(0)
        df_prod_pure = df_week[~df_week["Etape"].str.contains("INCIDENT|APPEL")].copy()
        if not df_prod_pure.empty:
            etat_global = df_prod_pure.sort_values("DateTime").groupby("SE_Unique").last().reset_index()
            pieces_terminees = etat_global[etat_global["Progression"] >= 95]
            nb_realise = pieces_terminees[pieces_terminees["Type"] == "Série"].shape[0]
            nb_rework = pieces_terminees[pieces_terminees["Type"] == "Rework"].shape[0]
            nb_mip = pieces_terminees[pieces_terminees["Type"] == "MIP"].shape[0]
            last_actions_prod = df_prod_pure.sort_values("DateTime").groupby("Poste").last().reset_index()
        else:
            nb_realise = 0; nb_rework = 0; nb_mip = 0; last_actions_prod = pd.DataFrame()
        last_actions_absolute = df_week.sort_values("DateTime").groupby("Poste").last().reset_index()
    else:
        nb_realise = 0; nb_rework = 0; nb_mip = 0; last_actions_absolute = pd.DataFrame(); last_actions_prod = pd.DataFrame()
else:
    nb_realise = 0; nb_rework = 0; nb_mip = 0; last_actions_absolute = pd.DataFrame(); last_actions_prod = pd.DataFrame()

target = VAL_OBJECTIF
cadence_par_shift = target / 9.0 

if sim_mode:
    delta = nb_pieces_simu - (shifts_ecoules * cadence_par_shift)
    affichage_realise = nb_pieces_simu
    titre_mode = "🔮 SIMULATION"
    couleur_bandeau = "#9b59b6"
else:
    delta = nb_realise - (shifts_ecoules * cadence_par_shift)
    affichage_realise = nb_realise
    titre_mode = f"📍 PILOTAGE LIVE | {nom_shift_actuel}"
    couleur_bandeau = "#2ecc71" if delta >= 0 else "#e74c3c"

now = get_heure_fr() 
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
                if txt_statut == "🟢 Fini":
                    opacity = "0.6" # Transparent mais lisible
                    border_color = "#2ecc71" # Vert
                    text_deco = "text-decoration: line-through;" # Barré
                elif txt_statut == "🟡 En cours":
                    opacity = "1.0"
                    border_color = "#f1c40f" # Jaune
                    text_deco = ""
                else: # À faire
                    opacity = "1.0"
                    border_color = couleur_bordure # Couleur normale du type
                    text_deco = ""

                moteur_info = ""
                if type_col == "Série" and "Moteur" in row: moteur_info = f" | 🔧 {row['Moteur']}"
                
                st.markdown(f"""
                <div class="prio-card" style="border-left: 6px solid {border_color}; opacity: {opacity};">
                    <div style="display:flex; justify-content:space-between;">
                        <span class="prio-rank">#{rank}</span>
                        <span class="prio-msn" style="{text_deco}">{row['MSN']}</span>
                    </div>
                    <div class="prio-loc">📍 {row.get('Emplacement', 'Non précisé')}{moteur_info}</div>
                    <div class="prio-info">{txt_statut} | {txt_qui}</div>
                </div>
                """, unsafe_allow_html=True)
                rank += 1
        else: st.caption("Aucune consigne.")
    with col_serie: st.markdown("### 🟦 SÉRIE"); afficher_colonne_prio("Série", "#0068C9")
    with col_mip: st.markdown("### 🟧 MIP"); afficher_colonne_prio("MIP", "#FCA510")
    with col_rework: st.markdown("### 🟥 REWORK"); afficher_colonne_prio("Rework", "#FF4B4B")

st.divider()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🎯 Objectif", target)
k2.metric("📊 Réalisé", affichage_realise)
k3.metric("🔴 Reworks", nb_rework)
k4.metric("🟠 MIPs", nb_mip)
k5.metric("🕒 Heure", now.strftime("%H:%M"))

st.subheader("📡 État des Postes (Live)")
cols = st.columns(3)
TEMPS_RESTANT = { "PHASE_DOSSIER": 260, "PHASE_PREP_MAT": 245, "STATION_BRAS": 210, "STATION_TRK1": 175, "STATION_TRK2": 85, "STATION_TRACKER": 120, "PHASE_RAPPORT": 45, "PHASE_DEMONTAGE": 25, "FIN": 0 }

for i, p in enumerate(["Poste_01", "Poste_02", "Poste_03"]):
    info_abs = last_actions_absolute[last_actions_absolute["Poste"] == p] if not last_actions_absolute.empty else pd.DataFrame()
    info_prod = last_actions_prod[last_actions_prod["Poste"] == p] if not last_actions_prod.empty else pd.DataFrame()
    with cols[i]:
        with st.container(border=True):
            if not info_abs.empty and info_abs.iloc[0]['Etape'] == "APPEL_REGLAGE":
                row_abs = info_abs.iloc[0]; msn_display = row_abs["MSN_Display"]
                st.markdown(f"<div class='blink-red'>🚨 APPEL RÉGLEUR EN COURS</div>", unsafe_allow_html=True)
                st.markdown(f"### ⚠️ {p}"); st.markdown(f"## **{msn_display}**"); 
                st.error(f"Motif : {row_abs.get('Info_Sup', 'Inconnu')}")
                duree = int((now - row_abs['DateTime']).total_seconds() / 60)
                st.markdown(f"⏳ Attente Régleur : **{duree} min**")
            elif not info_abs.empty and info_abs.iloc[0]['Etape'] == "INCIDENT_EN_COURS":
                row_abs = info_abs.iloc[0]; msn_display = "MAINTENANCE"
                if not info_prod.empty: msn_display = info_prod.iloc[0]['MSN_Display']
                st.markdown(f"### 🟠 {p}"); st.markdown(f"## **{msn_display}**"); st.warning(f"🔧 {row_abs.get('Info_Sup', '')}")
                duree = int((now - row_abs['DateTime']).total_seconds() / 60)
                st.markdown(f"🔧 Temps de Réglage : **{duree} min**")
            elif not info_prod.empty:
                row_prod = info_prod.iloc[0]
                if row_prod.get('Progression', 0) < 100:
                    icon = "🟨" if row_prod['Etape'] in ["PHASE_DOSSIER", "PHASE_PREP_MAT"] else ("🟪" if row_prod['Etape'] in ["PHASE_DEMONTAGE", "PHASE_RAPPORT"] else "🟦")
                    if row_prod['Type'] == "Rework": icon = "🟥"
                    st.markdown(f"### {icon} {p}"); st.markdown(f"## **{row_prod['MSN_Display']}**"); st.progress(int(row_prod.get('Progression', 0)))
                    reste = TEMPS_RESTANT.get(row_prod['Etape'], 30)
                    sortie = now + timedelta(minutes=reste)
                    if reste >= 60: str_duree = f"{reste // 60}h{reste % 60:02d}"
                    else: str_duree = f"{reste} min"
                    st.caption(f"📍 {row_prod['Etape']}"); st.markdown(f"⏳ Reste : **{str_duree}**"); st.markdown(f"🏁 Sortie : **{sortie.strftime('%H:%M')}**")
                else: st.markdown(f"### 🟦 {p}"); st.success("✅ Poste Libre")
            else: st.markdown(f"### ⬜ {p}"); st.info("En attente")

if acces_chef_ok:
    st.divider()
    st.markdown("---")
    st.subheader("📊 ANALYSE PERFORMANCE (Accès Chef)")
    tab1, tab2 = st.tabs(["🔧 Pannes & Réglages", "⏱️ Temps de Cycle Production"])
    with tab1:
        if not df.empty:
            df_kpi = calculer_kpi_pannes(df)
            if not df_kpi.empty:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("🔢 Nb Pannes", len(df_kpi))
                k2.metric("⏳ Total Attente", f"{int(df_kpi['Attente (min)'].sum())} min")
                k3.metric("🔧 Total Réglage", f"{int(df_kpi['Réglage (min)'].sum())} min")
                k4.metric("🛑 Temps Perdu Total", f"{int(df_kpi['Total (min)'].sum())} min")
                st.markdown("#### 📜 Historique Pannes :")
                st.dataframe(df_kpi, use_container_width=True, hide_index=True)
            else: st.info("Aucune panne terminée pour l'instant.")
        else: st.info("Pas encore de données.")
    with tab2:
        if not df.empty:
            df_prod = calculer_kpi_production(df)
            if not df_prod.empty:
                avg_cycle = int(df_prod["Durée (min)"].mean())
                st.metric("⏱️ Temps de Cycle Moyen", f"{avg_cycle} min")
                st.markdown("#### 📜 Historique Production :")
                st.dataframe(df_prod, use_container_width=True, hide_index=True)
            else: st.info("Aucune pièce terminée (LIBÉRÉE).")
        else: st.info("Pas encore de données.")
