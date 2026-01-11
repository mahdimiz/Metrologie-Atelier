import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import random

# ==============================================================================
# 1) CONFIG
# ==============================================================================
st.set_page_config(page_title="Suivi V77", layout="wide", page_icon="🔒")

MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

def get_heure_fr():
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
# 3) SUPABASE (Streamlit SQL Connection)
# ==============================================================================
def get_db_conn():
    """
    Dans Streamlit Cloud > Secrets:
    [connections.supabase_db]
    url = "postgresql://USER:PASSWORD@HOST:PORT/postgres?sslmode=require"
    """
    try:
        return st.connection("supabase_db", type="sql")
    except Exception:
        return None

def tables_ready(conn) -> bool:
    """On ne crée PAS les tables ici. On vérifie juste qu'elles existent."""
    try:
        conn.query("select 1 from public.events limit 1", ttl=0)
        conn.query("select 1 from public.pannes limit 1", ttl=0)
        conn.query("select 1 from public.consignes limit 1", ttl=0)
        conn.query("select 1 from public.settings limit 1", ttl=0)
        return True
    except Exception:
        return False

@st.cache_data(ttl=2)
@st.cache_data(ttl=2)
def read_events_live(limit=2000):
    conn = get_db_conn()
    if conn is None or not tables_ready(conn):
        return pd.DataFrame(columns=[
            "Date", "Heure", "Poste", "SE_Unique",
            "MSN_Display", "Etape", "Info_Sup", "DateTime"
        ])

    df = conn.query(f"""
        select
          date as "Date",
          heure as "Heure",
          poste as "Poste",
          se_unique as "SE_Unique",
          msn as "MSN_Display",
          etape as "Etape",
          info_sup as "Info_Sup",
          ts as "ts"
        from public.events
        order by ts desc
        limit {int(limit)}
    """, ttl=0)

    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "Date", "Heure", "Poste", "SE_Unique",
            "MSN_Display", "Etape", "Info_Sup", "DateTime"
        ])

    df["DateTime"] = pd.to_datetime(
        df["Date"].astype(str) + " " + df["Heure"].astype(str),
        errors="coerce"
    )
    return df

@st.cache_data(ttl=10)
def read_consignes():
    conn = get_db_conn()
    if conn is None or not tables_ready(conn):
        return pd.DataFrame(columns=["Type", "MSN", "Poste", "Emplacement"])

    df = conn.query("""
        select
          type as "Type",
          msn as "MSN",
          poste as "Poste",
          emplacement as "Emplacement"
        from public.consignes
    """)
    if df is None or df.empty:
        return pd.DataFrame(columns=["Type", "MSN", "Poste", "Emplacement"])
    return df

@st.cache_data(ttl=10)
def read_pannes():
    conn = get_db_conn()
    if conn is None or not tables_ready(conn):
        # fallback défaut
        data_defaut = [
            ["GAUCHE", "🔧 Capot Gauche (ST1)"], ["GAUCHE", "🔧 PAF"], ["GAUCHE", "🔧 Cornière SSAV Gauche"],
            ["DROIT", "🔧 Capot Droit (ST2)"], ["DROIT", "🔧 Cornière SSAV Droite"],
            ["GENERIC", "⚠️ SO3 - Pipes Arrière"]
        ]
        return pd.DataFrame(data_defaut, columns=["Zone", "Nom"])

    df = conn.query("""
        select
          zone as "Zone",
          nom as "Nom"
        from public.pannes
    """)
    if df is None or df.empty:
        data_defaut = [
            ["GAUCHE", "🔧 Capot Gauche (ST1)"], ["GAUCHE", "🔧 PAF"], ["GAUCHE", "🔧 Cornière SSAV Gauche"],
            ["DROIT", "🔧 Capot Droit (ST2)"], ["DROIT", "🔧 Cornière SSAV Droite"],
            ["GENERIC", "⚠️ SO3 - Pipes Arrière"]
        ]
        return pd.DataFrame(data_defaut, columns=["Zone", "Nom"])
    return df

