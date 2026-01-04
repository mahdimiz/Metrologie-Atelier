import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

import pandas as pd
from datetime import datetime, timedelta, time
import random

# ==============================================================================
# 1) CONFIG
# ==============================================================================
st.set_page_config(page_title="Suivi V78 Cloud", layout="wide", page_icon="☁️")

MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

conn = st.connection("gsheets", type=GSheetsConnection)

def get_heure_fr():
    # UTC+1 fixe (si tu veux DST auto France, je te le mets après)
    return datetime.utcnow() + timedelta(hours=1)

if "mode_admin" not in st.session_state:
    st.session_state.mode_admin = False

# ==============================================================================
# 2) CSS
# ==============================================================================
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
    st.markdown("""<style>header, footer, .stDeployButton {display:none;} .block-container{padding-top:1rem;}</style>""",
                unsafe_allow_html=True)

# ==============================================================================
# 3) FONCTIONS READ/WRITE (optimisées quota)
# ==============================================================================
def safe_read(worksheet, cols, ttl):
    """Lecture avec TTL (réduit fortement les read requests)."""
    try:
        df = conn.read(worksheet=worksheet, ttl=ttl)
        if df is None or df.empty or len(df.columns) < len(cols):
            return pd.DataFrame(columns=cols)
        df = df[df.columns[:len(cols)]].copy()
        df.columns = cols
        return df
    except Exception:
        return pd.DataFrame(columns=cols)

def overwrite_data(worksheet, df_to_write):
    try:
        conn.update(worksheet=worksheet, data=df_to_write)
    except Exception as e:
        st.error(f"Erreur Mise à jour Cloud : {e}")

# ✅ Logs: write sans relire = 0 READ par clic (juste 1 WRITE)
COLS_LOGS = ["Date", "Heure", "Poste", "SE_Unique", "MSN_Display", "Etape", "Info_Sup"]
def append_log_row(new_row_list):
    try:
        df_old = st.session_state.get("Logs_cache", pd.DataFrame(columns=COLS_LOGS))
        df_new = pd.DataFrame([new_row_list], columns=COLS_LOGS)
        df_final = pd.concat([df_old, df_new], ignore_index=True)
        conn.update(worksheet="Logs", data=df_final)        # 1 WRITE
        st.session_state["Logs_cache"] = df_final          # maj cache local
    except Exception as e:
        st.error(f"Erreur Sauvegarde Cloud : {e}")

def append_row_generic(worksheet, new_row_list, cols, ttl_cache=300):
    """
    Pour Pannes/Consignes (rarement modifiés):
    - on utilise un cache session pour éviter read + read.
    """
    try:
        key = f"cache_{worksheet}"
        if key not in st.session_state:
            st.session_state[key] = safe_read(worksheet, cols, ttl=ttl_cache)

        df_old = st.session_state[key]
        df_new = pd.DataFrame([new_row_list], columns=cols)
        df_final = pd.concat([df_old, df_new], ignore_index=True)
        conn.update(worksheet=worksheet, data=df_final)
        st.session_state[key] = df_final
    except Exception as e:
        st.error(f"Erreur Sauvegarde Cloud : {e}")

# ==============================================================================
# 4) HELPERS CALCUL
# ==============================================================================
def get_start_of_week():
    now = get_heure_fr()
    today_weekday = now.weekday()
    monday_six_thirty = now.replace(hour=6, minute=30, second=0, microsecond=0) - timedelta(days=today_weekday)
    if today_weekday == 0 and now.time() < time(6, 30):
        monday_six_thirty -= timedelta(days=7)
    return monday_six_thirty

