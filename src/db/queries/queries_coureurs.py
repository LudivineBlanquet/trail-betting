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
from src.db.connection import get_supabase_client

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