def append_event(poste, se_unique, msn_display, etape, info_sup=""):
    conn = get_db_conn()
    if conn is None or not tables_ready(conn):
        st.error("❌ Supabase pas prêt (Secrets ou tables).")
        return

    now = get_heure_fr()
    payload = {
        "date": now.strftime("%Y-%m-%d"),
        "heure": now.strftime("%H:%M:%S"),
        "poste": poste,
        "se_unique": se_unique,
        "msn_display": msn_display,
        "etape": etape,
        "info_sup": info_sup or ""
    }
    # INSERT simple
    conn.query("""
        insert into public.events (date, heure, poste, se_unique, msn_display, etape, info_sup)
        values (:date, :heure, :poste, :se_unique, :msn_display, :etape, :info_sup)
    """, params=payload, ttl=0)

    # vide le cache live pour refresh immédiat
    read_events_live.clear()

def get_setting(key, default_value=""):
    conn = get_db_conn()
    if conn is None or not tables_ready(conn):
        return default_value
    df = conn.query("select v from public.settings where k = :k limit 1", params={"k": key}, ttl=0)
    if df is None or df.empty:
        return default_value
    return str(df.iloc[0]["v"])

def set_setting(key, value):
    conn = get_db_conn()
    if conn is None or not tables_ready(conn):
        st.error("❌ Supabase pas prêt (Secrets ou tables).")
        return
    conn.query("""
        insert into public.settings (k, v)
        values (:k, :v)
        on conflict (k) do update set v = excluded.v
    """, params={"k": key, "v": str(value)}, ttl=0)

# ==============================================================================
# 4) CHARGEMENT DATA (Supabase)
# ==============================================================================
df = read_events_live(limit=2000)
df_consignes = read_consignes()
df_pannes = read_pannes()

def get_liste_pannes(zone):
    if df_pannes is None or df_pannes.empty:
        return []
    return df_pannes[df_pannes["Zone"] == zone]["Nom"].tolist()

REGLAGES_GAUCHE = get_liste_pannes("GAUCHE")
REGLAGES_DROIT = get_liste_pannes("DROIT")
REGLAGES_GENERIC = get_liste_pannes("GENERIC")

# ==============================================================================
# 5) KPI / ANALYSE (ton code)
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
                current_cycle = {'Poste': poste, 'MSN': msn_clean, 'Cause': row.get('Info_Sup', ''), 'Heure_Appel': row['DateTime'], 'Heure_Debut': None, 'Heure_Fin': None}
            elif etape == 'INCIDENT_EN_COURS':
                if not current_cycle:
                    current_cycle = {'Poste': poste, 'MSN': msn_clean, 'Cause': row.get('Info_Sup', ''), 'Heure_Appel': row['DateTime'], 'Heure_Debut': row['DateTime'], 'Heure_Fin': None}
                else:
                    current_cycle['Heure_Debut'] = row['DateTime']
            elif etape == 'INCIDENT_FINI':
                if current_cycle and current_cycle.get('Heure_Debut') is not None:
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

def deviner_contexte_poste(poste_choisi, dataframe):
    if dataframe.empty:
        return "Inconnu"
    df_clean = dataframe[~dataframe["Etape"].astype(str).str.contains("INCIDENT|APPEL", na=False)]
    actions_poste = df_clean[df_clean["Poste"] == poste_choisi].sort_values("DateTime")
    if actions_poste.empty:
        return "Inconnu"
    derniere_etape = actions_poste.iloc[-1]["Etape"]
    if derniere_etape in ["PHASE_SETUP", "STATION_BRAS", "STATION_TRK1"]:
        return "GAUCHE"
    elif derniere_etape in ["STATION_TRK2", "PHASE_RAPPORT"]:
        return "DROIT"
    return "GENERIC"

