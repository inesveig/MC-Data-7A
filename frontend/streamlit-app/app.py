import os
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

import auth
import db
import model
import utils

IMAGES_DIR = "uploaded_images"
os.makedirs(IMAGES_DIR, exist_ok=True)

ICONES = {"Sain": "✅", "Malade": "⚠️", "Incertain": "❔"}

#Page
st.set_page_config(page_title="Diagnostic Radio Thoracique", page_icon="🫁", layout="wide")
db.init_db()

if "confirm_delete_id" not in st.session_state:
    st.session_state.confirm_delete_id = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None

# AUTHENTIFICATION — bloque l'accès au reste de l'app si non connecté
if not st.session_state.access_token:
    st.title("🫁 Diagnostic IA — Radiographie Thoracique")
    st.caption("Connecte-toi pour accéder à l'application.")

    tab_login, tab_register = st.tabs(["🔐 Connexion", "📝 Inscription"])

    with tab_login:
        with st.form("login_form"):
            login_username = st.text_input("Nom d'utilisateur")
            login_password = st.text_input("Mot de passe", type="password")
            login_submitted = st.form_submit_button("Se connecter", type="primary")

        if login_submitted:
            if not login_username or not login_password:
                st.warning("Renseigne ton nom d'utilisateur et ton mot de passe.")
            else:
                success, result = auth.login(login_username, login_password)
                if success:
                    st.session_state.access_token = result["access"]
                    st.session_state.refresh_token = result["refresh"]
                    me = auth.get_me(result["access"])
                    st.session_state.user = me if me else {"username": login_username}
                    st.rerun()
                else:
                    st.error(result)

    with tab_register:
        with st.form("register_form"):
            reg_username = st.text_input("Nom d'utilisateur", key="reg_username")
            reg_email = st.text_input("Email (optionnel)", key="reg_email")
            reg_password = st.text_input("Mot de passe", type="password", key="reg_password")
            register_submitted = st.form_submit_button("Créer mon compte", type="primary")

        if register_submitted:
            if not reg_username or not reg_password:
                st.warning("Le nom d'utilisateur et le mot de passe sont obligatoires.")
            else:
                success, message = auth.register(reg_username, reg_password, reg_email)
                if success:
                    st.success(f"{message} 👉 Va dans l'onglet Connexion.")
                else:
                    st.error(message)

    st.stop()  # empêche le reste de l'app de s'exécuter tant que non connecté

