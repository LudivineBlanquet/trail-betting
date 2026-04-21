"""
REQUETES SQL - COUREURS ET INDEX UTMB

Ce module regroupe toutes les requêtes relatives aux coureurs et à leurs index UTMB World Series.
Formats d'index disponibles : global, 20K, 50K, 100K, 100M.

Fonctions disponibles :
    - get_tous_les_coureurs() : liste complète des coureurs.
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client, get_supabase_admin_client

# Mapping format → colonne d'index dans la table coureurs
FORMAT_TO_COLUMN: dict[str, str] = {
    "global": "index_utmb_global",
    "20K": "index_utmb_20k",
    "50K": "index_utmb_50k",
    "100K": "index_utmb_100k",
    "100M": "index_utmb_100m"
}


# LECTURE
# ---------------------------------------------------------------------------
def get_tous_les_coureurs() -> pd.DataFrame:
    """
    Récupère la liste complète de tous les coureurs du référentiel.
    Triés par index global décroissant pour faciliter la sélection dans les interfaces d'administration.

    Retourne :
        pd.DataFrame : colonnes [id, nom, prenom, nationalite, sexe, image, index_utmb_global, index_utmb_20k, index_utmb_50k,
            index_utmb_100k, index_utmb_100m, updated_at]. Retourne un DataFrame vide en cas d'erreur.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        supabase = get_supabase_client()

        all_rows = []
        batch_size = 1000
        offset = 0

        while True:
            response = (
                supabase
                .table("vue_coureurs")
                .select("*")
                .order("index_utmb_global", desc = True)
                .range(offset, offset + batch_size - 1)
                .execute()
            )

            data = response.data
            if not data:
                break

            all_rows.extend(data)
            # Stop si dernière page
            if len(data) < batch_size:
                break

            offset += batch_size

        return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des coureurs : {e}")
        return pd.DataFrame()


def reconcilier_participants(df_import: pd.DataFrame, df_coureurs: pd.DataFrame, course_id: str) -> tuple[list[dict], list[dict], pd.DataFrame]:
    """
    Réconcilie les participants importés avec le référentiel coureurs.

    Pour chaque ligne du fichier importé (Nom, Prenom, Sexe), tente de trouver le coureur correspondant dans df_coureurs via une jointure
    insensible à la casse sur (nom, prenom, sexe).

    Seuls les participants trouvés dans le référentiel sont conservés. Les non-trouvés sont retournés dans un DataFrame séparé pour signalement.

    Paramètres :
        df_import (pd.DataFrame) : données importées depuis le fichier. Colonnes attendues : Nom, Prenom, Sexe.
        df_coureurs (pd.DataFrame) : référentiel complet des coureurs.

    Retourne :
        tuple :
            - list[dict] : participants réconciliés prêts pour insertion, avec coureur_id, nom, prenom, sexe.
            - pd.DataFrame : participants non trouvés dans le référentiel.
    """

    df_import = df_import.copy()
    df_coureurs = df_coureurs.copy()

    # Normalisation
    df_import["nom_norm"] = df_import["Nom"].str.strip().str.upper()
    df_import["prenom_norm"] = df_import["Prenom"].str.strip().str.upper()
    df_import["sexe_norm"] = df_import["Sexe"].str.strip().str.upper()

    df_coureurs["nom_norm"] = df_coureurs["nom"].str.strip().str.upper()
    df_coureurs["prenom_norm"] = df_coureurs["prenom"].str.strip().str.upper()
    df_coureurs["sexe_norm"] = df_coureurs["sexe"].str.strip().str.upper()

    # Jointure sur (nom, prenom, sexe)
    merged = df_import.merge(df_coureurs[["id", "nom_norm", "prenom_norm", "sexe_norm"]], on = ["nom_norm", "prenom_norm", "sexe_norm"], how = "left")

    trouves = merged[merged["id"].notna()]
    non_trouves = merged[merged["id"].isna()][["Nom", "Prenom", "Sexe"]]

    # Chargement des coureur_id déjà en base pour cette course
    admin = get_supabase_admin_client()
    existants_resp = (
        admin
        .schema("trail_betting_db")
        .table("participants_course")
        .select("coureur_id")
        .eq("course_id", course_id)
        .execute()
    )
    deja_inseres = {p["coureur_id"] for p in existants_resp.data}

    participants_nouveaux = []
    participants_existants = []

    for _, row in trouves.iterrows():
        entry = {
            "coureur_id": row["id"],
            "nom": row["Nom"],
            "prenom": row["Prenom"],
            "sexe": row["sexe_norm"]
        }
        if row["id"] in deja_inseres:
            participants_existants.append(entry)
        else:
            participants_nouveaux.append(entry)

    return participants_nouveaux, participants_existants, non_trouves.reset_index(drop = True)


def insert_participants_reconcilies(course_id: str, participants: list[dict]) -> bool:
    """
    Insère ou met à jour les participants réconciliés dans la table participants_course.

    Stratégie : upsert basé sur une contrainte d’unicité (course_id, coureur_id).
    - Si un participant existe déjà pour cette course → mise à jour
    - Sinon → insertion

    Paramètres :
        course_id (str) : UUID de la course.
        participants (list[dict]) : liste des participants.

    Retourne :
        bool : True si l’opération a réussi, False sinon.

    Remarques :
        - Repose sur une contrainte UNIQUE(course_id, coureur_id) en base.
        - Garantit l’absence de doublons pour un même coureur dans une course.
        - Ne supprime pas les anciens participants absents de la liste fournie.
    """

    if not participants:
        return True

    try:
        admin = get_supabase_admin_client()
        rows = [
            {
                "course_id": course_id,
                "coureur_id": p["coureur_id"],
                "nom": p["nom"],
                "prenom": p["prenom"],
                "sexe": p["sexe"]
            }
            for p in participants
        ]
        admin.schema("trail_betting_db").table("participants_course").upsert(rows).execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement des participants : {e}", icon = "✖")
        return False