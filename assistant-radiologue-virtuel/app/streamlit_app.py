"""
Interface Streamlit — Assistant Radiologue Virtuel
Upload d'une radio → affichage du résultat JSON + warning
"""

import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000/predict"

st.set_page_config(
    page_title="Assistant Radiologue Virtuel",
    page_icon="🫁",
    layout="centered",
)

st.title("🫁 Assistant Radiologue Virtuel")
st.caption("Prototype pédagogique — EFREI Mastercamp 2025-2026")

st.warning(
    "⚠️ **Position non clinique.** Ce prototype ne pose aucun diagnostic. "
    "Toute sortie est expérimentale et doit être vérifiée par un professionnel qualifié.",
    icon="⚠️",
)

uploaded_file = st.file_uploader(
    "Charger une radiographie thoracique frontale",
    type=["png", "jpg", "jpeg"],
)

if uploaded_file is not None:
    st.image(uploaded_file, caption="Radiographie chargée", use_column_width=True)

    if st.button("Lancer l'analyse", type="primary"):
        with st.spinner("Analyse en cours…"):
            try:
                response = requests.post(
                    API_URL,
                    files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                result = data["result"]
                latency = data["latency_ms"]

            except requests.exceptions.ConnectionError:
                st.error("Impossible de joindre l'API. Lancez d'abord : `uvicorn api.main:app --reload`")
                st.stop()
            except Exception as e:
                st.error(f"Erreur : {e}")
                st.stop()

        st.success(f"Analyse terminée en {latency} ms")

        col1, col2, col3 = st.columns(3)
        col1.metric("Classe prédite", result["predicted_class"])
        col2.metric("Confiance", f"{result['confidence']:.0%}")
        col3.metric("Qualité image", result["image_quality"])

        st.subheader("Observations visuelles")
        for obs in result["visual_evidence"]:
            st.write(f"• {obs}")

        st.subheader("Justification")
        st.write(result["justification"])

        st.subheader("Limites identifiées")
        for lim in result["limitations"]:
            st.write(f"• {lim}")

        st.error(f"⚠️ {result['warning']}")

        with st.expander("JSON brut"):
            st.json(result)
