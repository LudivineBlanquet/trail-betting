"""
PAGE CONNEXION / INSCRIPTION

Cette page permet aux utilisateurs de se connecter ou de créer un compte.
Elle est accessible depuis le menu de navigation et redirige automatiquement vers la page d'accueil après une authentification réussie.

Contenu :
    - Bloc d'introduction avec description de l'application.
    - Deux boutons côte à côte : "Se connecter" et "Créer un compte" qui ouvrent les dialogs correspondants.
    - Bloc informatif sur le fonctionnement de l'application.

Si l'utilisateur est déjà connecté, la page affiche un message de bienvenue avec un bouton de déconnexion.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
import streamlit.components.v1 as components

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils import extraire_bloc_style, render_footer
from src.components.authentification import dialog_connexion, dialog_inscription, deconnecter


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_bandeau_connexion() -> None:
    """
    Affiche un bandeau d'invitation à la connexion si l'utilisateur n'est pas connecté.

    Le bandeau est masqué automatiquement dès que l'utilisateur se connecte.
    """

    if st.session_state.get("authentifie"):
        return


def afficher_utilisateur_connecte() -> None:
    """
    Affiche le bloc de bienvenue pour un utilisateur déjà connecté. Montre le pseudo, le rôle et un bouton de déconnexion.
    """

    pseudo = st.session_state.get("user_pseudo", "")
    role = st.session_state.get("user_role", "user")

    add_vertical_space(1)
    st.success(f"Bienvenue sur *Trail Betting* **{pseudo}** !", icon = "✔")

    if role == "admin":
        st.info("Tu as les droits administrateur.")

    add_vertical_space(1)

    if st.button("Se déconnecter", type = "primary"):
        deconnecter()


def afficher_formulaires_auth() -> None:
    """
    Affiche les boutons d'accès aux dialogs de connexion et d'inscription.
    """

    st.markdown(
        """
        <div style="font-size: 15px; text-align: center">
        Rejoins la communauté <i>Trail Betting</i> pour pronostiquer les podiums des plus grandes courses de trail et défier tes amis au classement.
        </div>
        """,
        unsafe_allow_html = True
    )

    add_vertical_space(2)
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

    with col2:
        if st.button("Se connecter", type = "primary", width = 'stretch'):
            dialog_connexion()

    with col3:
        if st.button("Créer un compte", width = 'stretch'):
            dialog_inscription()


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page connexion / inscription.

    Orchestre l'affichage selon l'état de connexion :
        - Si connecté : bloc de bienvenue + bouton déconnexion.
        - Si déconnecté : boutons connexion/inscription + bloc info.
    """

    # Injection des styles CSS de la page
    st.markdown(extraire_bloc_style("footer", "src/assets/styles/styles.html"), unsafe_allow_html = True)
    render_footer()

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
                MON COMPTE
            </span>
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(2)

    if st.session_state.get("authentifie"):
        afficher_utilisateur_connecte()

    else:
        afficher_formulaires_auth()
        add_vertical_space(2)