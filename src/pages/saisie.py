"""
PAGE SAISIE - ADMINISTRATION - TRAIL BETTING

Page réservée aux administrateurs pour la mise à jour hebdomadaire
du contenu de l'application (chaque vendredi).

Trois onglets disponibles :
    - Ajouter une course : saisie obligatoire de tous les champs (événement, nom, format, distance, dénivelé, lieu, date, avis expert).
    - Ajouter les participants : sélection d'une course et import d'un fichier.
    Réconciliation automatique obligatoire avec la table coureurs — les participants introuvables sont signalés et ignorés.
    - Ajouter les résultats : sélection d'une course et saisie du podium hommes et femmes à partir de la liste des participants inscrits.

Accès réservé aux utilisateurs avec role = 'admin'.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import pandas as pd
from streamlit_extras.add_vertical_space import add_vertical_space

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils import formater_date
from src.db.queries.queries_courses import insert_course
from src.db.queries.queries_coureurs import get_tous_les_coureurs, reconcilier_participants, insert_participants_reconcilies
from src.db.queries.queries_resultats import insert_resultats
from src.db.connection import get_supabase_admin_client


# UTILITAIRES INTERNES
# ---------------------------------------------------------------------------
def verifier_acces_admin() -> bool:
    """
    Vérifie que l'utilisateur connecté a le rôle admin.

    Affiche un message d'erreur et stoppe l'exécution si ce n'est pas le cas.

    Retourne :
        bool : True si l'utilisateur est admin, False sinon.
    """

    if not st.session_state.get("authentifie"):
        st.error("Tu dois être connecté pour accéder à cette page.", icon = "⚠")
        st.stop()
        return False

    if st.session_state.get("user_role") != "admin":
        st.error("Accès réservé aux administrateurs.", icon = "✖")
        st.stop()
        return False

    return True


def get_toutes_les_courses() -> pd.DataFrame:
    """
    Récupère toutes les courses (passées et à venir) pour les sélecteurs admin.

    Retourne :
        pd.DataFrame : colonnes [id, nom, evenement, format, date_course] triées par date décroissante.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("courses")
            .select("id, nom, evenement, format, date_course")
            .order("date_course", desc = True)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des courses : {e}", icon = "✖")
        return pd.DataFrame()


def label_course(row: pd.Series) -> str:
    """
    Génère un label lisible pour une course dans les selectbox.

    Paramètres :
        row (pd.Series) : ligne du DataFrame courses.

    Retourne :
        str : label formaté pour affichage dans un selectbox.
    """

    evenement = f"{row['evenement']} — " if row.get("evenement") else ""
    date = formater_date(row['date_course'])
    return f"{evenement}{row['nom']} ({row['format']}) — {date}"


# ONGLET 1 : AJOUTER UNE COURSE
# ---------------------------------------------------------------------------
def onglet_ajouter_course() -> None:
    """
    Affiche le formulaire de création d'une nouvelle course.

    Tous les champs sont obligatoires : événement, nom, format, distance, dénivelé, lieu et date.
    L'avis expert est le seul champ optionnel. Vérifie l'absence de doublon sur (nom, date_course) avant insertion.
    """

    col1, col2 = st.columns(2)

    with col1:
        evenement = st.text_input("Événement *", placeholder = "Val d'Aran by UTMB", help = "Nom de l'événement global.")
        nom = st.text_input("Nom de la course *", placeholder = "CCC", help = "Nom de la course de l'événement global.")
        format_c = st.selectbox("Format *", options = ["20K", "50K", "100K", "100M"])
        lieu = st.text_input("Lieu *", placeholder = "Chamonix, France")

    with col2:
        date_course = st.date_input("Date de la course *", min_value = 'today')
        distance = st.number_input("Distance (km) *", min_value = 0.0, value = 20.0, step = 5.0, format = "%.1f")
        denivele = st.number_input("Dénivelé positif (m) *", min_value = 0, value = 500, step = 100)
        image_url = st.text_input("URL du logo de la course")

    avis_expert = st.text_area("Avis du Duc de Savoie", placeholder = "Analyse et pronostic de la course... (optionnel)", height = 120)

    add_vertical_space(1)
    if st.button("Ajouter la course", type = "primary"):

        # Validation des champs obligatoires
        champs_vides = []
        if not evenement : champs_vides.append("Événement")
        if not nom : champs_vides.append("Nom")
        if not lieu : champs_vides.append("Lieu")

        if champs_vides:
            st.warning("Champs obligatoires manquants.", icon = "⚠")
            return

        # Vérification doublon sur (nom, date_course)
        try:
            admin = get_supabase_admin_client()
            response = (
                admin
                .table("courses")
                .select("id")
                .eq("nom", nom)
                .eq("date_course", str(date_course))
                .limit(1)
                .execute()
            )
            if response.data:
                st.warning(f"Une course **{nom}** existe déjà à cette date. Vérifie le calendrier avant d'ajouter.", icon = "⚠")
                return
        except Exception as e:
            st.error(f"Erreur lors de la vérification des doublons : {e}", icon = "✖")
            return

        # Insertion
        course = insert_course(
            evenement = evenement,
            nom = nom,
            format_course = format_c,
            distance = float(distance),
            denivele = float(denivele),
            lieu = lieu,
            date_course = str(date_course),
            avis_expert = avis_expert if avis_expert else None,
            image_url = image_url if image_url else None
        )

        if course:
            st.success(f"Course **{nom}** ajoutée avec succès !", icon = "✔")
            st.rerun()


