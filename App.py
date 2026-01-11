import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import random

# ==============================================================================
# 1. CONFIG (V77 + SUPABASE)
# ==============================================================================
st.set_page_config(page_title="Suivi V77", layout="wide", page_icon="🔒")

MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

def get_heure_fr():
    return datetime.utcnow() + timedelta(hours=1)

if "mode_admin" not in st.session_state:
    st.session_state.mode_admin = False

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
    st.markdown("""<style>header, footer, .stDeployButton {display:none;} .block-container{padding-top:1rem;}</style>""",
                unsafe_allow_html=True)

# ==============================================================================
# 2. SUPABASE (CONNEXION + TABLES)
# ==============================================================================

@st.cache_resource
def get_db():
    # utilise [connections.supabase_db] dans Secrets (TOML)
    return st.connection("supabase_db", type="sql")

def db_init_tables():
    """Crée les tables si elles n'existent pas (safe)."""
    conn = get_db()
    conn.query("""
        create table if not exists public.events (
            id bigserial primary key,
            ts timestamptz not null default now(),
            date text,
            heure text,
            poste text,
            se_unique text,
            msn_display text,
            etape text,
            info_sup text
        );
    """, ttl=0)

    conn.query("""
        create table if not exists public.consignes (
            id bigserial primary key,
            type text,
            msn text,
            poste text,
            emplacement text
        );
    """, ttl=0)

    conn.query("""
        create table if not exists public.pannes (
            id bigserial primary key,
            zone text,
            nom text
        );
    """, ttl=0)

    conn.query("""
        create table if not exists public.settings (
            k text primary key,
            v text
        );
    """, ttl=0)

# On initialise 1 fois
try:
    db_init_tables()
except Exception as e:
    st.error("❌ Supabase: impossible d'initialiser les tables (vérifie Secrets).")
    st.stop()

def insert_event(poste, se_unique, msn_display, etape, info_sup=""):
    now = get_heure_fr()
    conn = get_db()
    conn.query(
        """
        insert into public.events (ts, date, heure, poste, se_unique, msn_display, etape, info_sup)
        values (now(), :date, :heure, :poste, :se_unique, :msn_display, :etape, :info_sup)
        """,
        params={
            "date": now.strftime("%Y-%m-%d"),
            "heure": now.strftime("%H:%M:%S"),
            "poste": poste,
            "se_unique": se_unique,
            "msn_display": msn_display,
            "etape": etape,
            "info_sup": info_sup or ""
        },
        ttl=0
    )