# BARRE LATÉRALE — compte connecté + déconnexion
with st.sidebar:
    username_affiche = st.session_state.user.get("username") if st.session_state.user else "Utilisateur"
    st.write(f"👤 Connecté en tant que **{username_affiche}**")
    if st.button("🚪 Se déconnecter", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.user = None
        st.rerun()

st.title("🫁 Diagnostic IA — Radiographie Thoracique")
st.caption(
    "XXX vise à analyser le caractère des radios thoraciques afin d'apporter un "
    "deuxième contrôle après le regard des médecins. Notre solution vise aussi à "
    "gagner en précision et à accélérer le processus d'analyse."
)
st.error(
    "⚠️ **Avertissement** : cet outil est un projet étudiant (Mastercamp) à visée "
    "pédagogique. Ce n'est pas un dispositif médical certifié et il ne remplace en "
    "aucun cas l'avis d'un professionnel de santé. Toute décision médicale doit "
    "être validée par un médecin qualifié."
)

tab_diag, tab_hist, tab_avis, tab_kpi = st.tabs(
    ["📤 Nouveau diagnostic", "📋 Historique", "🩺 Avis médical", "📊 KPI"]
)

# TAB 1
with tab_diag:
    analysis_name = st.text_input(
        "Nom de l'analyse",
        placeholder="Ex : Patient 1",
        help="Ce nom sera affiché dans l'historique pour identifier la radio.",
    )

    uploaded_file = st.file_uploader("Téléverser une radio", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        col1, col2 = st.columns(2)

        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption=uploaded_file.name, use_container_width=True)

        with col2:
            st.subheader("Résultat du diagnostic")

            nom_renseigne = bool(analysis_name.strip())
            if not nom_renseigne:
                st.caption("⚠️ Renseigne un nom d'analyse ci-dessus pour activer le diagnostic.")

            if st.button(
                    "🔍 Lancer le diagnostic",
                    type="primary",
                    use_container_width=True,
                    disabled=not nom_renseigne,
            ):
                with st.spinner("Analyse en cours..."):
                    ext = uploaded_file.name.split(".")[-1]
                    unique_name = f"{uuid.uuid4().hex}.{ext}"
                    image_path = os.path.join(IMAGES_DIR, unique_name)
                    image.convert("RGB").save(image_path)

                    diagnosis, confidence = model.predict_diagnosis(image_path)
                    heatmap_path = model.generate_heatmap(image_path)

                    db.save_diagnostic(
                        uploaded_file.name, image_path, diagnosis, confidence,
                        analysis_name.strip(), heatmap_path,
                    )

                if diagnosis == "Sain":
                    st.success(f"✅ Résultat : **{diagnosis}**")
                elif diagnosis == "Malade":
                    st.error(f"⚠️ Résultat : **{diagnosis}**")
                else:
                    st.warning(
                        f"❔ Résultat : **{diagnosis}** — confiance insuffisante "
                        f"(seuil : {model.UNCERTAINTY_THRESHOLD * 100:.0f} %). "
                        "Vérification manuelle recommandée."
                    )

                st.metric("Confiance du modèle", f"{confidence * 100:.1f} %")
                st.progress(confidence)

                if heatmap_path:
                    st.image(heatmap_path, caption="Carte de chaleur (zones d'intérêt)")
                else:
                    st.caption("ℹ️ Carte de chaleur non disponible avec le modèle actuel.")

                st.caption("Le résultat a été enregistré dans l'historique.")
    else:
        st.info("Téléverse une image pour commencer.")

#TAB 2
with tab_hist:
    st.subheader("Historique des diagnostics")

    all_rows = db.get_all_diagnostics()

    col_search, col_filter, col_export = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("🔎 Rechercher par nom", placeholder="Tape un nom d'analyse...")
    with col_filter:
        filtre = st.selectbox("Filtrer par résultat", ["Tous", "Sain", "Malade", "Incertain"])
    with col_export:
        st.write("")  # alignement vertical avec les autres champs
        csv_data = utils.export_diagnostics_to_csv(all_rows)
        st.download_button(
            "⬇️ Exporter en CSV",
            data=csv_data,
            file_name="historique_diagnostics.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if not all_rows:
        st.info("Aucun diagnostic enregistré pour le moment.")
    else:
        filtered_rows = []
        for row in all_rows:
            display_name = row["analysis_name"] if row["analysis_name"] else row["filename"]
            if filtre != "Tous" and row["diagnosis"] != filtre:
                continue
            if search_query and search_query.lower() not in display_name.lower():
                continue
            filtered_rows.append(row)

        if not filtered_rows:
            st.info("Aucun résultat ne correspond à ta recherche.")

        for row in filtered_rows:
            diag_id = row["id"]
            display_name = row["analysis_name"] if row["analysis_name"] else row["filename"]
            date_affichee = row["created_at"][:19].replace("T", " ")
            icone = ICONES.get(row["diagnosis"], "❔")

            with st.expander(f"{icone} {display_name} — {row['diagnosis']} — {date_affichee}"):
                col1, col2, col3 = st.columns([1, 2, 1])

                with col1:
                    if row["image_path"] and os.path.exists(row["image_path"]):
                        st.image(row["image_path"], width=150, caption="Radio")
                    else:
                        st.caption("Image introuvable")
                    if row["heatmap_path"] and os.path.exists(row["heatmap_path"]):
                        st.image(row["heatmap_path"], width=150, caption="Heatmap")

                with col2:
                    st.write(f"**Nom de l'analyse :** {display_name}")
                    st.write(f"**Fichier original :** {row['filename']}")
                    st.write(f"**Diagnostic IA :** {row['diagnosis']}")
                    st.write(f"**Confiance :** {row['confidence'] * 100:.1f} %")
                    st.write(f"**Date :** {date_affichee}")

                    if row["doctor_diagnosis"]:
                        st.divider()
                        avis = row["doctor_diagnosis"]
                        if row["doctor_notes"]:
                            avis += f" ({row['doctor_notes']})"
                        st.write(f"**Avis médecin :** {avis}")

                        statut, pourcentage = utils.compute_concordance(
                            row["diagnosis"], row["doctor_diagnosis"]
                        )
                        if statut == "Concordant":
                            st.success(f"✅ {statut} — {pourcentage} % de similitude")
                        elif statut == "Discordant":
                            st.error(f"❌ {statut} — {pourcentage} % de similitude")
                        else:
                            st.warning(f"❔ {statut}")
                    else:
                        st.caption("Aucun avis médical enregistré pour cette analyse.")

                with col3:
                    if st.session_state.confirm_delete_id == diag_id:
                        st.warning("Confirmer la suppression ?")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("✅ Oui", key=f"yes_{diag_id}", use_container_width=True):
                            db.delete_diagnostic(diag_id)
                            if row["image_path"] and os.path.exists(row["image_path"]):
                                os.remove(row["image_path"])
                            if row["heatmap_path"] and os.path.exists(row["heatmap_path"]):
                                os.remove(row["heatmap_path"])
                            st.session_state.confirm_delete_id = None
                            st.rerun()
                        if cc2.button("❌ Non", key=f"no_{diag_id}", use_container_width=True):
                            st.session_state.confirm_delete_id = None
                            st.rerun()
                    else:
                        if st.button("🗑️ Supprimer", key=f"del_{diag_id}", use_container_width=True):
                            st.session_state.confirm_delete_id = diag_id
                            st.rerun()

# TAB 3
with tab_avis:
    st.subheader("🩺 Saisir l'avis d'un médecin")
    st.caption(
        "Permet de comparer le diagnostic de l'IA à l'avis réel d'un professionnel "
        "de santé, pour suivre la fiabilité du modèle dans le temps."
    )

    rows = db.get_all_diagnostics()

    if not rows:
        st.info("Aucune analyse enregistrée pour le moment.")
    else:
        afficher_tout = st.checkbox("Afficher aussi les analyses ayant déjà un avis (pour le modifier)")
        choix_rows = rows if afficher_tout else [r for r in rows if not r["doctor_diagnosis"]]

        if not choix_rows:
            st.success("Toutes les analyses ont déjà un avis médical associé ✅")
        else:
            options = {
                f"{(r['analysis_name'] or r['filename'])} — {r['created_at'][:19].replace('T', ' ')}": r["id"]
                for r in choix_rows
            }
            choix_label = st.selectbox("Sélectionne une analyse", list(options.keys()))
            selected_id = options[choix_label]
            selected_row = next(r for r in choix_rows if r["id"] == selected_id)

            col1, col2 = st.columns(2)

            with col1:
                if selected_row["image_path"] and os.path.exists(selected_row["image_path"]):
                    st.image(selected_row["image_path"], caption="Radio analysée", use_container_width=True)
                st.write(
                    f"**Diagnostic IA :** {selected_row['diagnosis']} "
                    f"({selected_row['confidence'] * 100:.1f} %)"
                )
                if selected_row["doctor_diagnosis"]:
                    st.caption(f"Avis déjà enregistré : {selected_row['doctor_diagnosis']}")

            with col2:
                doctor_diagnosis = st.radio(
                    "Diagnostic du médecin",
                    ["Sain", "Malade", "Autre"],
                    horizontal=True,
                )

                precision = ""
                if doctor_diagnosis == "Autre":
                    precision = st.text_input("Précise le diagnostic (ex : nom de la pathologie)")

                notes = st.text_area("Notes complémentaires (optionnel)")

                if doctor_diagnosis == "Autre" and precision and notes:
                    doctor_notes_final = f"{precision} — {notes}"
                elif doctor_diagnosis == "Autre":
                    doctor_notes_final = precision
                else:
                    doctor_notes_final = notes

                if st.button("💾 Enregistrer l'avis médical", type="primary"):
                    db.update_doctor_diagnosis(selected_id, doctor_diagnosis, doctor_notes_final)
                    st.success("Avis médical enregistré ! Retrouve la comparaison dans l'Historique.")
                    st.rerun()

# TAB 4
with tab_kpi:
    st.subheader("📊 Indicateurs clés")

    stats = db.get_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total analyses", stats["total"])
    c2.metric("Sain", stats["sain"])
    c3.metric("Malade", stats["malade"])
    c4.metric("Incertain", stats["incertain"])

    if stats["total"] > 0:
        chart_data = pd.DataFrame({
            "Catégorie": ["Sain", "Malade", "Incertain"],
            "Nombre": [stats["sain"], stats["malade"], stats["incertain"]],
        })
        chart_data = chart_data[chart_data["Nombre"] > 0]  # masque les tranches à 0

        fig = px.pie(
            chart_data,
            names="Catégorie",
            values="Nombre",
            color="Catégorie",
            color_discrete_map={"Sain": "#2ecc71", "Malade": "#e74c3c", "Incertain": "#f39c12"},
        )
        fig.update_traces(textinfo="label+percent+value")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas encore de données pour générer des statistiques.")

    st.divider()
    st.subheader("🩺 Concordance avec l'avis médical")

    rows = db.get_all_diagnostics()
    rows_avec_avis = [r for r in rows if r["doctor_diagnosis"]]

    if rows_avec_avis:
        concordants = 0
        for r in rows_avec_avis:
            statut, _ = utils.compute_concordance(r["diagnosis"], r["doctor_diagnosis"])
            if statut == "Concordant":
                concordants += 1
        taux = concordants / len(rows_avec_avis) * 100
        st.metric(
            "Taux de concordance IA / médecin",
            f"{taux:.0f} %",
            help=f"Calculé sur {len(rows_avec_avis)} analyse(s) ayant un avis médical.",
        )
    else:
        st.info("Aucun avis médical enregistré pour le moment.")