# ONGLET 2 : AJOUTER LES PARTICIPANTS
# ---------------------------------------------------------------------------
def onglet_participants() -> None:
    """
    Affiche l'interface d'import des participants pour une course.

    Étapes :
        1. Sélection de la course cible.
        2. Upload d'un fichier CSV ou Excel avec colonnes Nom, Prenom, Sexe.
        3. Réconciliation automatique obligatoire avec la table coureurs.
        4. Affichage des participants trouvés et non trouvés.
        5. Confirmation et insertion des participants réconciliés uniquement.
    """

    st.caption("Importe un fichier CSV ou Excel avec les colonnes **Nom**, **Prenom**, **Sexe**. Seuls les coureurs présents dans le référentiel seront intégrés.")

    add_vertical_space(1)
    # Sélection de la course
    df_courses = get_toutes_les_courses()

    if df_courses.empty:
        st.info("Aucune course disponible. Commence par en ajouter une.")
        return

    labels_courses = (df_courses.sort_values(["evenement", "date_course"], na_position = "last").apply(label_course, axis = 1).tolist())
    df_courses = df_courses.sort_values(["evenement", "date_course"], na_position = "last").reset_index(drop = True)

    idx_course = st.selectbox("Course cible *", options = range(len(labels_courses)), format_func = lambda i: labels_courses[i], key = "select_course_participants")
    course_id = df_courses.iloc[idx_course]["id"]

    add_vertical_space(1)
    # Upload du fichier
    fichier = st.file_uploader("Fichier participants (CSV ou Excel)", type = ["csv", "xlsx", "xls"], key = "upload_participants")

    if not fichier:
        return

    # Lecture du fichier
    try:
        df_import = (pd.read_csv(fichier, sep = ";") if fichier.name.endswith(".csv") else pd.read_excel(fichier))
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}", icon = "✖")
        return

    # Vérification des colonnes obligatoires
    colonnes_requises = {"Nom", "Prenom", "Sexe"}
    colonnes_manquantes = colonnes_requises - set(df_import.columns)

    if colonnes_manquantes:
        st.error("Colonnes manquantes dans le fichier. Les colonnes attendues sont exactement : **Nom**, **Prenom**, **Sexe**.", icon = "⚠")
        return

    st.success(f"Fichier chargé : **{len(df_import)} lignes** détectées.")

    # Réconciliation — on passe course_id en paramètre
    df_coureurs = get_tous_les_coureurs()
    participants_nouveaux, participants_existants, non_trouves = reconcilier_participants(df_import, df_coureurs, course_id)

    add_vertical_space(1)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"**✔ Nouveaux : {len(participants_nouveaux)}**")
        if participants_nouveaux:
            st.dataframe(pd.DataFrame(participants_nouveaux)[["nom", "prenom", "sexe"]], use_container_width = True, hide_index = True)

    with col2:
        st.markdown(f"**✔ Déjà enregistrés : {len(participants_existants)}**")
        if participants_existants:
            st.dataframe(pd.DataFrame(participants_existants)[["nom", "prenom", "sexe"]], use_container_width = True, hide_index = True)

    with col3:
        st.markdown(f"**✖ Non trouvés : {len(non_trouves)}**")
        if not non_trouves.empty: st.dataframe(non_trouves, use_container_width = True, hide_index = True)

    if not participants_nouveaux:
        st.info("Aucun nouveau participant à enregistrer.")
        return

    add_vertical_space(1)
    if st.button(f"Enregistrer {len(participants_nouveaux)} nouveaux participants", type = "primary"):
        ok = insert_participants_reconcilies(course_id, participants_nouveaux)
        if ok:
            st.success(f"**{len(participants_nouveaux)} participants** enregistrés !", icon = "✔")