@st.cache_data(ttl=2)
def read_events_live(limit=800):
    conn = get_db()
    df = conn.query(
        """
        select date, heure, poste, se_unique, msn_display, etape, info_sup, ts
        from public.events
        order by ts desc
        limit :limit
        """,
        params={"limit": int(limit)},
        ttl=0
    )
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date","Heure","Poste","SE_Unique","MSN_Display","Etape","Info_Sup","DateTime"])
    df = df.rename(columns={
        "date":"Date",
        "heure":"Heure",
        "poste":"Poste",
        "se_unique":"SE_Unique",
        "msn_display":"MSN_Display",
        "etape":"Etape",
        "info_sup":"Info_Sup",
        "ts":"ts"
    })
    df["DateTime"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(None)
    return df.drop(columns=["ts"], errors="ignore")

@st.cache_data(ttl=30)
def read_consignes():
    conn = get_db()
    df = conn.query("select type, msn, poste, emplacement from public.consignes order by id desc", ttl=0)
    if df is None or df.empty:
        return pd.DataFrame(columns=["Type","MSN","Poste","Emplacement"])
    return df.rename(columns={"type":"Type","msn":"MSN","poste":"Poste","emplacement":"Emplacement"})

@st.cache_data(ttl=30)
def read_pannes():
    conn = get_db()
    df = conn.query("select zone, nom from public.pannes order by id desc", ttl=0)
    if df is None or df.empty:
        return pd.DataFrame(columns=["Zone","Nom"])
    return df.rename(columns={"zone":"Zone","nom":"Nom"})

def get_setting(key, default=""):
    conn = get_db()
    df = conn.query("select v from public.settings where k = :k", params={"k": key}, ttl=0)
    if df is None or df.empty:
        return default
    return str(df.iloc[0]["v"])

def set_setting(key, value):
    conn = get_db()
    conn.query(
        """
        insert into public.settings(k, v) values(:k, :v)
        on conflict (k) do update set v = excluded.v
        """,
        params={"k": key, "v": str(value)},
        ttl=0
    )

# ==============================================================================
# 3. CHARGEMENT DONNÉES (SUPABASE)
# ==============================================================================
df = read_events_live(limit=1200)
df_consignes = read_consignes()
df_pannes = read_pannes()

# Si pannes vide, on met une base par défaut UNE SEULE FOIS
if df_pannes.empty:
    data_defaut = [
        ("GAUCHE", "🔧 Capot Gauche (ST1)"),
        ("GAUCHE", "🔧 PAF"),
        ("GAUCHE", "🔧 Cornière SSAV Gauche"),
        ("DROIT", "🔧 Capot Droit (ST2)"),
        ("DROIT", "🔧 Cornière SSAV Droite"),
        ("GENERIC", "⚠️ SO3 - Pipes Arrière"),
    ]
    conn = get_db()
    for z, n in data_defaut:
        conn.query("insert into public.pannes(zone, nom) values(:z, :n)", params={"z": z, "n": n}, ttl=0)
    st.cache_data.clear()
    df_pannes = read_pannes()

def get_liste_pannes(zone):
    if df_pannes.empty:
        return []
    return df_pannes[df_pannes["Zone"] == zone]["Nom"].tolist()

REGLAGES_GAUCHE = get_liste_pannes("GAUCHE")
REGLAGES_DROIT = get_liste_pannes("DROIT")
REGLAGES_GENERIC = get_liste_pannes("GENERIC")

# ==============================================================================
# 4. KPI / FONCTIONS (identiques V77)
# ==============================================================================
def calculer_kpi_pannes(dataframe):
    if dataframe.empty:
        return pd.DataFrame()
    df_maint = dataframe[dataframe['Etape'].isin(['APPEL_REGLAGE', 'INCIDENT_EN_COURS', 'INCIDENT_FINI'])].sort_values('DateTime')
    rapports = []

    for poste in df_maint['Poste'].unique():
        logs_poste = df_maint[df_maint['Poste'] == poste].sort_values('DateTime')
        current_cycle = {}
        for _, row in logs_poste.iterrows():
            etape = row['Etape']
            msn_brut = str(row['MSN_Display'])
            msn_clean = msn_brut.replace("MSN-", "") if "MSN-" in msn_brut else msn_brut

            if etape == 'APPEL_REGLAGE':
                current_cycle = {
                    'Poste': poste, 'MSN': msn_clean, 'Cause': row.get('Info_Sup', ''),
                    'Heure_Appel': row['DateTime'], 'Heure_Debut': None, 'Heure_Fin': None
                }
            elif etape == 'INCIDENT_EN_COURS':
                if not current_cycle:
                    current_cycle = {
                        'Poste': poste, 'MSN': msn_clean, 'Cause': row.get('Info_Sup', ''),
                        'Heure_Appel': row['DateTime'], 'Heure_Debut': row['DateTime'], 'Heure_Fin': None
                    }
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
                        "Cause": current_cycle.get('Cause', ''),
                        "Attente (min)": int(attente),
                        "Réglage (min)": int(reglage),
                        "Total (min)": int(attente + reglage)
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
    df_clean = dataframe[~dataframe["Etape"].str.contains("INCIDENT|APPEL", na=False)]
    actions_poste = df_clean[df_clean["Poste"] == poste_choisi].sort_values("DateTime")
    if actions_poste.empty:
        return "Inconnu"
    derniere_etape = str(actions_poste.iloc[-1]["Etape"])
    if derniere_etape in ["PHASE_SETUP", "STATION_BRAS", "STATION_TRK1"]:
        return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2", "PHASE_RAPPORT"]:
        return "DROIT"
    else:
        return "GENERIC"

# ==============================================================================
# 5. SIDEBAR (UI inchangé)
# ==============================================================================
with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
    st.divider()

    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe"])
    st.divider()

    # -------------------------
    # OPÉRATEUR
    # -------------------------
    if role == "Opérateur":
        sim_poste = st.selectbox("📍 Poste concerné", ["Poste_01", "Poste_02", "Poste_03"])
        st.subheader("🔨 Production")

        poste_occupe = False
        msn_en_cours = ""
        se_unique_en_cours = ""
        type_en_cours = "Série"
        etat_appel = False

        if not df.empty:
            df_poste = df[df["Poste"] == sim_poste].sort_values("DateTime")
            if not df_poste.empty:
                last_action = df_poste.iloc[-1]
                if last_action["Etape"] == "APPEL_REGLAGE":
                    poste_occupe = True
                    etat_appel = True
                    prev = df_poste[df_poste["Etape"] != "APPEL_REGLAGE"]
                    if not prev.empty:
                        last_real = prev.iloc[-1]
                        msn_en_cours = str(last_real["MSN_Display"]).replace("MSN-", "")
                        se_unique_en_cours = str(last_real["SE_Unique"])
                elif last_action["Etape"] == "INCIDENT_EN_COURS":
                    poste_occupe = True
                    msn_en_cours = "MAINTENANCE"
                elif last_action["Etape"] != "FIN":
                    poste_occupe = True
                    msn_en_cours = str(last_action["MSN_Display"]).replace("MSN-", "")
                    se_unique_en_cours = str(last_action["SE_Unique"])
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
                            str_raisons = " + ".join(raisons_appel)
                            if num_mat:
                                str_raisons = f"[MAT:{num_mat}] {str_raisons}"
                            insert_event(
                                poste=sim_poste,
                                se_unique=se_unique_en_cours,
                                msn_display=f"MSN-{msn_en_cours}",
                                etape="APPEL_REGLAGE",
                                info_sup=str_raisons
                            )
                            st.cache_data.clear()
                            st.rerun()

                st.markdown("---")
                sim_msn = msn_en_cours
                nom_se_complet = se_unique_en_cours

                c1, c2 = st.columns(2)
                if c1.button("🔵 Bras"):
                    insert_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_BRAS")
                    st.cache_data.clear(); st.rerun()

                if c2.button("🔵 Trk 1"):
                    insert_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK1")
                    st.cache_data.clear(); st.rerun()

                if st.button("🔵 Track 2", use_container_width=True):
                    insert_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK2")
                    st.cache_data.clear(); st.rerun()

                if st.button("🟣 Fin / Démont.", use_container_width=True):
                    insert_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DESETUP")
                    st.cache_data.clear(); st.rerun()

                if st.button("✅ LIBÉRER (FINI)", type="primary", use_container_width=True):
                    insert_event(sim_poste, "Aucun", "Aucun", "FIN")
                    st.cache_data.clear(); st.rerun()

        else:
            st.success("✅ Poste Libre")
            sim_type = st.radio("Type", ["Série", "Rework", "MIP"], horizontal=True)

            if not df_consignes.empty:
                liste_msn = df_consignes["MSN"].unique().tolist()
                st.markdown("👇 **Prendre dans la liste :**")
                selection_msn = st.selectbox("Sélection MSN", liste_msn)
                sim_msn = str(selection_msn).replace("MSN-", "")
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
                df_msn_check = df[df["MSN_Display"] == f"MSN-{sim_msn}"].sort_values("DateTime")
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
                    insert_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_SETUP")
                    st.cache_data.clear(); st.rerun()

    # -------------------------
    # RÉGLEUR
    # -------------------------
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
                df_p = df[df["Poste"] == sim_poste].sort_values("DateTime")
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
                    insert_event(sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", info_sup)
                    st.cache_data.clear(); st.rerun()

            elif etat_poste == "INTERVENTION_EN_COURS":
                st.info(f"🔧 En cours : {info_sup}")
                if start_time_evt:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.warning(f"⏱️ Temps passé : {duree} min")

                if st.button("✅ FIN RÉGLAGE (Reprise)", type="primary", use_container_width=True):
                    insert_event(sim_poste, "MAINTENANCE", "System", "INCIDENT_FINI", "Reprise")
                    st.cache_data.clear(); st.rerun()

            elif etat_poste == "EN_PROD":
                st.info("Arrêt manuel ?")
                liste_complete = REGLAGES_GAUCHE + REGLAGES_DROIT + REGLAGES_GENERIC
                causes_choisies = st.multiselect("Motif :", liste_complete)
                num_mat_regleur = st.text_input("📝 N° MAT (Optionnel)", placeholder="Ex: MAT-1234")

                if st.button("🛑 DÉBUT RÉGLAGE"):
                    if not causes_choisies:
                        st.error("Motif obligatoire")
                    else:
                        str_raisons = " + ".join(causes_choisies)
                        if num_mat_regleur:
                            str_raisons = f"[MAT:{num_mat_regleur}] {str_raisons}"
                        insert_event(sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", str_raisons)
                        st.cache_data.clear(); st.rerun()

        elif pwd:
            st.error("⛔ Code Faux !")

    # -------------------------
    # CHEF D'ÉQUIPE
    # -------------------------
    elif role == "Chef d'Équipe":
        pwd = st.text_input("🔑 Code PIN Chef", type="password")
        st.button("🔓 Se connecter", key="btn_chef")

        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")

            objectif_actuel = get_setting("objectif_semaine", "33")
            st.subheader("🎯 Objectif Semaine")
            obj = st.number_input("Définir l'objectif :", min_value=0, value=int(objectif_actuel), step=1)
            if st.button("💾 Valider Objectif"):
                set_setting("objectif_semaine", str(int(obj)))
                st.success("Objectif enregistré ✅")
        elif pwd:
            st.error("⛔ Code Faux !")

# ==============================================================================
# 6. MAIN (DASHBOARD)
# ==============================================================================
nom_shift, shifts_passes = get_current_shift_info()
st.markdown(f"# 📌 PILOTAGE LIVE | {nom_shift}")

# Objectif
objectif = int(get_setting("objectif_semaine", "33") or "33")

# KPI très simple: nombre de FIN depuis début semaine
start_week = get_start_of_week()
df_week = df[df["DateTime"] >= start_week].copy() if not df.empty else df.copy()
nb_fin = int((df_week["Etape"] == "FIN").sum()) if not df_week.empty else 0
retard = nb_fin - objectif

c1, c2, c3 = st.columns(3)
c1.metric("✅ FIN semaine", nb_fin)
c2.metric("🎯 Objectif", objectif)
c3.metric("⏱️ Retard (FIN - Obj)", retard)

st.divider()

# KPI réglages (chef)
st.subheader("🧰 KPI Réglages (Attente / Réglage)")
df_kpi = calculer_kpi_pannes(df_week)
if df_kpi.empty:
    st.info("Aucun réglage enregistré cette semaine.")
else:
    st.dataframe(df_kpi, use_container_width=True)

st.divider()
st.subheader("📜 Derniers événements")
st.dataframe(df.sort_values("DateTime", ascending=False).head(200), use_container_width=True)