def get_current_shift_info():
    now = get_heure_fr()
    day = now.weekday()
    t = now.time()
    nom_shift = "💤 Hors Shift"
    shifts_passes = 0.0
    if day < 4:
        shifts_passes = day * 2
    elif day == 4:
        shifts_passes = 8
    else:
        shifts_passes = 9

    if day < 4:
        if time(6,30) <= t < time(14,50):
            nom_shift, shifts_passes = "🌅 Shift Matin", shifts_passes + 0.5
        elif time(14,50) <= t or t <= time(0,9):
            nom_shift, shifts_passes = "🌙 Shift Soir", shifts_passes + 1.5
        else:
            shifts_passes += 2.0
    elif day == 4:
        if time(6,30) <= t < time(15,50):
            nom_shift, shifts_passes = "🌅 Shift Matin (Vendredi)", shifts_passes + 0.5
        else:
            shifts_passes += 1.0
    return nom_shift, min(shifts_passes, 9.0)

def analyser_type(se_name):
    if not isinstance(se_name, str) or len(se_name) < 1: return "Inconnu"
    if se_name[0].upper() == "S": return "Série"
    if se_name[0].upper() == "R": return "Rework"
    if se_name[0].upper() == "M": return "MIP"
    return "Autre"

def deviner_contexte_poste(poste_choisi, dataframe):
    if dataframe.empty: return "Inconnu"
    df_clean = dataframe[~dataframe["Etape"].astype(str).str.contains("INCIDENT|APPEL", na=False)]
    actions_poste = df_clean[df_clean["Poste"] == poste_choisi].sort_values("DateTime")
    if actions_poste.empty: return "Inconnu"
    derniere_etape = actions_poste.iloc[-1]["Etape"]
    if derniere_etape in ["PHASE_SETUP", "STATION_BRAS", "STATION_TRK1"]: return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2", "PHASE_RAPPORT"]: return "DROIT"
    else: return "GENERIC"

def get_info_msn(msn_cherche, df_logs):
    if df_logs.empty: return "⚪ À faire", "⚡ Premier Dispo"
    logs_msn = df_logs[df_logs["MSN_Display"].astype(str).str.contains(str(msn_cherche), na=False)]
    if logs_msn.empty: return "⚪ À faire", "⚡ Premier Dispo"
    last_log = logs_msn.sort_values("DateTime").iloc[-1]
    qui = last_log["Poste"]
    if last_log["Etape"] == "FIN": return "🟢 Fini", f"✅ Fait par {qui}"
    return "🟡 En cours", f"🛠️ Pris par {qui}"

def calculer_kpi_pannes(df_logs):
    if df_logs.empty:
        return pd.DataFrame()
    df_maint = df_logs[df_logs["Etape"].isin(["APPEL_REGLAGE", "INCIDENT_EN_COURS", "INCIDENT_FINI"])].sort_values("DateTime")
    rapports = []
    for poste in df_maint["Poste"].unique():
        logs_poste = df_maint[df_maint["Poste"] == poste].sort_values("DateTime")
        current = {}
        for _, row in logs_poste.iterrows():
            etape = row["Etape"]
            msn_brut = str(row["MSN_Display"])
            msn_clean = msn_brut.replace("MSN-", "") if "MSN-" in msn_brut else msn_brut

            if etape == "APPEL_REGLAGE":
                current = {
                    "Poste": poste,
                    "MSN": msn_clean,
                    "Cause": row.get("Info_Sup", ""),
                    "Heure_Appel": row["DateTime"],
                    "Heure_Debut": None,
                    "Heure_Fin": None,
                }
            elif etape == "INCIDENT_EN_COURS":
                if not current:
                    current = {
                        "Poste": poste,
                        "MSN": msn_clean,
                        "Cause": row.get("Info_Sup", ""),
                        "Heure_Appel": row["DateTime"],
                        "Heure_Debut": row["DateTime"],
                        "Heure_Fin": None,
                    }
                else:
                    current["Heure_Debut"] = row["DateTime"]
            elif etape == "INCIDENT_FINI":
                if current and current.get("Heure_Debut") is not None:
                    current["Heure_Fin"] = row["DateTime"]
                    attente = (current["Heure_Debut"] - current["Heure_Appel"]).total_seconds() / 60
                    reglage = (current["Heure_Fin"] - current["Heure_Debut"]).total_seconds() / 60
                    rapports.append({
                        "Date": current["Heure_Appel"].strftime("%d/%m"),
                        "Heure": current["Heure_Appel"].strftime("%H:%M"),
                        "Poste": poste,
                        "MSN": current.get("MSN", "?"),
                        "Cause": current.get("Cause", ""),
                        "Attente (min)": int(attente),
                        "Réglage (min)": int(reglage),
                        "Total (min)": int(attente + reglage),
                    })
                    current = {}
    return pd.DataFrame(rapports)

