import streamlit as st
import yaml
from scanner.scanner import audit_api
from report.report import generate_html_report
from io import BytesIO

st.set_page_config(page_title="APIChecker", page_icon="🛠", layout="centered")

st.title("🔍 APIChecker – Audit & Compliance d’API")
st.markdown("Scannez votre API et obtenez un rapport sur ses performances, sa sécurité et sa conformité RGPD.")

# --- Formulaire ---
with st.form("audit_form"):
    st.subheader("🔗 Entrez votre URL d'API")
    base_url = st.text_input("URL de base de l’API", placeholder="https://api.exemple.com")

    st.markdown("📄 *ou* importez un fichier de configuration `.yaml`")
    uploaded_file = st.file_uploader("Fichier YAML (optionnel)", type=["yaml", "yml"])

    submit_btn = st.form_submit_button("🚀 Lancer l'audit")

# --- Lancement de l’audit ---
if submit_btn:
    st.info("🔎 Audit en cours...")

    if uploaded_file:
        config = yaml.safe_load(uploaded_file)
        base_url = config.get("base_url", base_url)
        endpoints = config.get("endpoints", [])
    else:
        endpoints = ["/"]  # Audit de base si aucun endpoint fourni

    if not base_url:
        st.error("❌ Veuillez entrer une URL ou fournir un fichier de config.")
    else:
        # --- Lancer l'audit ---
        results = audit_api(base_url, endpoints)

        # --- Afficher résultats ---
        st.success("✅ Audit terminé ! Voici votre rapport.")
        st.write("### 📝 Résumé de l’audit")
        st.json(results["summary"])

        # --- Rapport HTML ---
        html_report = generate_html_report(results)

        # Affichage HTML (prévisualisation rapide)
        st.components.v1.html(html_report, height=500, scrolling=True)

        # Export PDF (optionnel)
        buffer = BytesIO()
        buffer.write(html_report.encode())
        st.download_button("📥 Télécharger le rapport (HTML)",
                           data=buffer,
                           file_name="rapport_api.html",
                           mime="text/html")
