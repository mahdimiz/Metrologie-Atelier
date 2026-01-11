import streamlit as st

st.set_page_config(page_title="Test Supabase", layout="wide")

st.title("🧪 Test connexion Supabase")

conn = st.connection("supabase_db", type="sql")

st.write("Connexion chargée")

try:
    df = conn.query("select now() as serveur_time", ttl=0)
    st.success("✅ Connexion Supabase OK")
    st.dataframe(df)
except Exception as e:
    st.error("❌ Connexion Supabase KO")
    st.exception(e)
    st.stop()

try:
    df2 = conn.query("select count(*) as total from public.events", ttl=0)
    st.success("✅ Table events accessible")
    st.dataframe(df2)
except Exception as e:
    st.error("❌ Problème table events")
    st.exception(e)
    st.stop()
