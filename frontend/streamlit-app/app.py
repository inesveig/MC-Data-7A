import base64
import io

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

import api
import auth
import utils

ICONES = {"Sain": "✅", "Malade": "⚠️", "Incertain": "❔"}

# Page
st.set_page_config(page_title="Diagnostic Radio Thoracique", page_icon="🫁", layout="wide")

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

    st.stop()  # empêche le reste de l'app tant que non connecté

TOKEN = st.session_state.access_token

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
    "Cet outil analyse des radiographies thoraciques pour apporter un second "
    "regard après celui des médecins, et gagner en rapidité d'analyse."
)
st.error(
    "⚠️ **Avertissement** : projet étudiant (Mastercamp) à visée pédagogique. "
    "Ce n'est pas un dispositif médical certifié et il ne remplace en aucun cas "
    "l'avis d'un professionnel de santé. Toute décision médicale doit être "
    "validée par un médecin qualifié."
)


@st.cache_data(ttl=5, show_spinner=False)
def _load_history(token: str):
    ok, rows = api.list_analyses(token)
    return rows if ok else None


tab_diag, tab_hist, tab_avis, tab_kpi = st.tabs(
    ["📤 Nouveau diagnostic", "📋 Historique", "🩺 Avis médical", "📊 KPI"]
)

# ---------------------------------------------------------------- TAB 1
with tab_diag:
    analysis_name = st.text_input(
        "Nom de l'analyse",
        placeholder="Ex : Patient 1",
        help="Ce nom sera affiché dans l'historique pour identifier la radio.",
    )
    uploaded_file = st.file_uploader(
        "Téléverser une radio", type=["jpg", "jpeg", "png", "dcm", "dicom"]
    )

    if uploaded_file is not None:
        col1, col2 = st.columns(2)
        with col1:
            if uploaded_file.name.lower().endswith((".dcm", ".dicom")):
                st.info("📄 Fichier DICOM — l'aperçu s'affichera après l'analyse.")
            else:
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)

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
                with st.spinner("Analyse en cours (Django → IA)..."):
                    ok, data = api.analyze(
                        TOKEN,
                        uploaded_file.getvalue(),
                        uploaded_file.name,
                        analysis_name.strip(),
                    )

                if not ok:
                    st.error(data)
                else:
                    _load_history.clear()
                    diagnosis = data.get("diagnosis", "Incertain")
                    confidence = data.get("confidence") or 0.0
                    result = data.get("result") or {}

                    if diagnosis == "Sain":
                        st.success(f"✅ Résultat : **{diagnosis}**")
                    elif diagnosis == "Malade":
                        st.error(f"⚠️ Résultat : **{diagnosis}**")
                    else:
                        st.warning(
                            f"❔ Résultat : **{diagnosis}** — confiance insuffisante. "
                            "Vérification manuelle recommandée."
                        )

                    st.metric("Confiance du modèle", f"{confidence * 100:.1f} %")
                    st.progress(min(max(confidence, 0.0), 1.0))
                    st.metric("Gravité estimée", f"{data.get('severity', 0)} / 10")
                    if data.get("region"):
                        st.write(f"**Région :** {data['region']}")

                    findings = result.get("findings") or []
                    if findings:
                        st.write("**Observations :** " + ", ".join(findings))
                    if result.get("explanation"):
                        st.info(result["explanation"])
                    if result.get("recommendation"):
                        st.write(f"**Conduite à tenir :** {result['recommendation']}")

                    # Image normalisée + cercle d'anomalie
                    png_b64 = data.get("image_png_base64")
                    if png_b64:
                        img = Image.open(io.BytesIO(base64.b64decode(png_b64)))
                        img = utils.draw_circle(img, result.get("circle"))
                        st.image(img, caption="Radio analysée (zone d'anomalie cerclée)")

                    st.caption("✔️ Enregistré dans l'historique (backend Django).")
    else:
        st.info("Téléverse une image pour commencer.")

