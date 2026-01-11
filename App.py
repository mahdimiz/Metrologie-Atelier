import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Suivi Atelier - Démo", layout="wide")

MOT_DE_PASSE_REGLEUR = "1234"
MOT_DE_PASSE_CHEF = "0000"

conn = st.connection("supabase_db", type="sql")

def heure_fr():
    return datetime.utcnow() + timedelta(hours=1)

# ============================================================
# SUPABASE - ÉCRITURE
# ============================================================
def log_event(poste, se_unique, msn, etape, info=""):
    conn.query("""
        INSERT INTO events (ts, poste, se_unique, msn, etape, info_sup)
        VALUES (now(), :poste, :se, :msn, :etape, :info)
    """, params={
        "poste": poste,
        "se": se_unique,
        "msn": msn,
        "etape": etape,
        "info": info
    })

# ============================================================
# SUPABASE - LECTURE LIVE
# ============================================================
@st.cache_data(ttl=2)
def read_live():
    return conn.query("""
        SELECT ts, poste, se_unique, msn, etape, info_sup
        FROM events
        ORDER BY ts DESC
        LIMIT 200
    """)

# ============================================================
# KPI CHEF
# ============================================================
def debut_semaine():
    now = heure_fr()
    wd = now.weekday()
    start = now.replace(hour=6, minute=30, second=0, microsecond=0) - timedelta(days=wd)
    if wd == 0 and now.time() < time(6,30):
        start -= timedelta(days=7)
    return start

def calcul_kpi(df):
    rows = []
    for poste in df["poste"].unique():
        dfp = df[df["poste"] == poste].sort_values("ts")
        cycle = {}
        for _, r in dfp.iterrows():
            if r["etape"] == "APPEL_REGLAGE":
                cycle = {"appel": r["ts"], "cause": r["info_sup"], "poste": poste, "msn": r["msn"]}
            elif r["etape"] == "INCIDENT_EN_COURS" and "appel" in cycle:
                cycle["debut"] = r["ts"]
            elif r["etape"] == "INCIDENT_FINI" and "debut" in cycle:
                attente = (cycle["debut"] - cycle["appel"]).total_seconds()/60
                reglage = (r["ts"] - cycle["debut"]).total_seconds()/60
                rows.append({
                    "Poste": poste,
                    "MSN": cycle["msn"],
                    "Cause": cycle["cause"],
                    "Attente (min)": int(attente),
                    "Réglage (min)": int(reglage),
                    "Total (min)": int(attente + reglage)
                })
                cycle = {}
    return pd.DataFrame(rows)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title("🎛️ Commandes")
    role = st.selectbox("Rôle", ["Opérateur", "Régleur", "Chef"])

# ============================================================
# OPÉRATEUR
# ============================================================
if role == "Opérateur":
    st.header("👷 Opérateur")
    poste = st.selectbox("Poste", ["Poste_01", "Poste_02", "Poste_03"])
    msn = st.text_input("MSN", "123")

    if st.button("🟢 DÉMARRER MESURE"):
        log_event(poste, f"S-SE-MSN-{msn}", f"MSN-{msn}", "PHASE_SETUP")
        st.success("Mesure démarrée")

    if st.button("🚨 SONNER RÉGLEUR"):
        log_event(poste, f"S-SE-MSN-{msn}", f"MSN-{msn}", "APPEL_REGLAGE", "Problème réglage")
        st.error("Régleur appelé")

# ============================================================
# RÉGLEUR
# ============================================================
elif role == "Régleur":
    pwd = st.text_input("Code régleur", type="password")
    if pwd == MOT_DE_PASSE_REGLEUR:
        st.header("🔧 Régleur")
        poste = st.selectbox("Poste", ["Poste_01", "Poste_02", "Poste_03"])

        if st.button("▶️ DÉBUT RÉGLAGE"):
            log_event(poste, "MAINT", "SYS", "INCIDENT_EN_COURS", "Début réglage")
            st.warning("Réglage en cours")

        if st.button("✅ FIN RÉGLAGE"):
            log_event(poste, "MAINT", "SYS", "INCIDENT_FINI", "Fin réglage")
            st.success("Réglage terminé")
    else:
        st.error("Code incorrect")

# ============================================================
# CHEF
# ============================================================
elif role == "Chef":
    pwd = st.text_input("Code chef", type="password")
    if pwd == MOT_DE_PASSE_CHEF:
        st.header("👨‍🏭 Chef d’équipe")

        if st.button("📊 GÉNÉRER KPI SEMAINE"):
            start = debut_semaine()
            df = conn.query("""
                SELECT ts, poste, msn, etape, info_sup
                FROM events
                WHERE ts >= :start
                ORDER BY ts
            """, params={"start": start})

            kpi = calcul_kpi(df)
            st.dataframe(kpi)

            csv = kpi.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Télécharger CSV", csv, "KPI_Semaine.csv")
    else:
        st.error("Code incorrect")

# ============================================================
# LIVE
# ============================================================
st.divider()
st.subheader("📡 Derniers événements (LIVE)")
st.dataframe(read_live())
