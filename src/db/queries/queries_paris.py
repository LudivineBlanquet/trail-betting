"""
REQUETES SQL - PARIS

Ce module regroupe toutes les requêtes relatives aux paris des utilisateurs.
Toutes les opérations passent par le client Supabase (PostgREST / HTTPS).

Fonctions disponibles :
    - get_pari_par_user_et_course() : pari d'un utilisateur pour une course.
    - pari_existe() : vérifie si un pari existe.
    - insert_pari() : enregistrement d'un nouveau pari.
    - update_pari() : modification d'un pari existant.
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_admin_client


def get_pari_par_user_et_course(user_id: str, course_id: str) -> dict | None:
    """
    Récupère le pari d'un utilisateur pour une course spécifique.

    Interroge directement la table paris (avec les UUID des coureurs) plutôt que la vue, pour pouvoir pré-remplir
    les listes déroulantes du dialog avec les UUID nécessaires à la comparaison.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
        course_id (str) : UUID de la course concernée.

    Retourne :
        dict | None : dictionnaire contenant tous les champs du pari, ou None si aucun pari trouvé ou en cas d'erreur.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        # Utilisation du client admin pour bypasser le RLS sur la table paris
        from src.db.connection import get_supabase_admin_client
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("paris")
            .select("*")
            .eq("user_id", user_id)
            .eq("course_id", course_id)
            .limit(1)
            .execute()
        )

        # Vérification explicite que response.data est une liste non vide
        if not response.data or not isinstance(response.data, list):
            return None

        return response.data[0]

    except Exception as e:
        st.error(f"Erreur lors de la vérification du pari : {e}")
        return None


def pari_existe(user_id: str, course_id: str) -> bool:
    """
    Vérifie si un utilisateur a déjà déposé un pari pour une course.

    Utilisé pour afficher "Modifier mon pari" ou "Saisir un pari" sur le bouton de chaque course dans la page courses.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
        course_id (str) : UUID de la course.

    Retourne :
        bool : True si un pari existe, False sinon.
    """

    pari = get_pari_par_user_et_course(user_id, course_id)

    # Vérification stricte : doit être un dict avec un id valide
    return isinstance(pari, dict) and bool(pari.get("id"))


def insert_pari(
    user_id: str,
    course_id: str,
    homme_1er: str | None = None,
    homme_2eme: str | None = None,
    homme_3eme: str | None = None,
    femme_1ere: str | None = None,
    femme_2eme: str | None = None,
    femme_3eme: str | None = None
) -> dict | None:
    """
    Enregistre un nouveau pari dans la base de données.

    La contrainte UNIQUE (user_id, course_id) définie dans le schema empêche les doublons au niveau base de données.
    Les pronostics null sont acceptés si l'utilisateur ne renseigne pas tout.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
        course_id (str) : UUID de la course concernée.
        homme_1er (str | None): UUID du coureur pronostiqué 1er homme.
        homme_2eme (str | None): UUID du coureur pronostiqué 2ème homme.
        homme_3eme (str | None): UUID du coureur pronostiqué 3ème homme.
        femme_1ere (str | None): UUID de la coureuse pronostiquée 1ère.
        femme_2eme (str | None): UUID de la coureuse pronostiquée 2ème.
        femme_3eme (str | None): UUID de la coureuse pronostiquée 3ème.

    Retourne :
        dict | None : données du pari créé (avec son UUID généré), ou None en cas d'erreur.

    Lève :
        Exception : en cas de doublon ou d'erreur d'insertion.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("paris")
            .insert({
                "user_id"   : user_id,
                "course_id" : course_id,
                "homme_1er" : homme_1er,
                "homme_2eme": homme_2eme,
                "homme_3eme": homme_3eme,
                "femme_1ere": femme_1ere,
                "femme_2eme": femme_2eme,
                "femme_3eme": femme_3eme,
            })
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement du pari : {e}")
        return None


def update_pari(
    pari_id: str,
    homme_1er: str | None = None,
    homme_2eme: str | None = None,
    homme_3eme: str | None = None,
    femme_1ere: str | None = None,
    femme_2eme: str | None = None,
    femme_3eme: str | None = None
) -> bool:
    """
    Met à jour les pronostics d'un pari existant.

    Appelé lorsque l'utilisateur modifie un pari avant la publication des résultats.
    Seuls les champs de pronostics sont modifiables — user_id et course_id sont immuables.

    Paramètres :
        pari_id (str) : UUID du pari à modifier.
        homme_1er (str | None) : UUID du nouveau pronostic 1er homme.
        homme_2eme (str | None) : UUID du nouveau pronostic 2ème homme.
        homme_3eme (str | None) : UUID du nouveau pronostic 3ème homme.
        femme_1ere (str | None) : UUID du nouveau pronostic 1ère femme.
        femme_2eme (str | None) : UUID du nouveau pronostic 2ème femme.
        femme_3eme (str | None) : UUID du nouveau pronostic 3ème femme.

    Retourne :
        bool : True si la mise à jour a réussi, False sinon.

    Lève :
        Exception : en cas d'erreur de mise à jour.
    """

    try:
        admin = get_supabase_admin_client()
        admin \
            .table("paris") \
            .update({
                "homme_1er" : homme_1er,
                "homme_2eme": homme_2eme,
                "homme_3eme": homme_3eme,
                "femme_1ere": femme_1ere,
                "femme_2eme": femme_2eme,
                "femme_3eme": femme_3eme,
            }) \
            .eq("id", pari_id) \
            .execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de la modification du pari : {e}")
        return False