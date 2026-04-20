"""
REQUETES SQL - COURSES ET PARTICIPANTS

Ce module regroupe toutes les requêtes relatives aux courses et à leurs participants (coureurs inscrits).

Fonctions disponibles :
    - get_courses_a_venir(): liste des courses à venir sans résultats.
    - get_participants_par_course(): coureurs inscrits à une course donnée.
    - get_favoris_par_course(): top N favoris H/F selon l'index UTMB.
    - insert_course(): création d'une nouvelle course (admin).
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client, get_supabase_admin_client

# Formats UTMB valides et colonnes d'index associées
FORMAT_TO_COLUMN: dict[str, str] = {
    "global": "index_utmb_global",
    "20K": "index_utmb_20k",
    "50K": "index_utmb_50k",
    "100K": "index_utmb_100k",
    "100M": "index_utmb_100m"
}

FORMATS_COURSE = ["20K", "50K", "100K", "100M"]


# LECTURE - COURSES
# ---------------------------------------------------------------------------
def get_courses_a_venir() -> pd.DataFrame:
    """
    Récupère toutes les courses à venir via la vue vue_courses_a_venir.
    Les courses sont triées par date croissante (défini dans la vue).

    Retourne :
        pd.DataFrame : colonnes [id, nom, evenement, format, lieu, distance, denivele, date_course, avis_expert]
            Retourne un DataFrame vide si aucune course à venir.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        supabase = get_supabase_client()
        
        response = supabase.table("vue_courses_a_venir").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des courses à venir : {e}")
        return pd.DataFrame()


# LECTURE - PARTICIPANTS ET FAVORIS
# ---------------------------------------------------------------------------
def get_participants_par_course(course_id: str) -> pd.DataFrame:
    """
    Récupère la liste des coureurs inscrits à une course via vue_participants_course.

    Paramètres :
        course_id (str) : UUID de la course.

    Retourne :
        pd.DataFrame : colonnes [coureur_id, nom, prenom, nationalite, sexe, index_utmb_global, index_utmb_20k,
            index_utmb_50k, index_utmb_100k, index_utmb_100m]. Retourne un DataFrame vide si aucun participant.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_participants_course")
            .select("*")
            .eq("course_id", course_id)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des participants : {e}")
        return pd.DataFrame()


def get_favoris_par_course(course_id: str, format_course: str, top_n: int = 10) -> dict:
    """
    Calcule le top N des favoris hommes et femmes pour une course donnée.
    Récupère les participants via la vue, trie par index UTMB global puis par index spécifique au format en critère secondaire, et sépare par genre.

    Paramètres :
        course_id (str) : UUID de la course.
        format_course (str) : format UTMB ('20K', '50K', '100K', '100M').
        top_n (int) : nombre de favoris à retourner par genre. Défaut : 10.

    Retourne :
        dict : {
            "hommes" : pd.DataFrame (top_n hommes triés par index),
            "femmes" : pd.DataFrame (top_n femmes triées par index)
        }
        Colonnes : [rang, coureur_id, nom, prenom, nationalite, index_utmb_global, index_utmb_format]

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    col_format = FORMAT_TO_COLUMN.get(format_course, "index_utmb_global")

    df = get_participants_par_course(course_id)
    if df.empty:
        return {"hommes": pd.DataFrame(), "femmes": pd.DataFrame()}

    # Tri par index global puis index format (critère secondaire)
    df = df.sort_values(by = ["index_utmb_global", col_format], ascending = [False, False], na_position = "last")

    # Renommage pour l'affichage
    df = df.rename(columns = {col_format: "index_utmb_format"})

    hommes = df[df["sexe"] == "H"].head(top_n).reset_index(drop = True)
    femmes = df[df["sexe"] == "F"].head(top_n).reset_index(drop = True)

    hommes.insert(0, "rang", range(1, len(hommes) + 1))
    femmes.insert(0, "rang", range(1, len(femmes) + 1))

    return {"hommes": hommes, "femmes": femmes}


# ECRITURE - ADMIN UNIQUEMENT
# ---------------------------------------------------------------------------
def insert_course(
    evenement: str,
    nom: str,
    format_course: str,
    distance: float,
    denivele: float,
    lieu: str,
    date_course: str,
    avis_expert: str = None,
    image_url: str = None
) -> dict | None:
    """
    Insère une nouvelle course dans la base de données.
    Réservé aux administrateurs. Utilise le client admin (SERVICE_KEY) pour bypasser le Row Level Security.

    Paramètres :
        evenement (str) : nom de l'événement parent (ex : 'Val d'Aran by UTMB').
        nom (str) : nom de la course (ex : 'CCC').
        format_course (str) : format UTMB ('20K', '50K', '100K', '100M').
        distance (float) : distance en kilomètres.
        denivele (float) : dénivelé positif en mètres.
        lieu (str) : lieu de la course.
        date_course (str) : date au format 'YYYY-MM-DD'.
        avis_expert (str | None) : analyse du Duc (optionnelle à la création).
        image_url (str | None) : URL d'un logo de la course (optionnelle à la création).

    Retourne :
        dict | None : données de la course créée (avec son UUID généré), ou None en cas d'erreur.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("courses")
            .insert({
                "evenement": evenement,
                "nom": nom,
                "format": format_course,
                "distance": distance,
                "denivele": denivele,
                "lieu": lieu,
                "date_course": date_course,
                "avis_expert": avis_expert,
                "image_url": image_url,
                "resultats_publies": False
            })
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors de la création de la course : {e}")
        return None