# ==============================================================================
# 6) SIDEBAR (ton app)
# ==============================================================================
with st.sidebar:
    st.title("🎛️ COMMANDES")
    st.caption(f"Heure : {get_heure_fr().strftime('%H:%M')}")
    st.divider()

    role = st.selectbox("👤 Qui êtes-vous ?", ["Opérateur", "Régleur", "Chef d'Équipe", "RDZ (Responsable)"])
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
                            append_event(sim_poste, se_unique_en_cours, f"MSN-{msn_en_cours}", "APPEL_REGLAGE", str_raisons)
                            st.rerun()

                st.markdown("---")
                sim_msn = msn_en_cours
                nom_se_complet = se_unique_en_cours

                c1, c2 = st.columns(2)
                if c1.button("🔵 Bras"):
                    append_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_BRAS")
                    st.rerun()

                if c2.button("🔵 Trk 1"):
                    append_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK1")
                    st.rerun()

                if st.button("🔵 Track 2", use_container_width=True):
                    append_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "STATION_TRK2")
                    st.rerun()

                if st.button("🟣 Fin / Démont.", use_container_width=True):
                    append_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_DESETUP")
                    st.rerun()

                if st.button("✅ LIBÉRER (FINI)", type="primary", use_container_width=True):
                    append_event(sim_poste, "Aucun", "Aucun", "FIN")
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
                    append_event(sim_poste, nom_se_complet, f"MSN-{sim_msn}", "PHASE_SETUP")
                    st.rerun()

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
                if start_time_evt is not None:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.error(f"⏳ Attente depuis : {duree} min")

                if st.button("✅ ACCEPTER & DÉMARRER", type="primary", use_container_width=True):
                    append_event(sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", info_sup)
                    st.rerun()

            elif etat_poste == "INTERVENTION_EN_COURS":
                st.info(f"🔧 En cours : {info_sup}")
                if start_time_evt is not None:
                    duree = int((get_heure_fr() - start_time_evt).total_seconds() / 60)
                    st.warning(f"⏱️ Temps passé : {duree} min")

                if st.button("✅ FIN RÉGLAGE (Reprise)", type="primary", use_container_width=True):
                    append_event(sim_poste, "MAINTENANCE", "System", "INCIDENT_FINI", "Reprise")
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
                        str_raisons = " + ".join(causes_choisies)
                        if num_mat_regleur:
                            str_raisons = f"[MAT:{num_mat_regleur}] {str_raisons}"
                        append_event(sim_poste, "MAINTENANCE", "System", "INCIDENT_EN_COURS", str_raisons)
                        st.rerun()

        elif pwd:
            st.error("⛔ Code Faux !")

    # -------------------------
    # CHEF
    # -------------------------
    elif role == "Chef d'Équipe":
        pwd = st.text_input("🔑 Code PIN Chef", type="password")
        st.button("🔓 Se connecter", key="btn_chef")

        if pwd == MOT_DE_PASSE_CHEF:
            st.success("Accès autorisé")

            st.subheader("🎯 Objectif Semaine")
            obj_actuel = get_setting("objectif_semaine", "33")

            colA, colB = st.columns([2,1])
            with colA:
                objectif = st.number_input("Définir l'objectif :", min_value=0, max_value=500, value=int(obj_actuel))
            with colB:
                if st.button("💾 Valider Objectif"):
                    set_setting("objectif_semaine", objectif)
                    st.success("✅ Objectif enregistré")
                    st.rerun()

            st.divider()
            st.subheader("📊 KPI Réglages / Attentes (Semaine)")

            start_week = get_start_of_week()
            df_week = df[df["DateTime"] >= start_week].copy() if not df.empty else pd.DataFrame()

            kpi = calculer_kpi_pannes(df_week)
            if kpi.empty:
                st.info("Aucun réglage enregistré cette semaine.")
            else:
                st.dataframe(kpi, use_container_width=True)

        elif pwd:
            st.error("⛔ Code Faux !")

    # RDZ (optionnel)
    else:
        st.info("Mode RDZ: à compléter si besoin (mêmes données Supabase).")

# ==============================================================================
# 7) MAIN (Dashboard simple / rapide)
# ==============================================================================
shift_name, shifts_passes = get_current_shift_info()
st.markdown(f"# 📍 PILOTAGE LIVE | {shift_name}")

# Objectif
obj = get_setting("objectif_semaine", "33")
st.caption(f"Objectif semaine (chef): **{obj}**")

# Statuts postes
cols = st.columns(3)
for i, poste in enumerate(["Poste_01", "Poste_02", "Poste_03"]):
    with cols[i]:
        if df.empty:
            st.metric(poste, "—")
        else:
            dfp = df[df["Poste"] == poste].sort_values("DateTime")
            if dfp.empty:
                st.metric(poste, "Libre")
            else:
                last = dfp.iloc[-1]
                etape = str(last["Etape"])
                msn = str(last["MSN_Display"]).replace("MSN-", "")
                if etape == "FIN":
                    st.metric(poste, "Libre")
                elif etape == "APPEL_REGLAGE":
                    st.metric(poste, f"APPEL ({msn})")
                elif etape == "INCIDENT_EN_COURS":
                    st.metric(poste, "MAINTENANCE")
                else:
                    st.metric(poste, f"En cours ({msn})")

st.divider()
st.subheader("🧾 Derniers événements")
st.dataframe(df.sort_values("DateTime").tail(30), use_container_width=True)