# ---------------------------------------------------------------- TAB 2
with tab_hist:
    st.subheader("Historique des diagnostics")
    all_rows = _load_history(TOKEN)

    if all_rows is None:
        st.error("Impossible de charger l'historique depuis Django.")
        all_rows = []

    col_search, col_filter, col_export = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("🔎 Rechercher par nom", placeholder="Tape un nom d'analyse...")
    with col_filter:
        filtre = st.selectbox("Filtrer par résultat", ["Tous", "Sain", "Malade", "Incertain"])
    with col_export:
        st.write("")
        st.download_button(
            "⬇️ Exporter en CSV",
            data=utils.export_diagnostics_to_csv(all_rows),
            file_name="historique_diagnostics.csv",
            mime="text/csv",
            use_container_width=True,
        )

    if not all_rows:
        st.info("Aucun diagnostic enregistré pour le moment.")
    else:
        filtered_rows = []
        for row in all_rows:
            display_name = row.get("analysis_name") or row.get("filename", "")
            if filtre != "Tous" and row.get("diagnosis") != filtre:
                continue
            if search_query and search_query.lower() not in display_name.lower():
                continue
            filtered_rows.append(row)

        if not filtered_rows:
            st.info("Aucun résultat ne correspond à ta recherche.")

        for row in filtered_rows:
            diag_id = row["id"]
            display_name = row.get("analysis_name") or row.get("filename", "")
            date_affichee = (row.get("created_at") or "")[:19].replace("T", " ")
            diagnosis = row.get("diagnosis", "Incertain")
            icone = ICONES.get(diagnosis, "❔")

            with st.expander(f"{icone} {display_name} — {diagnosis} — {date_affichee}"):
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if row.get("image_url"):
                        st.image(row["image_url"], width=160, caption="Radio")
                    else:
                        st.caption("Image indisponible")

                with col2:
                    confidence = row.get("confidence") or 0.0
                    st.write(f"**Nom de l'analyse :** {display_name}")
                    st.write(f"**Fichier original :** {row.get('filename', '')}")
                    st.write(f"**Diagnostic IA :** {diagnosis}")
                    st.write(f"**Confiance :** {confidence * 100:.1f} %")
                    st.write(f"**Gravité :** {row.get('severity', 0)} / 10")
                    if row.get("region"):
                        st.write(f"**Région :** {row['region']}")
                    if (row.get("result") or {}).get("explanation"):
                        st.caption(row["result"]["explanation"])
                    st.write(f"**Date :** {date_affichee}")

                    if row.get("doctor_diagnosis"):
                        st.divider()
                        avis = row["doctor_diagnosis"]
                        if row.get("doctor_notes"):
                            avis += f" ({row['doctor_notes']})"
                        st.write(f"**Avis médecin :** {avis}")
                        statut = row.get("concordance_status")
                        pct = row.get("concordance_pct")
                        if statut == "Concordant":
                            st.success(f"✅ {statut} — {pct} % de similitude")
                        elif statut == "Discordant":
                            st.error(f"❌ {statut} — {pct} % de similitude")
                        elif statut:
                            st.warning(f"❔ {statut}")
                    else:
                        st.caption("Aucun avis médical enregistré pour cette analyse.")

                with col3:
                    if st.session_state.confirm_delete_id == diag_id:
                        st.warning("Confirmer la suppression ?")
                        cc1, cc2 = st.columns(2)
                        if cc1.button("✅ Oui", key=f"yes_{diag_id}", use_container_width=True):
                            ok, _ = api.delete_analysis(TOKEN, diag_id)
                            st.session_state.confirm_delete_id = None
                            if ok:
                                _load_history.clear()
                            st.rerun()
                        if cc2.button("❌ Non", key=f"no_{diag_id}", use_container_width=True):
                            st.session_state.confirm_delete_id = None
                            st.rerun()
                    else:
                        if st.button("🗑️ Supprimer", key=f"del_{diag_id}", use_container_width=True):
                            st.session_state.confirm_delete_id = diag_id
                            st.rerun()

# ---------------------------------------------------------------- TAB 3
with tab_avis:
    st.subheader("🩺 Saisir l'avis d'un médecin")
    st.caption(
        "Compare le diagnostic de l'IA à l'avis réel d'un professionnel de santé "
        "pour suivre la fiabilité du modèle dans le temps."
    )
    rows = _load_history(TOKEN) or []

    if not rows:
        st.info("Aucune analyse enregistrée pour le moment.")
    else:
        afficher_tout = st.checkbox("Afficher aussi les analyses ayant déjà un avis (pour le modifier)")
        choix_rows = rows if afficher_tout else [r for r in rows if not r.get("doctor_diagnosis")]

        if not choix_rows:
            st.success("Toutes les analyses ont déjà un avis médical associé ✅")
        else:
            options = {
                f"{(r.get('analysis_name') or r.get('filename'))} — {(r.get('created_at') or '')[:19].replace('T', ' ')}": r["id"]
                for r in choix_rows
            }
            choix_label = st.selectbox("Sélectionne une analyse", list(options.keys()))
            selected_id = options[choix_label]
            selected_row = next(r for r in choix_rows if r["id"] == selected_id)

            col1, col2 = st.columns(2)
            with col1:
                if selected_row.get("image_url"):
                    st.image(selected_row["image_url"], caption="Radio analysée", use_container_width=True)
                st.write(
                    f"**Diagnostic IA :** {selected_row.get('diagnosis')} "
                    f"({(selected_row.get('confidence') or 0) * 100:.1f} %)"
                )
                if selected_row.get("doctor_diagnosis"):
                    st.caption(f"Avis déjà enregistré : {selected_row['doctor_diagnosis']}")

            with col2:
                doctor_diagnosis = st.radio(
                    "Diagnostic du médecin", ["Sain", "Malade", "Autre"], horizontal=True
                )
                precision = ""
                if doctor_diagnosis == "Autre":
                    precision = st.text_input("Précise le diagnostic (ex : nom de la pathologie)")
                notes = st.text_area("Notes complémentaires (optionnel)")

                if doctor_diagnosis == "Autre" and precision and notes:
                    notes_final = f"{precision} — {notes}"
                elif doctor_diagnosis == "Autre":
                    notes_final = precision
                else:
                    notes_final = notes

                if st.button("💾 Enregistrer l'avis médical", type="primary"):
                    ok, res = api.set_doctor_opinion(TOKEN, selected_id, doctor_diagnosis, notes_final)
                    if ok:
                        _load_history.clear()
                        st.success("Avis médical enregistré ! Retrouve la comparaison dans l'Historique.")
                        st.rerun()
                    else:
                        st.error(res)

# ---------------------------------------------------------------- TAB 4
with tab_kpi:
    st.subheader("📊 Indicateurs clés")
    ok, stats = api.get_stats(TOKEN)
    if not ok:
        st.error(stats)
        st.stop()

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
        chart_data = chart_data[chart_data["Nombre"] > 0]
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
    if stats.get("taux_concordance") is not None:
        st.metric(
            "Taux de concordance IA / médecin",
            f"{stats['taux_concordance']:.0f} %",
            help=f"Calculé sur {stats['avec_avis_medecin']} analyse(s) ayant un avis médical.",
        )
    else:
        st.info("Aucun avis médical enregistré pour le moment.")
