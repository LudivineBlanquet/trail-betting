"""
PAGE CLASSEMENT

Cette page affiche le classement général des participants ainsi que les statistiques personnelles de l'utilisateur connecté.

Contenu :
    - Bloc statistiques personnelles (rang, points, taux de réussite) affiché uniquement si l'utilisateur est connecté.
    - Classement général de tous les participants avec rang, pseudo, points, nombre de paris et taux de réussite.
    - Historique personnel des points course par course (graphique d'évolution du cumul) affiché si l'utilisateur est connecté et a au moins un pari scoré.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import streamlit.components.v1 as components
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container
import plotly.express as px

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils import get_image_base64, formater_date, format_rang
from src.db.queries.queries_classement import get_classement_general, get_stats_par_user, get_historique_points_user

# Dictionnaire de mapping format → image
FORMAT_IMAGES = {
    "20K": "src/assets/images/20K.png",
    "50K": "src/assets/images/50K.png",
    "100K": "src/assets/images/100K.png",
    "100M": "src/assets/images/100M.png"
}


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_stats_personnelles(user_id: str) -> None:
    """
    Affiche le bloc de statistiques personnelles de l'utilisateur connecté.

    Présente 4 métriques côte à côte : rang actuel, points cumulés, nombre de paris scorés et taux de réussite.
    Le bloc est masqué si l'utilisateur n'a pas encore de paris scorés.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
    """

    stats = get_stats_par_user(user_id)
    if not stats:
        st.caption("Tes statistiques apparaîtront ici une fois tes premiers paris scorés.")
        return
    
    st.markdown(
        f"""
        <div style="font-size: 16px; font-weight: bold; font-style:oblique; font-family: system-ui; margin-bottom: 8px; color: #D20606">
        Tes statistiques personnelles :
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label = "Rang", value = f"# &nbsp;{stats[0]['rang']}")
    col2.metric(label = "Points", value = stats[0]["points_total"])
    col3.metric(label = "Paris scorés", value = f"{stats[0]['nb_paris_scores']} / {stats[0]['nb_paris']}")
    col4.metric(label = "Taux de réussite", value = f"{stats[0]['taux_reussite']} %")