# ==============================================================================
# 5) LECTURES (TTL optimisés pour 8 users)
# ==============================================================================
nom_shift_actuel, shifts_ecoules = get_current_shift_info()

# ✅ Refresh adaptatif: Hors shift = 5min ; en shift = 30s
refresh_ms = 300_000 if "Hors Shift" in nom_shift_actuel else 30_000
st_autorefresh(interval=refresh_ms, key="refresh_adapt")

# TTL optimisés
df_logs = safe_read("Logs", COLS_LOGS, ttl=20)
if not df_logs.empty:
    df_logs["DateTime"] = pd.to_datetime(df_logs["Date"].astype(str) + " " + df_logs["Heure"].astype(str), errors="coerce")
    df_logs = df_logs.dropna(subset=["DateTime"])
else:
    df_logs["DateTime"] = pd.to_datetime([])

# Cache local pour écriture sans relire
st.session_state["Logs_cache"] = df_logs.copy()

COLS_CONSIGNES = ["Type", "MSN", "Poste", "Emplacement"]
df_consignes = safe_read("Consignes", COLS_CONSIGNES, ttl=120)

COLS_PANNES = ["Zone", "Nom"]
df_pannes = safe_read("Pannes", COLS_PANNES, ttl=600)
if df_pannes.empty:
    df_pannes = pd.DataFrame([
        ["GAUCHE", "🔧 Capot Gauche (ST1)"],
        ["GAUCHE", "🔧 PAF"],
        ["DROIT", "🔧 Capot Droit (ST2)"],
        ["GENERIC", "⚠️ SO3 - Pipes"],
    ], columns=COLS_PANNES)
    overwrite_data("Pannes", df_pannes)

COLS_OBJ = ["Valeur"]
df_obj = safe_read("Objectif", COLS_OBJ, ttl=600)
VAL_OBJECTIF = int(df_obj.iloc[0]["Valeur"]) if not df_obj.empty else 35

def get_liste_pannes(zone):
    if df_pannes.empty: return []
    return df_pannes[df_pannes["Zone"] == zone]["Nom"].tolist()

REGLAGES_GAUCHE = get_liste_pannes("GAUCHE")
REGLAGES_DROIT = get_liste_pannes("DROIT")
REGLAGES_GENERIC = get_liste_pannes("GENERIC")

# ==============================================================================
# 6) SIDEBAR
# ==============================================================================
sim_mode = False
nb_pieces_simu = 0
acces_chef_ok = False

