"""
PAGE D'ACCUEIL - TRAIL BETTING

Page d'entrée de l'application. Affiche:
    - Un bloc hero avec le logo et la description de l'application.
    - Des cartes de navigation cliquables vers les sections principales.
    - Un bloc des derniers résultats publiés pour donner vie à la page.

Cette page est accessible à tous les utilisateurs, connectés ou non.
La connexion est requise uniquement pour saisir un pari ou proposer une course.
"""

# LIBRAIRIES ----------------------------
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils import extraire_bloc_style, get_image_base64, render_footer
from src.components.navigation import carte_redirection_page

# Dictionnaire de mapping format → image
FORMAT_IMAGES = {
    "20K": "src/assets/images/20K.png",
    "50K": "src/assets/images/50K.png",
    "100K": "src/assets/images/100K.png",
    "100M": "src/assets/images/100M.png"
}


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_hero() -> None:
    """
    Affiche le bloc hero de la page d'accueil.
    Contient le logo de l'application, le titre, le tagline et une courte description du concept.
    """

    bg = get_image_base64("src/assets/images/ugo.jpg")
    st.markdown(
        f"""
        <div class="hero-wrapper">
            <div class="hero" style="background-image: url('data:image/png;base64,{bg}');">
                <p class="hero-titre">Trail Betting</p>
                <p class="hero-tagline">Le Betclic du trail running</p>
                <p class="hero-description">
                    Pronostique les podiums des plus grandes courses de trail, défie tes amis et grimpe au classement.<br>
                    Chaque vendredi, de nouvelles courses et l'avis de ton Souverain, le Duc de Savoie &nbsp; ❤︎
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html = True
    )


def afficher_cartes_navigation() -> None:
    """
    Affiche les cartes de navigation cliquables vers les sections principales.

    Deux cartes sont affichées côte à côte :
        - Courses à venir : accès aux pronostics.
        - Classement : accès au classement général.
    """

    img_courses = get_image_base64("src/assets/images/utmb_index.png")
    img_classement = get_image_base64("src/assets/images/duc-army-logo.webp")
    img_compte = get_image_base64("src/assets/images/mon-compte.png")

    col0, col1, col2, col3, col4 = st.columns([0.5, 1, 1, 1, 0.5])
    with col1:
        carte_redirection_page(page = "Courses", image = img_courses, titre = "Courses à venir et paris")
    with col2:
        carte_redirection_page(page = "Classement", image = img_classement, titre = "Classement des soldats du Duc")
    with col3:
        carte_redirection_page(page = "Mon compte", image = img_compte, titre = "Connexion à mon compte")


# MAIN
def main() -> None:
    """
    Fonction principale de la page d'accueil.

    Orchestre l'affichage des différents blocs dans l'ordre:
        1. Injection des styles CSS.
        2. Bandeau d'invitation à la connexion (si non connecté).
        3. Bloc hero (logo + titre + description).
        4. Cartes de navigation.
    """

    # Injection des styles CSS de la page
    st.markdown(extraire_bloc_style("header", "src/assets/styles/styles.html"), unsafe_allow_html = True)
    st.markdown(extraire_bloc_style("footer", "src/assets/styles/styles.html"), unsafe_allow_html = True)
    st.markdown(extraire_bloc_style("hero", "src/assets/styles/styles.html"), unsafe_allow_html = True)
    render_footer()

    # Hero : logo + titre + tagline
    afficher_hero()

    # Cartes de navigation
    afficher_cartes_navigation()