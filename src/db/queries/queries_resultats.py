"""
REQUETES SQL - RESULTATS

Ce module regroupe toutes les requêtes relatives aux résultats officiels des courses (podiums hommes et femmes).

Fonctions disponibles :
    - get_derniers_resultats() : derniers résultats publiés toutes courses.
    - insert_resultats() : saisie des résultats officiels (admin).
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client, get_supabase_admin_client


def get_derniers_resultats(limit: int = 5) -> pd.DataFrame:
    """
    Récupère les derniers résultats publiés via la vue vue_derniers_resultats.

    Paramètres :
        limit (int) : nombre de courses à retourner. Défaut : 5.

    Retourne :
        pd.DataFrame : colonnes [date_course, course_nom, course_format, homme_1er, femme_1ere, saisi_at]
            Triées par date décroissante. Retourne un DataFrame vide en cas d'erreur.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_derniers_resultats")
            .select("*")
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des derniers résultats : {e}")
        return pd.DataFrame()


def insert_resultats(course_id: str, admin_id: str, homme_1er: str | None = None, homme_2eme: str | None = None, homme_3eme: str | None = None, femme_1ere: str | None = None, femme_2eme: str | None = None, femme_3eme: str | None = None) -> dict | None:
    """
    Insère ou met à jour les résultats officiels d'une course.

    Stratégie : upsert basé sur une contrainte d’unicité (course_id).
    - Si les résultats existent déjà → mise à jour
    - Sinon → insertion

    Réservé aux administrateurs. L'insertion déclenche automatiquement le trigger fn_scorer_paris_apres_resultats()
    qui calcule les points de tous les paris et met à jour les totaux utilisateurs.

    Paramètres :
        course_id (str) : UUID de la course.
        admin_id (str) : UUID de l'admin saisissant les résultats.
        homme_1er (str | None) : UUID du coureur arrivé 1er.
        homme_2eme (str | None) : UUID du coureur arrivé 2ème.
        homme_3eme (str | None) : UUID du coureur arrivé 3ème.
        femme_1ere (str | None) : UUID de la coureuse arrivée 1ère.
        femme_2eme (str | None) : UUID de la coureuse arrivée 2ème.
        femme_3eme (str | None) : UUID de la coureuse arrivée 3ème.

    Retourne :
        dict | None : données du résultat créé ou None en cas d'erreur.

    Remarques :
    - Repose sur une contrainte UNIQUE(course_id).
    - Garantit un seul résultat par course.
    - Le trigger doit être défini sur INSERT ET UPDATE pour assurer la cohérence des scores.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("resultats")
            .upsert({
                "course_id": course_id,
                "saisi_par": admin_id,
                "homme_1er": homme_1er,
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
        st.error(f"Erreur lors de la saisie des résultats : {e}")
        return None