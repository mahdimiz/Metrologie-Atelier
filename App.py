import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import random

# ==============================================================================
# 1. CONFIGURATION (V77 - SUPABASE - RAPIDE & PERSISTANT)
# ==============================================================================
st.set_page_config(page_title="Suivi V77 (Supabase)", layout="wide", page_icon="🔒")

MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

def get_heure_fr():
    # Simple +1 comme ton code (tu peux ajuster plus tard)
    return datetime.utcnow() + timedelta(hours=1)

if "mode_admin" not in st.session_state:
    st.session_state.mode_admin = False

# --- CSS (identique) ---
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
# 2. CONNEXION SUPABASE
# ==============================================================================
conn = st.connection("supabase_db", type="sql")

def clear_cache():
    st.cache_data.clear()

# ==============================================================================
# 3. LECTURES SUPABASE (RAPIDES)
#   - LIVE: events LIMIT (super rapide)
#   - Pannes/Consignes/Settings: caches plus longs
# ==============================================================================
EVENT_COLS = ["ts", "poste", "se_unique", "msn_display", "etape", "info_sup"]

@st.cache_data(ttl=2)
def read_events_live(limit=400):
    # LIVE = derniers events seulement
    df = conn.query("""
        SELECT ts, poste, se_unique, msn_display, etape, info_sup
        FROM public.events
        ORDER BY ts DESC
        LIMIT :lim
    """, params={"lim": limit})
    if df.empty:
        return pd.DataFrame(columns=EVENT_COLS)
    df["DateTime"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna(subset=["DateTime"])
    return df

@st.cache_data(ttl=60)
def read_pannes():
    df = conn.query("""SELECT zone, nom FROM public.pannes ORDER BY zone, nom""")
    if df.empty:
        return pd.DataFrame(columns=["Zone", "Nom"])
    return df.rename(columns={"zone": "Zone", "nom": "Nom"})

@st.cache_data(ttl=15)
def read_consignes():
    df = conn.query("""SELECT type, msn, poste, emplacement FROM public.consignes ORDER BY id""")
    if df.empty:
        return pd.DataFrame(columns=["Type", "MSN", "Poste", "Emplacement"])
    return df.rename(columns={"type": "Type", "msn": "MSN", "poste": "Poste", "emplacement": "Emplacement"})

@st.cache_data(ttl=30)
def read_objectif():
    df = conn.query("""SELECT value FROM public.settings WHERE key='objectif' LIMIT 1""")
    if df.empty:
        return 35
    try:
        return int(df.iloc[0]["value"])
    except:
        return 35

# ==============================================================================
# 4. ÉCRITURE SUPABASE (remplace open(csv, "a"))
# ==============================================================================
def append_event(date_dt, poste, se_unique, msn_display, etape, info_sup=""):
    conn.query("""
        INSERT INTO public.events(ts, poste, se_unique, msn_display, etape, info_sup)
        VALUES (:ts, :poste, :se, :msn, :etape, :info)
    """, params={
        "ts": date_dt,
        "poste": poste,
        "se": se_unique,
        "msn": msn_display,
        "etape": etape,
        "info": info_sup
    })
    clear_cache()

def set_objectif(val):
    conn.query("""
        INSERT INTO public.settings(key, value)
        VALUES ('objectif', :v)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, params={"v": str(int(val))})
    clear_cache()

def add_panne(zone, nom):
    conn.query("""INSERT INTO public.pannes(zone, nom) VALUES (:z, :n)""", params={"z": zone, "n": nom})
    clear_cache()

def delete_panne(zone, nom):
    conn.query("""DELETE FROM public.pannes WHERE zone=:z AND nom=:n""", params={"z": zone, "n": nom})
    clear_cache()

def add_consigne(tp, msn, poste, emplacement):
    conn.query("""INSERT INTO public.consignes(type, msn, poste, emplacement)
                  VALUES (:t, :m, :p, :e)""",
               params={"t": tp, "m": msn, "p": poste, "e": emplacement})
    clear_cache()

def delete_consignes(msn_list):
    if not msn_list:
        return
    conn.query("""DELETE FROM public.consignes WHERE msn = ANY(:arr)""", params={"arr": msn_list})
    clear_cache()

def clear_consignes():
    conn.query("""DELETE FROM public.consignes""")
    clear_cache()

def clear_events():
    conn.query("""DELETE FROM public.events""")
    clear_cache()

# ==============================================================================
# 5. CHARGEMENT "DATAFRAME" COMME AVANT (df, df_consignes, df_pannes, objectif)
# ==============================================================================
df = read_events_live(limit=500)  # juste pour le live / démo
df_consignes = read_consignes()
df_pannes = read_pannes()
VAL_OBJECTIF = read_objectif()

def get_liste_pannes(zone):
    if df_pannes.empty:
        return []
    return df_pannes[df_pannes["Zone"] == zone]["Nom"].tolist()

REGLAGES_GAUCHE = get_liste_pannes("GAUCHE")
REGLAGES_DROIT = get_liste_pannes("DROIT")
REGLAGES_GENERIC = get_liste_pannes("GENERIC")

# ==============================================================================
# 6. FONCTIONS (identiques à ton code)
# ==============================================================================
def calculer_kpi_pannes(dataframe):
    if dataframe.empty:
        return pd.DataFrame()

    # On prend seulement les maintenances
    df_maint = dataframe[dataframe["etape"].isin(["APPEL_REGLAGE", "INCIDENT_EN_COURS", "INCIDENT_FINI"])].copy()
    if df_maint.empty:
        return pd.DataFrame()

    df_maint = df_maint.sort_values("DateTime")
    rapports = []

    for poste in df_maint["poste"].dropna().unique():
        logs_poste = df_maint[df_maint["poste"] == poste].sort_values("DateTime")
        current_cycle = {}

        for _, row in logs_poste.iterrows():
            etape = row["etape"]
            msn_brut = str(row.get("msn_display", ""))
            msn_clean = msn_brut.replace("MSN-", "") if "MSN-" in msn_brut else msn_brut

            if etape == "APPEL_REGLAGE":
                current_cycle = {
                    "Poste": poste,
                    "MSN": msn_clean,
                    "Cause": str(row.get("info_sup", "")),
                    "Heure_Appel": row["DateTime"],
                    "Heure_Debut": None,
                    "Heure_Fin": None
                }

            elif etape == "INCIDENT_EN_COURS":
                # Si le cycle n'existe pas (cas manuel), on crée quand même
                if not current_cycle:
                    current_cycle = {
                        "Poste": poste,
                        "MSN": msn_clean,
                        "Cause": str(row.get("info_sup", "")),
                        "Heure_Appel": row["DateTime"],
                        "Heure_Debut": row["DateTime"],
                        "Heure_Fin": None
                    }
                else:
                    current_cycle["Heure_Debut"] = row["DateTime"]

            elif etape == "INCIDENT_FINI":
                if current_cycle and current_cycle.get("Heure_Debut") is not None:
                    current_cycle["Heure_Fin"] = row["DateTime"]

                    attente = (current_cycle["Heure_Debut"] - current_cycle["Heure_Appel"]).total_seconds() / 60
                    reglage = (current_cycle["Heure_Fin"] - current_cycle["Heure_Debut"]).total_seconds() / 60

                    rapports.append({
                        "Date": current_cycle["Heure_Appel"].strftime("%d/%m"),
                        "Heure": current_cycle["Heure_Appel"].strftime("%H:%M"),
                        "Poste": poste,
                        "MSN": current_cycle.get("MSN", "?"),
                        "Cause": current_cycle.get("Cause", ""),
                        "Attente (min)": int(attente),
                        "Réglage (min)": int(reglage),
                        "Total (min)": int(attente + reglage),
                    })
                    current_cycle = {}

    return pd.DataFrame(rapports)

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
        if time(6, 30) <= t < time(14, 50):
            nom_shift, shifts_passes = "🌅 Shift Matin", shifts_passes + 0.5
        elif time(14, 50) <= t or t <= time(0, 9):
            nom_shift, shifts_passes = "🌙 Shift Soir", shifts_passes + 1.5
        else:
            shifts_passes += 2.0

    elif day == 4:
        if time(6, 30) <= t < time(15, 50):
            nom_shift, shifts_passes = "🌅 Shift Matin (Vendredi)", shifts_passes + 0.5
        else:
            shifts_passes += 1.0

    return nom_shift, min(shifts_passes, 9.0)

def analyser_type(se_name):
    if not isinstance(se_name, str) or len(se_name) < 1:
        return "Inconnu"
    if se_name[0].upper() == "S":
        return "Série"
    if se_name[0].upper() == "R":
        return "Rework"
    if se_name[0].upper() == "M":
        return "MIP"
    return "Autre"

def deviner_contexte_poste(poste_choisi, dataframe):
    if dataframe.empty:
        return "Inconnu"
    # dataframe ici = df (events live)
    df_clean = dataframe[~dataframe["etape"].astype(str).str.contains("INCIDENT|APPEL", na=False)]
    actions_poste = df_clean[df_clean["poste"] == poste_choisi].sort_values("DateTime")
    if actions_poste.empty:
        return "Inconnu"
    derniere_etape = str(actions_poste.iloc[-1]["etape"])
    if derniere_etape in ["PHASE_SETUP", "STATION_BRAS", "STATION_TRK1"]:
        return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2", "PHASE_RAPPORT"]:
        return "DROIT"
    else:
        return "GENERIC"

def get_info_msn(msn_cherche, df_logs):
    if df_logs.empty:
        return "⚪ À faire", "⚡ Premier Dispo"
    logs_msn = df_logs[df_logs["msn_display"].astype(str).str.contains(str(msn_cherche), na=False)]
    if logs_msn.empty:
        return "⚪ À faire", "⚡ Premier Dispo"
    last_log = logs_msn.sort_values("DateTime").iloc[0]  # attention: df_logs déjà DESC, mais on garde logique
    qui = last_log.get("poste", "?")
    if last_log.get("etape") == "FIN":
        return "🟢 Fini", f"✅ Fait par {qui}"
    return "🟡 En cours", f"🛠️ Pris par {qui}"

# ==============================================================================
# 7. SIDEBAR (même logique)
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

    # ----------------------------------------------------------
    # OPÉRATEUR
    # ----------------------------------------------------------
    if role == "Opérateur":
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
        st.subheader("🔨 Production")

        poste_occupe = False
        msn_en_cours = ""
        se_unique_en_cours = ""
        type_en_cours = "Série"
        etat_appel = False

        if not df.empty:
            df_poste = df[df["poste"] == sim_poste].sort_values("DateTime")
            if not df_poste.empty:
                last_action = df_poste.iloc[0]  # df est DESC
                if last_action["etape"] == "APPEL_REGLAGE":
                    poste_occupe = True
                    etat_appel = True
                    prev = df_poste[df_poste["etape"] != "APPEL_REGLAGE"]
                    if not prev.empty:
                        last_real = prev.iloc[0]
                        msn_en_cours = str(last_real.get("msn_display", "")).replace("MSN-", "")
                        se_unique_en_cours = str(last_real.get("se_unique", ""))
                elif last_action["etape"] == "INCIDENT_EN_COURS":
                    poste_occupe = True
                    msn_en_cours = "MAINTENANCE"
                elif last_action["etape"] != "FIN":
                    poste_occupe = True
                    msn_en_cours = str(last_action.get("msn_display", "")).replace("MSN-", "")
                    se_unique_en_cours = str(last_action.get("se_unique", ""))
                    if se_unique_en_cours.startswith("R"):
                        type_en_cours = "Rework"
                    elif se_unique_en_cours.startswith("M"):
                        type_en_cours = "MIP"

        if poste_occupe:
            if etat_appel:
                st.error("🆘 APPEL LANCÉ !")
                st.info("Attendez le régleur.")
            elif msn_en_cours == "MAINTENANCE":
                st.warning("🔧 Régleur en cours...")
            else:
                st.warning(f"⚠️ **EN COURS : MSN-{msn_en_cours}**")
                with st.expander("🚨 APPEL RÉGLEUR"):
                    contexte = deviner_contexte_poste(sim_poste, df)
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
                            now = get_heure_fr()
                            str_raisons = " + ".join(raisons_appel)
                            if num_mat:
                                str_raisons = f"[MAT:{num_mat}] {str_raisons}"
                            append_event(
                                date_dt=now,
                                poste=sim_poste,
                                se_unique=se_unique_en_cours,
                                msn_display=f"MSN-{msn_en_cours}",
                                etape="APPEL_REGLAGE",
                                info_sup=str_raisons
                            )
                            st.rerun()

                st.markdown("---")
                sim_msn = msn_en_cours
                nom_se_complet = se_unique_en_cours
                c1, c2 = st.columns(2)

                if c1.button("🔵 Bras"):
                    now = get_heure_fr()
                    append_event(now, sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_BRAS", "")
                    st.rerun()

                if c2.button("🔵 Trk 1"):
                    now = get_heure_fr()
                    append_event(now, sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK1", "")
                    st.rerun()

                if st.button("🔵 Track 2", use_container_width=True):
                    now = get_heure_fr()
                    append_event(now, sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK2", "")
                    st.rerun()

                st.write("")
                if st.button("🟣 Fin / Démont.", use_container_width=True):
                    now = get_heure_fr()
                    append_event(now, sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DESETUP", "")
                    st.rerun()

                if st.button("✅ LIBÉRER (FINI)", type="primary", use_container_width=True):
                    now = get_heure_fr()
                    append_event(now, sim_poste, "Aucun", "Aucun", "FIN", "")
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

            if not df.empty:
                # Vérif dans le LIVE (derniers events)
                df_msn_check = df[df["msn_display"] == f"MSN-{sim_msn}"].sort_values("DateTime")
                if not df_msn_check.empty:
                    last_check = df_msn_check.iloc[0]
                    if last_check["etape"] not in ["FIN", "INCIDENT_FINI"] and last_check["poste"] != sim_poste:
                        msn_deja_pris = True
                        qui_a_le_msn = str(last_check["poste"])

            prefix = "S" if sim_type == "Série" else ("R" if sim_type == "Rework" else "M")
            nom_se_complet = f"{prefix}-SE-MSN-{sim_msn}"
            st.markdown("---")

            if msn_deja_pris:
                st.error(f"⛔ STOP ! {qui_a_le_msn} travaille déjà dessus !")
            else:
                if st.button("🟡 DÉMARRER (Setup)", use_container_width=True, type="primary"):
                    now = get_heure_fr()
                    append_event(now, sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_SETUP", "")
                    st.rerun()

    # ----------------------------------------------------------
    # RÉGLEUR
    # ----------------------------------------------------------
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

            if not df.empty:
                df_p = df[df["poste"] == sim_poste].sort_values("DateTime")
                if not df_p.empty:
                    last_evt = df_p.iloc[0]
                    info_sup = str(last_evt.get("info_sup", ""))
                    start_time_evt = last_evt["DateTime"]

                    if last_evt["etape"] == "APPEL_REGLAGE":
                        etat_poste = "APPEL_EN_COURS"
                    elif last_evt["etape"] == "INCIDENT_EN_COURS":
                        etat_poste = "INTERVENTION_EN_COURS"
                    elif last_evt["etape"] != "FIN":
                        etat_poste = "EN_PROD"

            if etat_poste == "VIDE":
                st.warning(f"🚫 {sim_poste} est vide.")

            elif etat_poste == "APPEL_EN_COURS":
                st.markdown(f"<h3 style='color:red'>🚨 APPEL : {info_sup}</h3>", unsafe_allow_html=True)
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.error(f"⏳ Attente depuis : {duree} min")

                if st.button("✅ ACCEPTER & DÉMARRER", type="primary", use_container_width=True):
                    now = get_heure_fr()
                    append_event(now, sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", info_sup)
                    st.rerun()

            elif etat_poste == "INTERVENTION_EN_COURS":
                st.info(f"🔧 En cours : {info_sup}")
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.warning(f"⏱️ Temps passé : {duree} min")

                if st.button("✅ FIN RÉGLAGE (Reprise)", type="primary", use_container_width=True):
                    now = get_heure_fr()
                    append_event(now, sim_poste, "MAINTENANCE", "System", "INCIDENT_FINI", "Reprise")
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
                        now = get_heure_fr()
                        str_raisons = " + ".join(causes_choisies)
                        if num_mat_regleur:
                            str_raisons = f"[MAT:{num_mat_regleur}] {str_raisons}"
                        append_event(now, sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", str_raisons)
                        st.rerun()

        elif pwd:
            st.error("⛔ Code Faux !")

    # ----------------------------------------------------------
    # CHEF D'ÉQUIPE
    # ----------------------------------------------------------
    elif role == "Chef d'Équipe":
        pwd = st.text_input("🔑 Code PIN Chef", type="password")
        st.button("🔓 Se connecter", key="btn_chef")

        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")
            acces_chef_ok = True

            st.subheader("🎯 Objectif Semaine")
            nouveau_obj = st.number_input("Définir l'objectif :", value=int(VAL_OBJECTIF), step=1)

            if st.button("💾 Valider Objectif"):
                set_objectif(nouveau_obj)
                st.success(f"Objectif passé à {int(nouveau_obj)} !")
                st.rerun()

            st.divider()

            with st.expander("⚙️ Gérer la liste des Pannes"):
                st.write("Ajouter ou supprimer des pannes")
                new_panne = st.text_input("Nouvelle Panne")
                new_zone = st.selectbox("Zone", ["GAUCHE", "DROIT", "GENERIC"])

                if st.button("Ajouter à la liste"):
                    if new_panne.strip():
                        add_panne(new_zone, new_panne.strip())
                        st.success("Ajouté !")
                        st.rerun()
                    else:
                        st.error("Nom panne vide")

                st.markdown("---")
                if not df_pannes.empty:
                    dfp = df_pannes.copy()
                    dfp["Label"] = dfp["Zone"] + " - " + dfp["Nom"]
                    to_del = st.selectbox("Supprimer une panne :", dfp["Label"].unique())
                    if st.button("Supprimer"):
                        z, n = to_del.split(" - ", 1)
                        delete_panne(z, n)
                        st.success("Supprimé !")
                        st.rerun()

            st.divider()
            sim_mode = st.checkbox("🔮 Activer Simulation", value=False)
            if sim_mode:
                nb_pieces_simu = st.number_input("Nb Pièces :", value=10)

            st.divider()
            if st.button("⚠️ RAZ Logs Production"):
                clear_events()
                st.rerun()

        elif pwd:
            st.error("⛔ Code Faux !")

    # ----------------------------------------------------------
    # RDZ
    # ----------------------------------------------------------
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
                    if not c_msn.strip() or not c_loc.strip():
                        st.error("Infos manquantes !")
                    else:
                        msn_value = f"MSN-{c_msn.strip()}" if not c_msn.strip().startswith("MSN-") else c_msn.strip()
                        # contrôle doublon
                        if not df_consignes.empty and msn_value in df_consignes["MSN"].values:
                            st.error(f"⚠️ {msn_value} existe déjà !")
                        else:
                            add_consigne(c_type, msn_value, "Indifférent", c_loc.strip())
                            st.success("Ajouté !")
                            st.rerun()

            st.divider()
            if not df_consignes.empty:
                dfc = df_consignes.copy()
                dfc["Label"] = dfc["MSN"] + " (" + dfc["Type"] + ")"
                to_delete = st.multiselect("Effacer :", dfc["Label"].unique())

                if st.button("Supprimer Sélection"):
                    # récupérer les msn depuis "MSN (Type)"
                    msn_list = [x.split(" (", 1)[0] for x in to_delete]
                    delete_consignes(msn_list)
                    st.success("Supprimé !")
                    st.rerun()

            if st.button("🔥 Tout effacer"):
                clear_consignes()
                st.rerun()

        elif pwd:
            st.error("⛔ Code Faux !")

    st.divider()
    st.checkbox("🔓 Mode Admin", key="mode_admin")

# ==============================================================================
# 8. DASHBOARD (même esprit, optimisé)
# ==============================================================================
debut_semaine = get_start_of_week()
nom_shift_actuel, shifts_ecoules = get_current_shift_info()

mapping_etapes = {
    "PHASE_SETUP": 5,
    "STATION_BRAS": 15,
    "STATION_TRK1": 30,
    "STATION_TRK2": 65,
    "PHASE_RAPPORT": 90,
    "PHASE_DESETUP": 95,
    "FIN": 100
}

# On travaille sur df (events live)
nb_realise = 0
nb_rework = 0
nb_mip = 0
last_actions_absolute = pd.DataFrame()
last_actions_prod = pd.DataFrame()

if not df.empty:
    df_week = df[df["DateTime"] >= debut_semaine].copy()
    if not df_week.empty:
        # production pure = tout sauf incident/appel
        df_week["Type"] = df_week["se_unique"].apply(analyser_type)
        df_week["Progression"] = df_week["etape"].map(mapping_etapes).fillna(0)

        df_prod_pure = df_week[~df_week["etape"].astype(str).str.contains("INCIDENT|APPEL", na=False)].copy()

        if not df_prod_pure.empty:
            # Comme df_week est live (DESC), on trie ASC avant groupby last
            etat_global = df_prod_pure.sort_values("DateTime").groupby("se_unique").last().reset_index()
            pieces_terminees = etat_global[etat_global["Progression"] >= 95]
            nb_realise = pieces_terminees[pieces_terminees["Type"] == "Série"].shape[0]
            nb_rework = pieces_terminees[pieces_terminees["Type"] == "Rework"].shape[0]
            nb_mip = pieces_terminees[pieces_terminees["Type"] == "MIP"].shape[0]

            last_actions_prod = df_prod_pure.sort_values("DateTime").groupby("poste").last().reset_index()

        last_actions_absolute = df_week.sort_values("DateTime").groupby("poste").last().reset_index()

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

if sim_mode:
    msg = f"Avec {int(nb_pieces_simu)} pièces MAINTENANT 👉 DELTA : {delta:+.1f}"
else:
    msg = f"🚀 AVANCE : {delta:+.1f}" if delta >= 0 else f"🐢 RETARD : {delta:+.1f}"

st.markdown(
    f"<div style='padding:10px;border-radius:5px;background-color:{couleur_bandeau};color:white;text-align:center;font-weight:bold;'>{msg}</div>",
    unsafe_allow_html=True
)

# --------- ORDRE DE PASSAGE ----------
if not sim_mode:
    st.write("")
    st.subheader("📋 ORDRE DE PASSAGE & EMPLACEMENTS")
    col_serie, col_mip, col_rework = st.columns(3)

    def afficher_colonne_prio(type_col, couleur_bordure):
        if not df_consignes.empty:
            items = df_consignes[df_consignes["Type"] == type_col]
            rank = 1
            for _, row in items.iterrows():
                txt_statut, txt_qui = get_info_msn(row["MSN"], df)

                if txt_statut == "🟢 Fini":
                    opacity = "0.4"
                elif txt_statut == "🟡 En cours":
                    opacity = "1.0; border: 2px solid #f1c40f"
                else:
                    opacity = "1.0"

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

TEMPS_RESTANT = {
    "PHASE_SETUP": 245,
    "STATION_BRAS": 210,
    "STATION_TRK1": 175,
    "STATION_TRK2": 85,
    "PHASE_RAPPORT": 45,
    "PHASE_DESETUP": 25,
    "FIN": 0
}

for i, p in enumerate(["Poste_01", "Poste_02", "Poste_03"]):
    info_abs = last_actions_absolute[last_actions_absolute["poste"] == p] if not last_actions_absolute.empty else pd.DataFrame()
    info_prod = last_actions_prod[last_actions_prod["poste"] == p] if not last_actions_prod.empty else pd.DataFrame()

    with cols[i]:
        with st.container(border=True):
            if not info_abs.empty and info_abs.iloc[0]["etape"] == "APPEL_REGLAGE":
                row_abs = info_abs.iloc[0]
                msn_display = row_abs.get("msn_display", "")
                st.markdown("<div class='blink-red'>🚨 APPEL RÉGLEUR EN COURS</div>", unsafe_allow_html=True)
                st.markdown(f"### ⚠️ {p}")
                st.markdown(f"## **{msn_display}**")
                st.error(f"Motif : {row_abs.get('info_sup', 'Inconnu')}")
                duree = int((now - row_abs["DateTime"]).total_seconds() / 60)
                st.markdown(f"⏳ Attente Régleur : **{duree} min**")

            elif not info_abs.empty and info_abs.iloc[0]["etape"] == "INCIDENT_EN_COURS":
                row_abs = info_abs.iloc[0]
                msn_display = "MAINTENANCE"
                if not info_prod.empty:
                    msn_display = info_prod.iloc[0].get("msn_display", "MAINTENANCE")
                st.markdown(f"### 🟠 {p}")
                st.markdown(f"## **{msn_display}**")
                st.warning(f"🔧 {row_abs.get('info_sup', '')}")
                duree = int((now - row_abs["DateTime"]).total_seconds() / 60)
                st.markdown(f"🔧 Temps de Réglage : **{duree} min**")

            elif not info_prod.empty:
                row_prod = info_prod.iloc[0]
                prog = int(row_prod.get("Progression", 0))

                if prog < 100:
                    icon = "🟨" if row_prod["etape"] == "PHASE_SETUP" else ("🟪" if row_prod["etape"] == "PHASE_DESETUP" else "🟦")
                    if row_prod.get("Type") == "Rework":
                        icon = "🟥"

                    st.markdown(f"### {icon} {p}")
                    st.markdown(f"## **{row_prod.get('msn_display','')}**")
                    st.progress(prog)

                    reste = TEMPS_RESTANT.get(row_prod["etape"], 30)
                    sortie = now + timedelta(minutes=reste)
                    str_duree = f"{reste // 60}h{reste % 60:02d}" if reste >= 60 else f"{reste} min"

                    st.caption(f"📍 {row_prod['etape']}")
                    st.markdown(f"⏳ Reste : **{str_duree}**")
                    st.markdown(f"🏁 Sortie : **{sortie.strftime('%H:%M')}**")
                else:
                    st.markdown(f"### 🟦 {p}")
                    st.success("✅ Poste Libre")

            else:
                st.markdown(f"### ⬜ {p}")
                st.info("En attente")

# ==============================================================================
# 9. KPI CHEF (à la demande, et sur la "semaine atelier")
# ==============================================================================
if acces_chef_ok:
    st.divider()
    st.subheader("📊 ANALYSE PERFORMANCE (Accès Chef)")

    # IMPORTANT : KPI doit être basé sur plus que les 500 derniers events.
    # Donc on lit la semaine depuis Supabase quand on affiche l'analyse.
    start = get_start_of_week()
    df_week_full = conn.query("""
        SELECT ts, poste, se_unique, msn_display, etape, info_sup
        FROM public.events
        WHERE ts >= :start
        ORDER BY ts ASC
    """, params={"start": start})

    if df_week_full.empty:
        st.info("Pas encore de données cette semaine.")
    else:
        df_week_full["DateTime"] = pd.to_datetime(df_week_full["ts"], errors="coerce")
        df_week_full = df_week_full.dropna(subset=["DateTime"])

        # Adapter noms colonnes attendus par calculer_kpi_pannes
        # (ton calcul utilise dataframe["etape"], ["poste"], ["msn_display"], ["info_sup"])
        df_kpi = calculer_kpi_pannes(df_week_full)

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
            st.download_button("📥 Télécharger le Rapport CSV", data=csv, file_name="Rapport_Pannes.csv", mime="text/csv")
        else:
            st.info("Tout va bien ! Aucune panne terminée pour l'instant.")