def afficher_historique(user_id: str) -> None:
    """
    Affiche le graphique d'évolution des points cumulés de l'utilisateur.

    Trace une courbe du cumul de points au fil des courses, avec en dessous un tableau détaillé par course (points gagnés, pronostics vs résultats réels).
    Le bloc est masqué si aucun historique n'est disponible.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
    """

    df = get_historique_points_user(user_id)
    if df.empty:
        return

    st.markdown(
        f"""
        <div style="font-size: 16px; font-weight: bold; font-style:oblique; font-family: system-ui; margin-bottom: 8px; color: #D20606">
        Évolution de tes points :
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    # Graphique d'évolution du cumul
    fig = px.line(df, x = "date_course", y = "cumul_points")
    fig.update_layout(title = "Évolution du cumul des points", xaxis_title = "Date des courses", yaxis_title = "Points cumulés", hovermode = "x unified")
    fig.update_traces(line = dict(color = "#A76FE7", width = 1), marker = dict(size = 12), mode = "lines+markers",
        hovertemplate = "<b>Date :</b> %{x|%d/%m/%Y}<br><b>Points :</b> %{y}")

    st.plotly_chart(fig, theme = "streamlit", width = "stretch")
    add_vertical_space(1)

    # Tableau détaillé par course
    st.markdown(
        f"""
        <div style="font-size: 16px; font-weight: bold; font-style:oblique; font-family: system-ui; margin-bottom: 8px; color: #D20606">
        Détail par course :
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    df["course_format"] = df["course_format"].map(lambda format: f"data:image/png;base64,{get_image_base64(FORMAT_IMAGES[format])}"
        if format in FORMAT_IMAGES else format)

    df_affichage = df[["date_course", "course_evt", "course_nom", "course_format", "points_gagnes",
        "homme_1er_parie", "homme_1er_reel", "femme_1ere_pariee", "femme_1ere_reelle"]
        ].rename(columns = {
            "date_course": "Date",
            "course_evt": "Evénement",
            "course_nom": "Course",
            "course_format": "Format",
            "points_gagnes": "Points",
            "homme_1er_parie": "Pari 1er Homme",
            "homme_1er_reel": "Réel 1er Homme",
            "femme_1ere_pariee": "Pari 1ère Femme",
            "femme_1ere_reelle": "Réel 1ère Femme"
        }
    )
    df_affichage["Date"] = df_affichage["Date"].apply(formater_date)

    st.dataframe(df_affichage, width = 'stretch', hide_index = True,
        column_config = {
            "Format": st.column_config.ImageColumn(
                label = "Format",
                width = 100,
            )
        }
    )


def afficher_classement_general() -> None:
    """
    Affiche le tableau du classement général de tous les participants.
    """

    df = get_classement_general()
    if df.empty:
        st.info("Le classement est vide pour le moment. Sois le premier à parier !")
        return

    # Préparer les données
    df_clean = df[["rang", "pseudo", "points_total", "nb_paris_scores", "nb_paris", "taux_reussite"]].copy()
    rows_json = df_clean.to_json(orient = "records", force_ascii = False)

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
        td {{ padding: 6px 12px; vertical-align: middle; }}
        .rang {{ font-size: 16px; width: 36px; display: inline-block; text-align: center; }}
        .pseudo {{ font-weight: 500; }}
        .points {{ font-weight: 600; color: #185FA5; }}
        .paris-cell {{ font-size: 12px; color: #555; }}
        .progress-wrap {{ display: flex; align-items: center; gap: 8px; }}
        .progress-bar {{ flex: 1; height: 6px; background: #eee; border-radius: 3px; overflow: hidden; min-width: 60px; }}
        .progress-fill {{ height: 100%; border-radius: 3px; background: linear-gradient(90deg, #4caf50, #81c784); transition: width 0.4s ease; }}
        .progress-label {{ font-size: 12px; color: #555; white-space: nowrap; }}
    </style>

    <div style="padding: 1rem 0; max-height: 400px; overflow-y: auto;">
        <div class="toolbar">
            <span class="toolbar-title">Classement général :</span>
            <input type="search" id="search" placeholder="Rechercher..." oninput="render()">
        </div>
        <table>
            <thead>
                <tr>
                    <th onclick="sort('rang')" id="h-rang">Rang <span class="sort-icon">↕</span></th>
                    <th onclick="sort('pseudo')" id="h-pseudo">Pseudo <span class="sort-icon">↕</span></th>
                    <th onclick="sort('points_total')" id="h-points_total">Points <span class="sort-icon">↕</span></th>
                    <th onclick="sort('nb_paris')" id="h-nb_paris">Paris scorés <span class="sort-icon">↕</span></th>
                    <th onclick="sort('taux_reussite')" id="h-taux_reussite">Réussite (%) <span class="sort-icon">↕</span></th>
                </tr>
            </thead>
            <tbody id="tbody"></tbody>
        </table>
    </div>

    <script>
        const data = {rows_json};

        const PODIUM = {{ 1: "🥇", 2: "🥈", 3: "🥉" }};

        const formatRang = r => PODIUM[r] ? `<span class="rang">${{PODIUM[r]}}</span>` : `<span class="rang" style="font-size:13px;color:#888">#${{r}}</span>`;

        let sortKey = "rang", sortDir = 1;

        function sort(key) {{
            if (sortKey === key) sortDir *= -1;
            else {{ sortKey = key; sortDir = 1; }}
            document.querySelectorAll("thead th").forEach(th => th.classList.remove("sorted"));
            document.getElementById("h-" + key)?.classList.add("sorted");
            render();
        }}

        function render() {{
            const q = document.getElementById("search").value.toLowerCase();
            let rows = data.filter(r =>
                (r.pseudo || "").toLowerCase().includes(q)
            );
            rows.sort((a, b) => {{
                const av = a[sortKey] ?? "", bv = b[sortKey] ?? "";
                return av < bv ? -sortDir : av > bv ? sortDir : 0;
            }});
            const tbody = document.getElementById("tbody");
            if (!rows.length) {{
                tbody.innerHTML = `<tr><td colspan="5" style="padding:16px;text-align:center;color:#aaa;font-size:13px;">Aucun résultat</td></tr>`;
                return;
            }}
            tbody.innerHTML = rows.map(r => {{
                const taux = r.taux_reussite ?? 0;
                const paris = `${{r.nb_paris_scores}} / ${{r.nb_paris}}`;
                return `
                    <tr>
                        <td>${{formatRang(r.rang)}}</td>
                        <td class="pseudo">${{r.pseudo}}</td>
                        <td class="points">${{r.points_total}}</td>
                        <td class="paris-cell">${{paris}}</td>
                        <td>
                            <div class="progress-wrap">
                                <div class="progress-bar">
                                    <div class="progress-fill" style="width:${{taux}}%"></div>
                                </div>
                                <span class="progress-label">${{taux}}%</span>
                            </div>
                        </td>
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


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page classement.

    Orchestre l'affichage dans l'ordre :
        1. Injection des styles CSS.
        2. Titre de la page.
        3. Bloc statistiques personnelles (si connecté).
        4. Historique personnel des points (si connecté et données disponibles).
        5. Classement général de tous les participants.
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
                CLASSEMENT DES SOLDATS
            </span>
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(2)

    # Classement général (visible par tous)
    afficher_classement_general()

    # Bloc personnel : stats + historique (uniquement si connecté)
    if st.session_state.get("authentifie"):

        user_id = st.session_state["user_id"]

        # CONTAINER
        with stylable_container(
            key = f"container_ombre",
            css_styles = """
                {
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    background-color: white;
                    padding: 10px 15px 10px;
                    box-shadow: 3px 3px 5px rgba(0, 32, 96, 0.25); /* Ombre bleue (#002060) */
                }
            """,
        ):
            afficher_stats_personnelles(user_id)
            add_vertical_space(1)

            afficher_historique(user_id)
            add_vertical_space(1)

    else:
        st.info("Tu auras accès à tes statistiques personnelles et ton historique une fois connecté.")
        add_vertical_space(1)