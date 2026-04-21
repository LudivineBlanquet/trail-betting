"""
MODULE DE NAVIGATION - GESTION DYNAMIQUE

Ce fichier gère la navigation dynamique de l'application Streamlit sans gestion de rôles.

Fonctionnalités principales :
- Lecture dynamique de la configuration de navigation via un fichier YAML (config_pages.yml) :
    * Définition des pages disponibles et de leur organisation en sections logiques (Menu, etc.).
- Génération du menu de navigation (st.navigation) basée sur le fichier YAML.
- Affichage d'un logo personnalisable dans la barre latérale.
- Affichage de cartes sur la page d'accueil servant de boutons de navigation vers les autres pages.

Ce module est utilisé au niveau principal de l'application (app.py) pour initialiser la structure de navigation lors du lancement.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import streamlit.components.v1 as components
from streamlit_extras.add_vertical_space import add_vertical_space
import yaml

# LOCAL LIBRAIRIES ----------------------------
from src.functions.utils import get_image_base64, load_callable
from src.pages.login import afficher_bandeau_connexion


def make_wrapped_page(callable_or_path: callable, page_name: str):
    """
    Crée un wrapper qui définit automatiquement la page courante avant d'appeler la vraie fonction de page.

    Args:
        callable_or_path (callable): La fonction correspondant à la page à afficher.
        page_name (str): Le nom de la page courante à enregistrer dans la session.

    Returns:
        callable: Une fonction sans argument qui met à jour la session puis appelle la page.
    """

    def wrapped():
        st.session_state["page_courante"] = page_name
        callable_or_path()

    return wrapped

def charger_config_et_pages():
    """
    Charge la configuration YAML et instancie les objets Page Streamlit.
    
    Returns:
        tuple:
            - variables (dict): contenu du fichier config_pages.yml
            - nav (dict): mapping {nom_page: st.Page}
    """

    with open("config_pages.yml", "r", encoding = "utf-8-sig") as f:
        variables = yaml.safe_load(f)

    nav = {}
    for page_name, page_info in variables["PAGES"].items():
        page_source = load_callable(page_info["source_file"])
        wrapped_callable = make_wrapped_page(page_source, page_info["page_title"])
        nav[page_name] = st.Page(
            wrapped_callable,
            title = page_info["page_title"],
            icon = page_info["page_icon"],
            url_path = page_info["page_title"]
        )

    return variables, nav

def afficher_logo_sidebar(logo_path: str, logo_link: str):
    """
    Affiche le logo dans la sidebar si présent.
    
    Args:
        logo_path (str): Chemin vers le fichier image du logo.
        logo_link (str): URL vers laquelle le logo redirige lorsqu'on clique dessus.
    """

    if not logo_path:
        return

    logo_base64 = get_image_base64(logo_path)
    html = f"""
        <style>
        .rounded-img {{
            border-radius: 15px;
            width: 75%;
            display: block;
            margin-top: -10px;
            margin-left: auto;
            margin-right: auto;
        }}
        </style>
        <a href="{logo_link}" target="_blank">
            <img src="data:image/png;base64,{logo_base64}" class="rounded-img">
        </a>
    """
    st.sidebar.markdown(html, unsafe_allow_html = True)


def construire_menu(nav: dict, variables: dict) -> dict:
    """
    Construit le menu de navigation en filtrant les pages selon le rôle de l'utilisateur connecté.

    Les pages avec role_requis = "admin" ne sont visibles que si st.session_state["user_role"] == "admin".
    Les pages sans role_requis (null) sont visibles par tous.

    Paramètres :
        nav (dict) : Dictionnaire des pages Streamlit.
        variables (dict) : Configuration extraite de config_pages.yml.

    Retourne :
        dict : Structure du menu Streamlit regroupée par sections. Exemple : {"Menu": [...], "Administration": [...], "Compte": [...]}
    """

    role_utilisateur = st.session_state.get("user_role")
    menu = {}

    for page_name, page_info in variables["PAGES"].items():

        role_requis = page_info.get("role_requis")

        # Filtrage : page admin visible uniquement pour les admins
        if role_requis == "admin" and role_utilisateur != "admin":
            continue

        section = page_info.get("section", "Menu")
        page = nav.get(page_name)

        if page:
            menu.setdefault(section, []).append(page)

    return menu


def carte_redirection_page(page: str, image: str, titre: str):
    """
    Crée une carte interactive (image + titre) permettant de rediriger vers une autre page de l'application via un clic utilisateur.
    Il est nécessaire d'avoir un menu de navigation. 

    Cette fonction insère un composant HTML contenant :
        - Une carte stylisée avec une image et un titre.
        - Du JavaScript pour simuler un clic sur la barre latérale de navigation Streamlit.
        - Du CSS pour personnaliser l'apparence et l'effet au survol.

    Args:
        page (str): Le nom ou une partie du libellé de la page cible (tel qu'affiché dans la sidebar).
        image (str): L'image encodée en base64, affichée sur la carte.
        titre (str): Le texte du titre affiché sous l'image.

    Returns:
        streamlit.components.v1.components.html: Un composant HTML rendu dans l'application.
    """

    # Script JavaScript pour simuler un clic dans la barre de navigation.
    js = """
        <script>
            function goTo(page) {

                const page_links = parent.document.querySelectorAll('[data-testid="stSidebarNavLink"]');

                let found = false;
                page_links.forEach((link, i) => {
                    const text = link.textContent.trim();
                    
                    if (text.includes(page)) {
                        link.click();
                        found = true;
                    }
                });
            }
        </script>
        """
    # Composant HTML (image + redirection via la fonction JS définie précédemment)
    html = f"""
        <div class="card" onclick="goTo('{page}')">
            <img src="data:image/png;base64,{image}" style="width:50%; height:40px; object-fit:contain;">
            <div style="margin-top: 10px;">
                {titre}
            </div>
        </div>
        """
    # CSS pour personnaliser l'apparence et l'effet au survol
    css = """
        <style>
            /* Style des cartes de navigation cliquables */
            .card {
                background-color: #F2F6FC;
                box-shadow: 3px 3px 5px rgba(0, 32, 96, 0.25);
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                color: #504b51;
                font-family: system-ui;
                font-weight: bold;
                font-size: 14px;
                transition: all 0.3s ease;
                cursor: pointer;
            }

            /* Effet au survol */
            .card:hover {
                transform: scale(1.03);
                background-color: #E9EBF2;
                box-shadow: 3px 3px 5px rgba(0, 32, 96, 0.25);
            }
        </style>
    """

    return components.html(js + html + css, width = None)


@st.dialog("Comment ça marche ?", width = 'medium')
def afficher_bloc_info() -> None:
    """
    Affiche un bloc explicatif sur le fonctionnement de l'application.
    Présente les règles du jeu : comment parier, comment les points sont calculés et quand les résultats sont publiés.
    """

    components.html(
        """
        <style>
            body, html { margin: 0; padding: 0; }
        </style>
        <div style="font-family: system-ui; font-size: 14px; line-height: 1.5;">

            <p style="margin-top: 0;"><strong>Saisi des paris :</strong><br>
            Pour chaque course à venir, pronostique le podium hommes et femmes parmi les favoris - sélectionnés selon leur index UTMB.</p>

            <p><strong>Système de points :</strong></p>
            <table style="width:100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #E8FFEE;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: center;">Pronostic</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: center;">Points</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">Coureur à la bonne place</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">10 pts</td>
                    </tr>
                    <tr style="background-color: #F2F6FC;">
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">Coureur sur le podium (mais à la mauvaise place)</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">4 pts</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">Podium complet dans le bon ordre (H ou F)</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">+5 pts bonus</td>
                    </tr>
                </tbody>
            </table>

            <p><strong>Mise à jour hebdomadaire :</strong><br>
            Chaque vendredi, de nouvelles courses sont ajoutées et l'avis de ton souverain le Duc de Savoie, est publié, pour t'aider à faire tes choix.</p>

            <p><strong>Classement :</strong><br>
            Les points s'accumulent au fil des courses. Le classement est mis à jour automatiquement après chaque publication de résultats.</p>

        </div>
        """,
        height = 400, scrolling = True
    )


@st.dialog("Nous contacter")
def afficher_contact() -> None:
    """
    Affiche un formulaire de contact permettant à l'utilisateur d'envoyer un message par mail.
    Nécessite la configuration des variables SMTP dans les secrets Streamlit.
    """

    # Utilisateur non connecté : invitation à se connecter
    if not st.session_state.get("authentifie"):
        st.caption("Connecte-toi pour pouvoir nous écrire.")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            img_compte = get_image_base64("src/assets/images/mountain-running-silhouette.png")
            carte_redirection_page(page = "Mon compte", image = img_compte, titre = "Connexion à mon compte")
        return

    st.caption("Tu as une question ou un problème ? Écris-nous !")
    sujet = st.text_input("Sujet")
    message = st.text_area("Message", height = 150)

    col1, col2, col3 = st.columns([1, 1, 1])
    if col2.button("Envoyer", type = "primary", use_container_width = True):
        if not sujet or not message:
            st.error("Merci de remplir tous les champs.", icon = "⚠")
        else:
            try:
                import smtplib
                from email.mime.text import MIMEText

                msg = MIMEText(f"De : {st.session_state.get('user_email')}\n\n{message}")
                msg["Subject"] = f"[Trail Betting] {sujet}"
                msg["From"] = st.secrets["SMTP_USER"]
                msg["To"] = st.secrets["SMTP_TO"]

                with smtplib.SMTP_SSL("smtp.orange.fr", 465) as server:
                    server.login(st.secrets["SMTP_USER"], st.secrets["SMTP_PASSWORD"])
                    server.send_message(msg)

                st.success("Message envoyé ! On te répond au plus vite.", icon = "✔")
            except Exception as e:
                st.error(f"Erreur lors de l'envoi : {e}", icon = "✖")


def set_navigation() :
    """
    Définit et exécute la navigation principale de l'application sans gestion de rôles.

    Cette fonction réalise les étapes suivantes :
    - Chargement de la configuration des pages et crée les objets Page Streamlit.
    - Affichage éventuel du logo dans la barre latérale.
    - Lancement de la navigation via st.navigation().

    Returns:
        None. La navigation est lancée via pg.run() et contrôle le flux de l'application.
    """

    # Chargement de la configuration et des pages
    variables, nav = charger_config_et_pages()

    # Affichage du logo sidebar si présent
    afficher_logo_sidebar(variables.get("LOGO_SIDEBAR"), variables.get("LOGO_LINK", "#"))

    # Bandeau connexion si non authentifié
    afficher_bandeau_connexion()

    # Construction du menu par section
    menu = construire_menu(nav, variables)

    with st.sidebar:
        col1, col2 = st.columns([1, 1], gap = "xxsmall")
        if col1.button("Infos", type = 'tertiary', icon = ":material/info:"):
            afficher_bloc_info()
        if col2.button("Contact", type = "tertiary", icon = "✉"):
            afficher_contact()

    pg = st.navigation(menu)        
    pg.run()