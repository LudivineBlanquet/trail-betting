"""
PAGE COURSES A VENIR

Cette page affiche la liste des courses à venir sous forme de volets dépliables.

Pour chaque course, l'utilisateur peut consulter :
    - Le top 10 des favoris hommes et femmes selon l'index UTMB global et l'index spécifique au format de la course.
    - L'avis du Duc de Savoie (expert trail).
    - Un bouton pour saisir ou modifier son pari via un dialog st.dialog.

L'accès à la saisie d'un pari nécessite d'être connecté.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import streamlit.components.v1 as components
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
import requests
import base64
import json
from datetime import datetime, date

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils import get_image_base64, formater_date, colorier_rang_favoris, code_pays_drapeau
from src.components.navigation import carte_redirection_page
from src.db.queries.queries_courses import get_courses_a_venir, get_favoris_par_course
from src.db.queries.queries_paris import pari_existe, get_pari_par_user_et_course
from src.functions.paris_dialog import dialog_saisir_pari
from src.db.queries.queries_resultats import get_derniers_resultats
from src.db.connection import get_supabase_client

# Dictionnaire de mapping format → image
FORMAT_IMAGES = {
    "20K": "src/assets/images/20K.png",
    "50K": "src/assets/images/50K.png",
    "100K": "src/assets/images/100K.png",
    "100M": "src/assets/images/100M.png"
}


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_derniers_resultats() -> None:
    """
    Affiche un bloc récapitulatif des derniers résultats publiés.

    Récupère les 5 dernières courses dont les résultats sont disponibles et les affiche sous forme de tableau stylisé.
    Le bloc est masqué si aucun résultat n'est encore disponible.
    """

    df = get_derniers_resultats(limit = 5)
    if df.empty:
        return

    # Préparer les images base64 pour chaque format
    format_images_b64 = {fmt: get_image_base64(path) for fmt, path in FORMAT_IMAGES.items()}

    # Convertir le DataFrame en liste de dicts
    df_clean = df.rename(columns = {
        "date_course": "date",
        "course_evt": "evt",
        "course_nom": "course",
        "course_format": "format",
        "homme_1er": "homme",
        "femme_1ere": "femme",
        "homme_1er_photo": "homme_photo",
        "femme_1ere_photo": "femme_photo"
    }).drop(columns = ["saisi_at"])

    rows_json = df_clean.to_json(orient = "records", force_ascii = False)
    images_json = json.dumps(format_images_b64)

    html = f"""
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: system-ui; color: var(--color-text-primary); }}
        .toolbar {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 12px; flex-wrap: wrap; }}
        .toolbar-title {{ font-size: 15px; font-style: italic; color: #888; }}
        input[type=search] {{ font-size: 13px; padding: 6px 10px; border-radius: 8px; border: 0.5px solid #ccc; width: 200px; outline: none; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        thead th {{ padding: 8px 12px; text-align: left; font-weight: 500; font-size: 12px; color: #888; border-bottom: 0.5px solid #eee; cursor: pointer; user-select: none; white-space: nowrap; }}
        thead th:hover {{ color: #333; }}
        .sort-icon {{ margin-left: 4px; opacity: 0.4; font-size: 10px; }}
        thead th.sorted .sort-icon {{ opacity: 1; }}
        tbody tr {{ border-bottom: 0.5px solid #f0f0f0; transition: background 0.1s; }}
        tbody tr:hover {{ background: #fafafa; }}
        tbody tr:last-child {{ border-bottom: none; }}
        td {{ padding: 1px 12px; vertical-align: middle; }}
        .runner {{ display: flex; align-items: center; gap: 8px; white-space: nowrap; overflow: hidden; }}
        .avatar {{ width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 500; flex-shrink: 0; }}
        .avatar.m {{ background: #E6F1FB; color: #185FA5; }}
        .avatar.f {{ background: #FBEAF0; color: #993556; }}
        .date-chip {{ font-size: 12px; color: #888; }}
        .fmt-img {{ width: 50px; height: 40px; object-fit: contain; }}
    </style>

    <div style="padding: 1rem 0; max-height: 400px; overflow-y: auto;">
        <div class="toolbar">
            <span class="toolbar-title">Derniers résultats disponibles...</span>
            <input type="search" id="search" placeholder="Rechercher..." oninput="render()">
        </div>
        <table>
            <thead>
                <tr>
                    <th onclick="sort('date')" id="h-date">Date <span class="sort-icon">↕</span></th>
                    <th onclick="sort('evt')" id="h-evt">Événement <span class="sort-icon">↕</span></th>
                    <th onclick="sort('course')" id="h-course">Course <span class="sort-icon">↕</span></th>
                    <th onclick="sort('format')" id="h-format">Format <span class="sort-icon">↕</span></th>
                    <th>1er Homme</th>
                    <th>1ère Femme</th>
                </tr>
            </thead>
            <tbody id="tbody"></tbody>
        </table>
    </div>

    <script>
        const data = {rows_json};
        const formatImages = {images_json};

        const initials = name => name.split(" ").map(p => p[0]).join("").slice(0, 2).toUpperCase();

        const avatar = (name, photo, genre) => {{
            if (photo) {{
                return `<img src="${{photo}}" style="width:26px;height:26px;border-radius:50%;object-fit:cover;flex-shrink:0;">`;
            }}
            return `<div class="avatar ${{genre}}">${{initials(name)}}</div>`;
        }};

        const formatDate = d => {{
            const [y, m, j] = d.split("-");
            const mois = ["jan","fév","mar","avr","mai","jun","jul","aoû","sep","oct","nov","déc"];
            return `${{j}} ${{mois[+m-1]}} ${{y}}`;
        }};

        let sortKey = "date", sortDir = -1;

        function sort(key) {{
            if (sortKey === key) sortDir *= -1;
            else {{ sortKey = key; sortDir = -1; }}
            document.querySelectorAll("thead th").forEach(th => th.classList.remove("sorted"));
            document.getElementById("h-" + key)?.classList.add("sorted");
            render();
        }}

        function render() {{
            const q = document.getElementById("search").value.toLowerCase();
            let rows = data.filter(r =>
                (r.evt || "").toLowerCase().includes(q) ||
                (r.course || "").toLowerCase().includes(q) ||
                (r.format || "").toLowerCase().includes(q) ||
                (r.homme || "").toLowerCase().includes(q) ||
                (r.femme || "").toLowerCase().includes(q)
            );
            rows.sort((a, b) => {{
                const av = a[sortKey] || "", bv = b[sortKey] || "";
                return av < bv ? sortDir : av > bv ? -sortDir : 0;
            }});
            const tbody = document.getElementById("tbody");
            if (!rows.length) {{
                tbody.innerHTML = `<tr><td colspan="6" class="empty">Aucun résultat</td></tr>`;
                return;
            }}
            tbody.innerHTML = rows.map(r => {{
                const imgSrc = formatImages[r.format]
                    ? `<img src="data:image/png;base64,${{formatImages[r.format]}}" class="fmt-img">`
                    : `<span style="font-size:11px;color:#888">${{r.format}}</span>`;
                return `
                    <tr>
                        <td><span class="date-chip">${{formatDate(r.date)}}</span></td>
                        <td style="font-weight:500">${{r.evt}}</td>
                        <td style="color:#888">${{r.course}}</td>
                        <td>${{imgSrc}}</td>
                        <td><div class="runner">${{avatar(r.homme, r.homme_photo, 'm')}}${{r.homme}}</div></td>
                        <td><div class="runner">${{avatar(r.femme, r.femme_photo, 'f')}}${{r.femme}}</div></td>
                    </tr>
                `;
            }}).join("");
        }}

        render();
    </script>
    """

    row_height = 50 # hauteur par ligne en px
    header_height = 100 # toolbar + thead
    max_height = 360 # plafond
    height = min(header_height + len(df_clean) * row_height, max_height)

    components.html(html, height = height, scrolling = True)


def afficher_favoris(course_id: str, format_course: str) -> None:
    """
    Affiche le top 10 des favoris hommes et femmes pour une course.
    Présente deux tableaux côte à côte : favoris hommes à gauche, favoris femmes à droite.

    Paramètres :
        course_id (str) : UUID de la course.
        format_course (str) : format UTMB pour choisir l'index pertinent.
    """

    favoris = get_favoris_par_course(course_id, format_course, top_n = 40)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-weight: bold; font-family: system-ui; margin-bottom: 8px; color: #D20606">
            Favoris Hommes :
            </div>
            """,
            unsafe_allow_html = True
        )

        df_h = favoris["hommes"]
        if df_h.empty:
            st.caption("Aucun favori disponible.")
        else:
            # Sélection et renommage des colonnes pour l'affichage
            df_affichage = df_h[["rang", "prenom", "nom", "nationalite", "index_utmb_global", "index_utmb_format"]]
            df_affichage["coureur"] = df_affichage["prenom"].str.title() + " " + df_affichage["nom"].str.upper()
            df_affichage["index_utmb_global"] = df_affichage["index_utmb_global"].astype("Int64")
            df_affichage["index_utmb_format"] = df_affichage["index_utmb_format"].astype("Int64")
            df_affichage["nationalite"] = df_affichage["nationalite"].apply(code_pays_drapeau)
            df_affichage = df_affichage[["rang", "coureur", "nationalite", "index_utmb_global", "index_utmb_format"]
            ].rename(columns = {
                "rang": "Rang",
                "coureur": "Coureur",
                "nationalite": "Nationalité",
                "index_utmb_global": "Index global",
                "index_utmb_format": f"Index {format_course}"
            })
            st.dataframe(
                df_affichage.style.apply(colorier_rang_favoris, axis = 1),
                hide_index = True,
                width = 'stretch',
                height = 280,
                column_config = {"Nationalité": st.column_config.ImageColumn(label = "Nationalité", width = "small")}
            )

    with col2:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-weight: bold; font-family: system-ui; margin-bottom: 8px; color: #D20606"">
            Favorites Femmes :
            </div>
            """,
            unsafe_allow_html = True
        )

        df_f = favoris["femmes"]
        if df_f.empty:
            st.caption("Aucune favorite disponible.")
        else:
            # Sélection et renommage des colonnes pour l'affichage
            df_affichage = df_f[["rang", "prenom", "nom", "nationalite", "index_utmb_global", "index_utmb_format"]]
            df_affichage["coureuse"] = df_affichage["prenom"] + " " + df_affichage["nom"].str.upper()
            df_affichage["index_utmb_global"] = df_affichage["index_utmb_global"].astype("Int64")
            df_affichage["index_utmb_format"] = df_affichage["index_utmb_format"].astype("Int64")
            df_affichage["nationalite"] = df_affichage["nationalite"].apply(code_pays_drapeau)
            df_affichage = df_affichage[["rang", "coureuse", "nationalite", "index_utmb_global", "index_utmb_format"]
            ].rename(columns = {
                "rang": "Rang",
                "coureuse": "Coureuse",
                "nationalite": "Nationalité",
                "index_utmb_global": "Index global",
                "index_utmb_format": f"Index {format_course}"
            })
            st.dataframe(
                df_affichage.style.apply(colorier_rang_favoris, axis = 1),
                hide_index = True,
                width = 'stretch',
                height = 280,
                column_config = {"Nationalité": st.column_config.ImageColumn(label = "Nationalité", width = "small")}
            )


def afficher_avis_expert(avis_expert: str | None) -> None:
    """
    Affiche l'avis du Duc de Savoie pour une course.
    Affiche un message par défaut si l'avis n'a pas encore été saisi.

    Paramètres :
        avis_expert (str | None) : texte de l'analyse du Duc, ou None.
    """

    st.markdown("**L'avis du Duc de Savoie &nbsp; ❤**")
    if avis_expert:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-style: italic; font-family: system-ui; color: #55545a; margin-bottom: 15px;">
            {avis_expert}
            </div>
            """,
            unsafe_allow_html = True
        )
    else:
        st.caption("La sainte parole de ton souverain n'est pas encore disponible pour cette course.")


def afficher_bouton_pari(course: dict) -> None:
    """
    Affiche le bouton de saisie ou modification du pari pour une course.

    Si l'utilisateur n'est pas connecté, affiche un message d'invitation à la connexion.
    Si un pari existe déjà, le bouton passe en mode modification. Le clic ouvre le dialog de saisie du pari.

    Paramètres :
        course (dict) : dictionnaire contenant les infos de la course.
    """

    # Utilisateur non connecté : invitation à se connecter
    if not st.session_state.get("authentifie"):
        st.caption("Connecte-toi pour saisir un pari.")
        return

    # Détermination du libellé selon l'existence d'un pari
    a_deja_parie = pari_existe(st.session_state["user_id"], course["id"])
    label_bouton = "Modifier mon pari" if a_deja_parie else "Saisir un pari"

    date_course = datetime.strptime(course["date_course"], "%Y-%m-%d").date()
    if st.button(label_bouton, key = f"btn_pari_{course['id']}", type = 'primary', disabled = date.today() >= date_course):
        # Récupération du pari existant pour pré-remplissage éventuel
        pari_existant = get_pari_par_user_et_course(st.session_state["user_id"], course["id"]) if a_deja_parie else None
        dialog_saisir_pari(course = course, pari_existant = pari_existant)


def afficher_volet_course(course: dict) -> None:
    """
    Affiche un volet dépliable complet pour une course.

    Contient dans l'ordre :
        1. Les informations générales (lieu, date, format).
        2. Le top 10 des favoris H/F.
        3. L'avis du Duc.
        4. Le bouton de saisie du pari.

    Paramètres :
        course (dict) : dictionnaire avec les champs de la course.
    """

    # Label du volet : nom + date + format
    label_expander = (f"{course['nom']}  —  " f"{course['format']}  —  "f"{formater_date(course['date_course'])}")
    with st.expander(label_expander, expanded = False):

        # Informations générales
        col1, col2, col3 = st.columns(3)
        with col1:
            img_path = FORMAT_IMAGES.get(course["format"])
            img_b64 = get_image_base64(img_path)
            st.markdown(
                """
                <div style="font-size: 14px;">
                Format
                </div>
                """,
                unsafe_allow_html = True
            )
            st.markdown(
                f'<img src="data:image/png;base64,{img_b64}" style="width:130px; height:auto; margin-top: 10px">',
                unsafe_allow_html = True
            )
        col2.metric("Lieu", course["lieu"] or "—")
        col3.metric("Date", formater_date(course["date_course"]))

        # CONTAINER
        with stylable_container(
            key = f"container_ombre_{course}",
            css_styles = """
                {
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    background-color: white;
                    padding: 8px 6px 24px;
                    box-shadow: 3px 3px 5px rgba(0, 32, 96, 0.25); /* Ombre bleue (#002060) */
                }
            """,
        ):
            col1, col2 = st.columns(2)

            # Top 10 favoris
            afficher_favoris(course["id"], course["format"])

        col1, col2, col3, col4 = st.columns([0.25, 0.5, 0.25, 1])
        # Bouton pari
        with col2:
            add_vertical_space(1)
            afficher_bouton_pari(course)

        # Avis du Duc
        with col4:
            # CONTAINER AVIS DU DUC
            with stylable_container(
                key = f"container_infos_{course}",
                css_styles = """
                    {
                        border-radius: 0.5rem;
                        background-color: #F8EBFA;
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        border-color: #D20606;
                        padding: 10px 10px 11px;
                    }
                """
            ):
                afficher_avis_expert(course.get("avis_expert"))


@st.dialog("Proposer une course")
def afficher_suggestion_course() -> None:
    """
    Affiche un formulaire permettant à l'utilisateur de proposer une course manquante.
    """

    # Utilisateur non connecté : invitation à se connecter
    if not st.session_state.get("authentifie"):
        st.caption("Connecte-toi pour pouvoir nous envoyer ta course.")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            img_compte = get_image_base64("src/assets/images/mountain-running-silhouette.png")
            carte_redirection_page(page = "Mon compte", image = img_compte, titre = "Connexion à mon compte")
        return

    st.caption("⚠ &nbsp; Nous ne pourrons l'ajouter que si la liste des participants est disponible !")

    nom_course = st.text_input("Nom de la course")
    url = st.text_input("Lien vers la liste des participants (optionnel)")

    col1, col2, col3 = st.columns([1, 1, 1])
    if col2.button("Envoyer", type = "primary", use_container_width = True):
        if not nom_course:
            st.warning("Merci de renseigner le nom de la course.", icon = "⚠")
        else:
            supabase = get_supabase_client()
            supabase.table("courses_suggestions").insert({
                "nom_course": nom_course,
                "url_participants": url
            }).execute()
            st.success("Merci ! On va regarder ça...", icon = "✔")


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page courses à venir qui présente :
        - Un tableau des derniers résultats disponibles.
        - Un volet dépliable par course à venir.
        - Un formulaire de suggestion de course.
    """

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
                COURSES À VENIR
            </span>
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(2)

    # Derniers résultats
    afficher_derniers_resultats()
    add_vertical_space(1)

    # Chargement des courses
    df_courses = get_courses_a_venir()
    if df_courses.empty:
        st.info("Aucune course à venir pour le moment... Reviens bientôt pour les prochaines annonces !")
        return

    # Affichage groupé par événement
    evenements = df_courses["evenement"].unique()
    for evenement in evenements:
        col1, col2 = st.columns([6, 1])
        col1.markdown(
            f"""
            <div style="font-size: 15px; font-family: system-ui; margin-bottom: 0px">
            ➤ &nbsp; <span style="font-weight: bold ;font-style: italic">{evenement}</span>
            </div>
            """,
            unsafe_allow_html = True
        )

        image_url = df_courses[df_courses["evenement"] == evenement]["image_url"].iloc[0]
        with col2:
            if image_url:
                content_type = "image/svg+xml" if image_url.endswith(".svg") else "image/png"
                img_data = base64.b64encode(requests.get(image_url).content).decode()
                style = "width:100px; height:50px; object-fit:contain; margin-bottom: 0px;"

            else:
                content_type = "image/png"
                img_data = get_image_base64("src/assets/images/utmb_index.png")
                style = "width:100px; height:auto; margin-bottom: 15px;"
            
            st.markdown(
                f'<img src="data:{content_type};base64,{img_data}" style="{style}">',
                unsafe_allow_html = True
            )

        df_evenement = df_courses[df_courses["evenement"].fillna("Autres courses") == evenement]
        for _, course in df_evenement.iterrows():
            afficher_volet_course(course.to_dict())

    add_vertical_space(2)
    if st.button("Ta course n'est pas dispo &nbsp; ?", type = 'primary'):
        afficher_suggestion_course()