with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
    st.divider()

    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe", "RDZ (Responsable)"])
    st.divider()

    # ---------------- OPÉRATEUR ----------------
    if role == "Opérateur":
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
        st.subheader("🔨 Production")

        poste_occupe = False
        msn_en_cours = ""
        se_unique_en_cours = ""
        etat_appel = False

        if not df_logs.empty:
            df_poste = df_logs[df_logs["Poste"] == sim_poste].sort_values("DateTime")
            if not df_poste.empty:
                last_action = df_poste.iloc[-1]
                if last_action["Etape"] == "APPEL_REGLAGE":
                    poste_occupe = True
                    etat_appel = True
                    prev = df_poste[df_poste["Etape"] != "APPEL_REGLAGE"]
                    if not prev.empty:
                        last_real = prev.iloc[-1]
                        msn_en_cours = str(last_real["MSN_Display"]).replace("MSN-", "")
                        se_unique_en_cours = last_real["SE_Unique"]
                elif last_action["Etape"] == "INCIDENT_EN_COURS":
                    poste_occupe = True
                    msn_en_cours = "MAINTENANCE"
                elif last_action["Etape"] != "FIN":
                    poste_occupe = True
                    msn_en_cours = str(last_action["MSN_Display"]).replace("MSN-", "")
                    se_unique_en_cours = last_action["SE_Unique"]

        if poste_occupe:
            if etat_appel:
                st.error("🆘 APPEL LANCÉ !")
                st.info("Attendez le régleur.")
            elif msn_en_cours == "MAINTENANCE":
                st.warning("🔧 Régleur en cours...")
            else:
                st.warning(f"⚠️ **EN COURS : MSN-{msn_en_cours}**")

                with st.expander("🚨 APPEL RÉGLEUR"):
                    contexte = deviner_contexte_poste(sim_poste, df_logs)
                    if contexte == "GAUCHE":
                        liste_pannes = REGLAGES_GAUCHE + REGLAGES_GENERIC
                    elif contexte == "DROIT":
                        liste_pannes = REGLAGES_DROIT + REGLAGES_GENERIC
                    else:
                        liste_pannes = REGLAGES_GAUCHE + REGLAGES_DROIT + REGLAGES_GENERIC

                    raisons_appel = st.multiselect("Quels réglages ?", liste_pannes)
                    num_mat = st.text_input("📝 N° MAT / Outillage (Optionnel)", placeholder="Ex: MAT-1234")

                    if st.button("📢 SONNER RÉGLEUR", type="primary"):
                        if not raisons_appel:
                            st.error("⚠️ Choisissez au moins un problème !")
                        else:
                            now_ = get_heure_fr()
                            str_raisons = " + ".join(raisons_appel)
                            if num_mat:
                                str_raisons = f"[MAT:{num_mat}] {str_raisons}"
                            new_data = [
                                now_.strftime("%Y-%m-%d"),
                                now_.strftime("%H:%M:%S"),
                                sim_poste,
                                se_unique_en_cours,
                                f"MSN-{msn_en_cours}",
                                "APPEL_REGLAGE",
                                str_raisons,
                            ]
                            append_log_row(new_data)
                            st.rerun()

                st.markdown("---")
                sim_msn = msn_en_cours
                nom_se_complet = se_unique_en_cours
                c1, c2 = st.columns(2)

                if c1.button("🔵 Bras"):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_BRAS", ""])
                    st.rerun()

                if c2.button("🔵 Trk 1"):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK1", ""])
                    st.rerun()

                if st.button("🔵 Track 2", use_container_width=True):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK2", ""])
                    st.rerun()

                if st.button("🟣 Fin / Démont.", use_container_width=True):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DESETUP", ""])
                    st.rerun()

                if st.button("✅ LIBÉRER (FINI)", type="primary", use_container_width=True):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, "Aucun", "Aucun", "FIN", ""])
                    st.rerun()

        else:
            st.success("✅ Poste Libre")
            sim_type = st.radio("Type", ["Série", "Rework", "MIP"], horizontal=True)

            if not df_consignes.empty:
                liste_msn = df_consignes["MSN"].unique().tolist()
                st.markdown("👇 **Prendre dans la liste :**")
                selection_msn = st.selectbox("Sélection MSN", liste_msn)
                sim_msn = selection_msn.replace("MSN-", "")
            else:
                col_msn, col_rand = st.columns([3, 1])
                if "current_msn" not in st.session_state:
                    st.session_state.current_msn = "MSN-001"
                if col_rand.button("🎲"):
                    st.session_state.current_msn = f"MSN-{random.randint(100, 999)}"
                    st.rerun()
                st.warning("⚠️ Aucune consigne, saisie manuelle.")
                sim_msn = col_msn.text_input("Saisie MSN", st.session_state.current_msn)

            msn_deja_pris = False
            qui_a_le_msn = ""
            if not df_logs.empty:
                df_msn_check = df_logs[df_logs["MSN_Display"] == f"MSN-{sim_msn}"].sort_values("DateTime")
                if not df_msn_check.empty:
                    last_check = df_msn_check.iloc[-1]
                    if last_check["Etape"] not in ["FIN", "INCIDENT_FINI"] and last_check["Poste"] != sim_poste:
                        msn_deja_pris = True
                        qui_a_le_msn = last_check["Poste"]

            prefix = "S" if sim_type == "Série" else ("R" if sim_type == "Rework" else "M")
            nom_se_complet = f"{prefix}-SE-MSN-{sim_msn}"

            st.markdown("---")
            if msn_deja_pris:
                st.error(f"⛔ STOP ! {qui_a_le_msn} travaille déjà dessus !")
            else:
                if st.button("🟡 DÉMARRER (Setup)", use_container_width=True, type="primary"):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_SETUP", ""])
                    st.rerun()

    # ---------------- RÉGLEUR ----------------
    elif role == "Régleur":
        pwd = st.text_input("🔑 Code PIN Régleur", type="password")
        st.button("🔓 Se connecter", key="btn_regleur")

        if pwd == MOT_DE_PASSE_REGLEUR:
            st.success("Accès autorisé")
            sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
            st.subheader("🔧 Intervention")

            etat_poste = "VIDE"
            info_sup = ""
            start_time_evt = None

            if not df_logs.empty:
                df_p = df_logs[df_logs["Poste"] == sim_poste].sort_values("DateTime")
                if not df_p.empty:
                    last_evt = df_p.iloc[-1]
                    info_sup = str(last_evt.get("Info_Sup", ""))
                    start_time_evt = last_evt["DateTime"]
                    if last_evt["Etape"] == "APPEL_REGLAGE":
                        etat_poste = "APPEL_EN_COURS"
                    elif last_evt["Etape"] == "INCIDENT_EN_COURS":
                        etat_poste = "INTERVENTION_EN_COURS"
                    elif last_evt["Etape"] != "FIN":
                        etat_poste = "EN_PROD"

            if etat_poste == "VIDE":
                st.warning(f"🚫 {sim_poste} est vide.")
            elif etat_poste == "APPEL_EN_COURS":
                st.markdown(f"<h3 style='color:red'>🚨 APPEL : {info_sup}</h3>", unsafe_allow_html=True)
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.error(f"⏳ Attente depuis : {duree} min")

                if st.button("✅ ACCEPTER & DÉMARRER", type="primary", use_container_width=True):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", info_sup])
                    st.rerun()

            elif etat_poste == "INTERVENTION_EN_COURS":
                st.info(f"🔧 En cours : {info_sup}")
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.warning(f"⏱️ Temps passé : {duree} min")

                if st.button("✅ FIN RÉGLAGE (Reprise)", type="primary", use_container_width=True):
                    now_ = get_heure_fr()
                    append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, "MAINTENANCE", "System", "INCIDENT_FINI", "Reprise"])
                    st.rerun()

            elif etat_poste == "EN_PROD":
                st.info("Arrêt manuel ?")
                liste_complete = REGLAGES_GAUCHE + REGLAGES_DROIT + REGLAGES_GENERIC
                causes_choisies = st.multiselect("Motif :", liste_complete)
                num_mat_regleur = st.text_input("📝 N° MAT (Optionnel)", placeholder="Ex: MAT-1234")

                if st.button("🛑 DÉBUT RÉGLAGE"):
                    if not causes_choisies:
                        st.error("Motif obligatoire")
                    else:
                        now_ = get_heure_fr()
                        str_raisons = " + ".join(causes_choisies)
                        if num_mat_regleur:
                            str_raisons = f"[MAT:{num_mat_regleur}] {str_raisons}"
                        append_log_row([now_.strftime("%Y-%m-%d"), now_.strftime("%H:%M:%S"), sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", str_raisons])
                        st.rerun()
        elif pwd:
            st.error("⛔ Code Faux !")

    # ---------------- CHEF ----------------
    elif role == "Chef d'Équipe":
        pwd = st.text_input("🔑 Code PIN Chef", type="password")
        st.button("🔓 Se connecter", key="btn_chef")

        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")
            acces_chef_ok = True

            st.subheader("🎯 Objectif Semaine")
            nouveau_obj = st.number_input("Définir l'objectif :", value=int(VAL_OBJECTIF), step=1)
            if st.button("💾 Valider Objectif"):
                overwrite_data("Objectif", pd.DataFrame([[nouveau_obj]], columns=["Valeur"]))
                st.success(f"Objectif passé à {nouveau_obj} !")
                st.rerun()

            st.divider()

            with st.expander("⚙️ Gérer la liste des Pannes"):
                new_panne = st.text_input("Nouvelle Panne")
                new_zone = st.selectbox("Zone", ["GAUCHE", "DROIT", "GENERIC"])
                if st.button("Ajouter à la liste"):
                    append_row_generic("Pannes", [new_zone, new_panne], COLS_PANNES, ttl_cache=600)
                    st.success("Ajouté !")
                    st.rerun()

            st.divider()
            sim_mode = st.checkbox("🔮 Activer Simulation", value=False)
            if sim_mode:
                nb_pieces_simu = st.number_input("Nb Pièces :", value=10, step=1)

            st.divider()
            if st.button("⚠️ RAZ Logs Production"):
                overwrite_data("Logs", pd.DataFrame(columns=COLS_LOGS))
                st.success("Logs vidés.")
                st.rerun()
        elif pwd:
            st.error("⛔ Code Faux !")

    # ---------------- RDZ ----------------
    elif role == "RDZ (Responsable)":
        pwd = st.text_input("🔑 Code PIN RDZ", type="password")
        st.button("🔓 Se connecter", key="btn_rdz")
        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")
            st.subheader("📋 Consignes")

            with st.form("form_consigne"):
                c_type = st.selectbox("Type", ["Série", "Rework", "MIP"])
                c_msn = st.text_input("Numéro MSN")
                c_loc = st.text_input("📍 Emplacement", placeholder="Ex: Étagère 4...")

                if st.form_submit_button("Ajouter"):
                    if c_msn and c_loc:
                        append_row_generic("Consignes", [c_type, f"MSN-{c_msn}", "Indifférent", c_loc], COLS_CONSIGNES, ttl_cache=300)
                        st.success("Ajouté !")
                        st.rerun()
                    else:
                        st.error("Infos manquantes !")
        elif pwd:
            st.error("⛔ Code Faux !")

    st.divider()
    st.checkbox("🔓 Mode Admin", key="mode_admin")

# ==============================================================================
# 7) DASHBOARD
# ==============================================================================
debut_semaine = get_start_of_week()
mapping_etapes = {
    "PHASE_SETUP": 5,
    "STATION_BRAS": 15,
    "STATION_TRK1": 30,
    "STATION_TRK2": 65,
    "PHASE_RAPPORT": 90,
    "PHASE_DESETUP": 95,
    "FIN": 100,
}

if not df_logs.empty:
    df_week = df_logs[df_logs["DateTime"] >= debut_semaine].copy()
    if not df_week.empty:
        df_week["Type"] = df_week["SE_Unique"].apply(analyser_type)
        df_week["Progression"] = df_week["Etape"].map(mapping_etapes).fillna(0)

        df_prod_pure = df_week[~df_week["Etape"].astype(str).str.contains("INCIDENT|APPEL", na=False)].copy()
        if not df_prod_pure.empty:
            etat_global = df_prod_pure.sort_values("DateTime").groupby("SE_Unique").last().reset_index()
            pieces_terminees = etat_global[etat_global["Progression"] >= 95]
            nb_realise = pieces_terminees[pieces_terminees["Type"] == "Série"].shape[0]
            nb_rework = pieces_terminees[pieces_terminees["Type"] == "Rework"].shape[0]
            nb_mip = pieces_terminees[pieces_terminees["Type"] == "MIP"].shape[0]
            last_actions_prod = df_prod_pure.sort_values("DateTime").groupby("Poste").last().reset_index()
        else:
            nb_realise = nb_rework = nb_mip = 0
            last_actions_prod = pd.DataFrame()

        last_actions_absolute = df_week.sort_values("DateTime").groupby("Poste").last().reset_index()
    else:
        nb_realise = nb_rework = nb_mip = 0
        last_actions_prod = pd.DataFrame()
        last_actions_absolute = pd.DataFrame()
else:
    nb_realise = nb_rework = nb_mip = 0
    last_actions_prod = pd.DataFrame()
    last_actions_absolute = pd.DataFrame()

target = int(VAL_OBJECTIF)
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
msg = f"Avec {int(nb_pieces_simu)} pièces MAINTENANT 👉 DELTA : {delta:+.1f}" if sim_mode else (f"🚀 AVANCE : {delta:+.1f}" if delta >= 0 else f"🐢 RETARD : {delta:+.1f}")
st.markdown(f"<div style='padding:10px;border-radius:5px;background-color:{couleur_bandeau};color:white;text-align:center;font-weight:bold;'>{msg}</div>",
            unsafe_allow_html=True)

if not sim_mode:
    st.write("")
    st.subheader("📋 ORDRE DE PASSAGE & EMPLACEMENTS")
    col_serie, col_mip, col_rework = st.columns(3)

    def afficher_colonne_prio(type_col, couleur_bordure):
        if not df_consignes.empty:
            items = df_consignes[df_consignes["Type"] == type_col]
            rank = 1
            for _, row in items.iterrows():
                txt_statut, txt_qui = get_info_msn(row["MSN"], df_logs)
                opacity = "0.4" if txt_statut == "🟢 Fini" else ("1.0; border: 2px solid #f1c40f" if txt_statut == "🟡 En cours" else "1.0")
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
        else:
            st.caption("Aucune consigne.")

    with col_serie:
        st.markdown("### 🟦 SÉRIE")
        afficher_colonne_prio("Série", "#3498db")
    with col_mip:
        st.markdown("### 🟧 MIP")
        afficher_colonne_prio("MIP", "#e67e22")
    with col_rework:
        st.markdown("### 🟥 REWORK")
        afficher_colonne_prio("Rework", "#c0392b")

st.divider()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🎯 Objectif", target)
k2.metric("📊 Réalisé", affichage_realise)
k3.metric("🔴 Reworks", nb_rework)
k4.metric("🟠 MIPs", nb_mip)
k5.metric("🕒 Heure", now.strftime("%H:%M"))

st.subheader("📡 État des Postes (Live)")
cols = st.columns(3)
TEMPS_RESTANT = {"PHASE_SETUP": 245, "STATION_BRAS": 210, "STATION_TRK1": 175, "STATION_TRK2": 85,
                 "PHASE_RAPPORT": 45, "PHASE_DESETUP": 25, "FIN": 0}

for i, p in enumerate(["Poste_01", "Poste_02", "Poste_03"]):
    info_abs = last_actions_absolute[last_actions_absolute["Poste"] == p] if not last_actions_absolute.empty else pd.DataFrame()
    info_prod = last_actions_prod[last_actions_prod["Poste"] == p] if not last_actions_prod.empty else pd.DataFrame()
    with cols[i]:
        with st.container(border=True):
            if not info_abs.empty and info_abs.iloc[0]["Etape"] == "APPEL_REGLAGE":
                row_abs = info_abs.iloc[0]
                st.markdown("<div class='blink-red'>🚨 APPEL RÉGLEUR EN COURS</div>", unsafe_allow_html=True)
                st.markdown(f"### ⚠️ {p}")
                st.markdown(f"## **{row_abs['MSN_Display']}**")
                st.error(f"Motif : {row_abs.get('Info_Sup', 'Inconnu')}")
                duree = int((now - row_abs["DateTime"]).total_seconds() / 60)
                st.markdown(f"⏳ Attente Régleur : **{duree} min**")
            elif not info_abs.empty and info_abs.iloc[0]["Etape"] == "INCIDENT_EN_COURS":
                row_abs = info_abs.iloc[0]
                msn_display = info_prod.iloc[0]["MSN_Display"] if not info_prod.empty else "MAINTENANCE"
                st.markdown(f"### 🟠 {p}")
                st.markdown(f"## **{msn_display}**")
                st.warning(f"🔧 {row_abs.get('Info_Sup', '')}")
                duree = int((now - row_abs["DateTime"]).total_seconds() / 60)
                st.markdown(f"🔧 Temps de Réglage : **{duree} min**")
            elif not info_prod.empty:
                row_prod = info_prod.iloc[0]
                icon = "🟨" if row_prod["Etape"] == "PHASE_SETUP" else ("🟪" if row_prod["Etape"] == "PHASE_DESETUP" else "🟦")
                if row_prod["Type"] == "Rework": icon = "🟥"
                st.markdown(f"### {icon} {p}")
                st.markdown(f"## **{row_prod['MSN_Display']}**")
                st.progress(int(row_prod.get("Progression", 0)))
                reste = TEMPS_RESTANT.get(row_prod["Etape"], 30)
                sortie = now + timedelta(minutes=reste)
                str_duree = f"{reste // 60}h{reste % 60:02d}" if reste >= 60 else f"{reste} min"
                st.caption(f"📍 {row_prod['Etape']}")
                st.markdown(f"⏳ Reste : **{str_duree}**")
                st.markdown(f"🏁 Sortie : **{sortie.strftime('%H:%M')}**")
            else:
                st.markdown(f"### ⬜ {p}")
                st.info("En attente")

# ==============================================================================
# 8) ANALYSE CHEF (fresh uniquement à la demande)
# ==============================================================================
if acces_chef_ok:
    st.divider()
    st.subheader("📊 ANALYSE PERFORMANCE (Accès Chef)")

    st.caption("✅ Optimisé quota : le KPI ne fait une lecture fresh que si tu cliques sur Actualiser.")

    if st.button("🔄 Actualiser KPI (lecture fresh Logs)"):
        try:
            df_fresh = conn.read(worksheet="Logs", ttl=0)
            if df_fresh is None or df_fresh.empty:
                st.warning("Logs vides.")
            else:
                df_fresh = df_fresh[df_fresh.columns[:len(COLS_LOGS)]].copy()
                df_fresh.columns = COLS_LOGS
                df_fresh["DateTime"] = pd.to_datetime(df_fresh["Date"].astype(str) + " " + df_fresh["Heure"].astype(str), errors="coerce")
                df_fresh = df_fresh.dropna(subset=["DateTime"])

                df_kpi = calculer_kpi_pannes(df_fresh)
                st.session_state["kpi_cache"] = df_kpi
        except Exception as e:
            st.error(f"Erreur KPI fresh : {e}")

    df_kpi = st.session_state.get("kpi_cache", pd.DataFrame())
    if not df_kpi.empty:
        total_pannes = len(df_kpi)
        total_attente = int(df_kpi["Attente (min)"].sum())
        total_reglage = int(df_kpi["Réglage (min)"].sum())
        grand_total = total_attente + total_reglage

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔢 Nb Pannes", total_pannes)
        c2.metric("⏳ Total Attente", f"{total_attente} min")
        c3.metric("🔧 Total Réglage", f"{total_reglage} min")
        c4.metric("🛑 Temps Perdu Total", f"{grand_total} min")

        st.markdown("#### 📜 Historique détaillé :")
        st.dataframe(df_kpi, use_container_width=True, hide_index=True)

        csv = df_kpi.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Télécharger le Rapport CSV", csv, "Rapport_Pannes.csv", "text/csv")
    else:
        st.info("Clique sur **Actualiser KPI** pour calculer l’analyse (lecture fresh).")