# ONGLET 3 : AJOUTER LES RESULTATS
# ---------------------------------------------------------------------------
def get_resultats_bruts(course_id: str) -> dict | None:
    """
    Récupère les résultats bruts d'une course (avec UUID des coureurs).
    Utilisé pour pré-remplir les selectbox en mode édition.

    Paramètres :
        course_id (str) : UUID de la course.

    Retourne :
        dict | None : résultats avec UUID des coureurs, ou None si inexistants.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("resultats")
            .select("*")
            .eq("course_id", course_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors du chargement des résultats : {e}", icon = "✖")
        return None


def onglet_resultats() -> None:
    """
    Affiche l'interface de saisie ou modification des résultats d'une course.

    Deux modes :
        - Insertion : aucun résultat existant, bouton "Enregistrer".
        - Edition : résultats existants pré-remplis, bouton "Modifier".
    
    Note : le trigger de scoring ne se relance pas sur un UPDATE.
    """

    st.caption("Saisis le podium officiel. Cette action déclenche le calcul automatique des points pour tous les paris.")
    add_vertical_space(1)

    # Sélection de la course
    df_courses = get_toutes_les_courses()

    if df_courses.empty:
        st.info("Aucune course disponible.")
        return

    labels_courses = (df_courses.sort_values(["evenement", "date_course"], na_position = "last").apply(label_course, axis = 1).tolist())
    df_courses = df_courses.sort_values(["evenement", "date_course"], na_position="last").reset_index(drop = True)

    idx_course = st.selectbox("Course *", options = range(len(labels_courses)), format_func = lambda i: labels_courses[i], key = "select_course_resultats")
    course_id = df_courses.iloc[idx_course]["id"]

    add_vertical_space(1)
    # Détection du mode : insertion ou édition
    resultats_existants = get_resultats_bruts(course_id)
    est_edition = resultats_existants is not None

    if est_edition:
        st.info("Des résultats existent déjà pour cette course. Tu peux les modifier.")

    # Chargement des participants
    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("vue_participants_course")
            .select("coureur_id, nom, prenom, sexe")
            .eq("course_id", course_id)
            .execute()
        )
        df_participants = pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des participants : {e}", icon = "✖")
        return

    if df_participants.empty:
        st.info("Aucun participant enregistré pour cette course. Importe d'abord les participants dans l'onglet **Participants**.")
        return

    # Séparation H / F
    df_h = df_participants[df_participants["sexe"] == "H"].reset_index(drop = True)
    df_f = df_participants[df_participants["sexe"] == "F"].reset_index(drop = True)

    # Construction des options selectbox
    def build_opts(df: pd.DataFrame) -> tuple[list, dict]:

        options = ["— — —"]
        mapping = {"— — —": None}
        for _, row in df.iterrows():
            label = f"{row['prenom']} {row['nom'].upper()}"
            options.append(label)
            mapping[label] = str(row["coureur_id"])
        return options, mapping


    def index_existant(uuid_existant: str | None, mapping: dict) -> int:
        """
        Retrouve l'index d'un UUID existant dans le mapping pour pré-sélection.
        """

        if not uuid_existant:
            return 0
        for i, uuid in enumerate(mapping.values()):
            if uuid == uuid_existant:
                return i
        return 0

    opts_h, map_h = build_opts(df_h)
    opts_f, map_f = build_opts(df_f)

    # Pré-remplissage en mode édition
    h1_pre = resultats_existants.get("homme_1er") if est_edition else None
    h2_pre = resultats_existants.get("homme_2eme") if est_edition else None
    h3_pre = resultats_existants.get("homme_3eme") if est_edition else None
    f1_pre = resultats_existants.get("femme_1ere") if est_edition else None
    f2_pre = resultats_existants.get("femme_2eme") if est_edition else None
    f3_pre = resultats_existants.get("femme_3eme") if est_edition else None

    col_h, col_f = st.columns(2)
    with col_h:
        st.markdown("**Hommes :**")
        sel_h1 = st.selectbox("🥇 1er", opts_h, index = index_existant(h1_pre, map_h), key = f"res_h1_{course_id}")
        sel_h2 = st.selectbox("🥈 2ème", opts_h, index = index_existant(h2_pre, map_h), key = f"res_h2_{course_id}")
        sel_h3 = st.selectbox("🥉 3ème", opts_h, index = index_existant(h3_pre, map_h), key = f"res_h3_{course_id}")
    with col_f:
        st.markdown("**Femmes :**")
        sel_f1 = st.selectbox("🥇 1ère", opts_f, index = index_existant(f1_pre, map_f), key = f"res_f1_{course_id}")
        sel_f2 = st.selectbox("🥈 2ème", opts_f, index = index_existant(f2_pre, map_f), key = f"res_f2_{course_id}")
        sel_f3 = st.selectbox("🥉 3ème", opts_f, index = index_existant(f3_pre, map_f), key = f"res_f3_{course_id}")

    uuid_h1 = map_h[sel_h1]
    uuid_h2 = map_h[sel_h2]
    uuid_h3 = map_h[sel_h3]
    uuid_f1 = map_f[sel_f1]
    uuid_f2 = map_f[sel_f2]
    uuid_f3 = map_f[sel_f3]

    # Détection des doublons
    uuids_h = [u for u in [uuid_h1, uuid_h2, uuid_h3] if u]
    uuids_f = [u for u in [uuid_f1, uuid_f2, uuid_f3] if u]
    doublon_h = len(uuids_h) != len(set(uuids_h))
    doublon_f = len(uuids_f) != len(set(uuids_f))

    if doublon_h:
        st.warning("Le même coureur est sélectionné à plusieurs places (hommes).", icon = "⚠")
    if doublon_f:
        st.warning("La même coureuse est sélectionnée à plusieurs places (femmes).", icon = "⚠")

    add_vertical_space(1)
    label_bouton = "Modifier les résultats" if est_edition else "Enregistrer les résultats"
    if st.button(label_bouton, type = "primary", disabled = doublon_h or doublon_f):

        resultats = insert_resultats(
            course_id = course_id,
            homme_1er = uuid_h1,
            homme_2eme = uuid_h2,
            homme_3eme = uuid_h3,
            femme_1ere = uuid_f1,
            femme_2eme = uuid_f2,
            femme_3eme = uuid_f3
        )
        if resultats:
            st.success("Résultats enregistrés ! Les points ont été calculés automatiquement pour tous les paris.", icon = "✔")


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page d'administration.

    Vérifie les droits admin, injecte les styles CSS puis affiche les trois onglets de saisie.
    """

    verifier_acces_admin()

    st.markdown(
        """
        <div style="
            background-color: #D20606;
            border-radius: 8px;
            padding: 6px 24px;
            width: 90%;
            max-width: 500px;  
            margin: 0 auto;
            text-align: center;
        ">
            <span style="
                font-size: 20px;
                font-weight: bold;
                font-family: system-ui;
                color: white;
                letter-spacing: 1px;
            ">
                ADMINISTRATION
            </span>
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(2)

    st.caption(f"Connecté en tant que **{st.session_state.get('user_pseudo')}** — accès admin ✔")
    add_vertical_space(1)

    tab1, tab2, tab3 = st.tabs(["📋 Ajouter une course", "🏃‍♀️‍➡️ Entrer des participants", "🥇 Saisir des résultats"])

    with tab1:
        add_vertical_space(1)
        onglet_ajouter_course()

    with tab2:
        add_vertical_space(1)
        onglet_participants()

    with tab3:
        add_vertical_space(1)
        onglet_resultats()