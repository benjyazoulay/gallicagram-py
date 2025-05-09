import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import json
from streamlit_javascript import st_javascript
from user_agents import parse
import html # Not strictly needed in this snippet, but was in your original
import requests.utils
import os

st.set_page_config(page_title="Gallicagram", page_icon="https://github.com/user-attachments/assets/6011b645-fba6-4e16-9f39-d54add706fa2", layout="wide", menu_items=None)

# Injecter du CSS pour masquer la barre par défaut de Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    div[data-testid="stConnectionStatus"] {
    display: none !important;
    }
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.markdown("""
    <style>
    /* Supprimer l'espace en haut de la page */
    .main .block-container {
        padding-top: 0 !important;
        margin-top: -70px !important; /* Ajustez cette valeur si nécessaire */
    }

    /* Style spécifique pour les mobiles */
    @media only screen and (max-width: 600px) {
        /* Pour toutes les images sur mobile (le logo devra outrepasser margin-top) */
        img {
            display: block;
            margin-left: auto;
            margin-right: auto;
            margin-top: 0 !important; 
            padding-top: 0 !important;
        }
        .main .block-container {
            padding-top: 0 !important;
            margin-top: -70px !important; /* Ajustez cette valeur pour mobile si nécessaire */
        }
    }
    </style>
    """, unsafe_allow_html=True)


# Détecter le type d'appareil
ua_string = st_javascript("""window.navigator.userAgent;""")

# Initialiser la variable pour savoir si l'utilisateur est sur mobile
is_mobile = False

# Vérifier si ua_string est valide
if ua_string and isinstance(ua_string, str):
    user_agent = parse(ua_string)
    is_mobile = not user_agent.is_pc

st.session_state.is_mobile = is_mobile


# Fonction pour lire les cookies en Python
def get_is_mobile_from_cookie():
    # Fallback to False if 'is_mobile' is not in query_params
    return st.query_params.get('is_mobile', ['false'])[0] == 'true'

# Lire si c'est mobile à partir du cookie (ou fallback)
# is_mobile = get_is_mobile_from_cookie() # This might be overridden by JS, prioritize session_state

# Prioritize the JavaScript detection result if available
if 'is_mobile' in st.session_state:
    is_mobile = st.session_state.is_mobile
else:
    is_mobile = get_is_mobile_from_cookie() # Fallback if JS hasn't run or set the state


def generate_share_url():
    # Ensure 'state' is in query_params and not empty before accessing [0]
    base_url_param = st.query_params.get('state')
    if base_url_param:
        base_url = base_url_param[0]
        return f"https://gallicagram.streamlit.app/?state={base_url}"
    return "https://gallicagram.streamlit.app/" # Fallback if no state

def share_url():
    share_url_val = generate_share_url()
    st.code(share_url_val, language="python") # Changed variable name to avoid conflict

# Mapping des titres de corpus vers leurs codes API
corpus_mapping = {
    "Le Monde (1944-2024)": "lemonde_rubriques",
    "Presse de Gallica (1789-1950)": "presse",
    "Livres de Gallica (1600-1940)": "livres",
    "Opensubtitles (français, 1935-2020)": "subtitles",
    "Opensubtitles (anglais, 1930-2020)": "subtitles_en",
    "Rap (Genius, 1989-février 2024)": "rap",
    "Persée (1789-2023)": "query_persee",
    "Deutsches Zeitungsportal (DDB, 1780-1950)": "ddb",
    "American Stories (1798-1963)": "american_stories",
    "Journal de Paris (1777-1827)": "paris",
    "Moniteur Universel (1789-1869)": "moniteur",
    "Journal des Débats (1789-1944)": "journal_des_debats",
    "La Presse (1836-1869)": "la_presse",
    "Le Constitutionnel (1821-1913)": "constitutionnel",
    "Le Figaro (1854-1952)": "figaro",
    "Le Temps (1861-1942)": "temps",
    "Le Petit Journal (1863-1942)": "petit_journal",
    "Le Petit Parisien (1876-1944)": "petit_parisien",
    "L'Humanité (1904-1952)": "huma"
}

# Fonctions pour encoder et décoder l'état
def encode_state(state):
    json_str = json.dumps(state)
    return base64.urlsafe_b64encode(json_str.encode()).decode()

def decode_state(encoded_state):
    json_str = base64.urlsafe_b64decode(encoded_state.encode()).decode()
    return json.loads(json_str)

# Définir l'état par défaut
default_state = {
    'termes_recherche': "guerre, paix",
    'annee_debut': 1945,
    'annee_fin': 2024,
    'resolution': "Année",
    'titre_corpus': "Le Monde (1944-2024)"
}

# Vérifiez s'il y a un état dans l'URL
if 'state' in st.query_params:
    # Access query_params directly as it's a dict-like object
    state_param = st.query_params['state']
    # Check if it's a list (it usually is) and take the first element
    state_value = state_param[0] if isinstance(state_param, list) else state_param
    try:
        state = decode_state(state_value)
    except Exception as e:
        st.error(f"Erreur lors du décodage de l'état de l'URL: {e}. Utilisation de l'état par défaut.")
        state = default_state.copy()
else:
    state = default_state.copy()

def load_offline_data(debut, fin, resolution):
    try:
        guerre_df = pd.read_csv('guerre.csv')
        paix_df = pd.read_csv('paix.csv')
    except FileNotFoundError:
        st.sidebar.warning("Fichiers de données hors ligne (guerre.csv, paix.csv) non trouvés.")
        return pd.DataFrame() # Return empty DataFrame

    # Filtrer les données selon la plage de dates spécifiée
    guerre_df = guerre_df[(guerre_df['annee'] >= debut) & (guerre_df['annee'] <= fin)]
    paix_df = paix_df[(paix_df['annee'] >= debut) & (paix_df['annee'] <= fin)]

    if guerre_df.empty and paix_df.empty:
        return pd.DataFrame()

    # Appliquer le même traitement que dans obtenir_donnees_gallicagram
    if resolution.lower() == 'année':
        if not guerre_df.empty:
            guerre_df = guerre_df.groupby('annee')[['n', 'total']].sum().reset_index()
            guerre_df['ratio'] = guerre_df['n'] / guerre_df['total']
            guerre_df['date'] = pd.to_datetime(guerre_df['annee'].astype(str) + '-01-01')
        if not paix_df.empty:
            paix_df = paix_df.groupby('annee')[['n', 'total']].sum().reset_index()
            paix_df['ratio'] = paix_df['n'] / paix_df['total']
            paix_df['date'] = pd.to_datetime(paix_df['annee'].astype(str) + '-01-01')

    elif resolution.lower() == 'mois':
        if not guerre_df.empty:
            guerre_df['mois'] = guerre_df['mois'].astype(int).apply(lambda x: f'{x:02}')
            guerre_df = guerre_df.groupby(['annee', 'mois'])[['n', 'total']].sum().reset_index() # Added groupby for month
            guerre_df['ratio'] = guerre_df['n'] / guerre_df['total']
            guerre_df['date'] = pd.to_datetime(guerre_df['annee'].astype(str) + '-' + guerre_df['mois'] + '-01', format='%Y-%m-%d')
        if not paix_df.empty:
            paix_df['mois'] = paix_df['mois'].astype(int).apply(lambda x: f'{x:02}')
            paix_df = paix_df.groupby(['annee', 'mois'])[['n', 'total']].sum().reset_index() # Added groupby for month
            paix_df['ratio'] = paix_df['n'] / paix_df['total']
            paix_df['date'] = pd.to_datetime(paix_df['annee'].astype(str) + '-' + paix_df['mois'] + '-01', format='%Y-%m-%d')

    if not guerre_df.empty: guerre_df['terme'] = 'guerre'
    if not paix_df.empty: paix_df['terme'] = 'paix'

    # Concatenate, handling cases where one df might be empty
    dfs_to_concat = []
    if not guerre_df.empty: dfs_to_concat.append(guerre_df)
    if not paix_df.empty: dfs_to_concat.append(paix_df)
    
    if not dfs_to_concat:
        return pd.DataFrame()
        
    all_data = pd.concat(dfs_to_concat)
    return all_data[['date', 'ratio', 'terme']]


# Vérifier si les paramètres actuels correspondent aux paramètres par défaut
def is_default_params():
    return (termes_recherche == default_state['termes_recherche'] and
            annee_debut == default_state['annee_debut'] and
            annee_fin == default_state['annee_fin'] and
            resolution == default_state['resolution'] and
            titre_corpus == default_state['titre_corpus'])

sidebar_header_style = """
        <style>
        [data-testid="stSidebarHeader"] {
            padding: 10px !important; /* Réduire le padding */
            margin-bottom: -20px !important; /* Ajuster la marge en bas */
        }
        </style>
        """
st.markdown(sidebar_header_style, unsafe_allow_html=True)
# Entrées dans la barre latérale
termes_recherche = st.sidebar.text_area("Termes de recherche", value=state['termes_recherche'])
col1, col2 = st.sidebar.columns(2)
with col1:
    annee_debut = st.number_input("Début", min_value=1600, max_value=2024, value=state['annee_debut'])
with col2:
    annee_fin = st.number_input("Fin", min_value=1600, max_value=2024, value=state['annee_fin'])
resolution = st.sidebar.selectbox("Résolution", ["Année", "Mois"], index=["Année", "Mois"].index(state['resolution']))
titre_corpus = st.sidebar.selectbox("Corpus", list(corpus_mapping.keys()), index=list(corpus_mapping.keys()).index(state['titre_corpus']))

# Mettre à jour l'état et l'URL
current_state = {
    'termes_recherche': termes_recherche,
    'annee_debut': annee_debut,
    'annee_fin': annee_fin,
    'resolution': resolution,
    'titre_corpus': titre_corpus
}
encoded_state = encode_state(current_state)
st.query_params.state = encoded_state

corpus = corpus_mapping[titre_corpus]

# Fonction pour appeler l'API Gallicagram
def obtenir_donnees_gallicagram(terme, debut, fin, resolution_api, corpus_api): # Renamed params to avoid conflict
    terme_encode = requests.utils.quote(terme).lower()
    url = f"https://shiny.ens-paris-saclay.fr/guni/query?mot={terme_encode}&corpus={corpus_api}&from={debut}&to={fin}"
    if corpus_api == "query_persee" : # Use corpus_api
        url = f"https://shiny.ens-paris-saclay.fr/guni/query_persee?mot={terme_encode}&from={debut}&to={fin}"
    # print(url) # Good for debugging, consider removing for production
    try:
        response = requests.get(url, timeout=30) # Added timeout
        response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        donnees = pd.read_csv(url) # pd.read_csv can also take a URL
        if donnees.empty:
            st.warning(f"Aucune donnée retournée par l'API pour le terme '{terme}'.")
            return pd.DataFrame() # Return empty DataFrame

        if resolution_api.lower() == 'année': # Use resolution_api
            donnees_annee = donnees.groupby('annee')[['n', 'total']].sum().reset_index()
            donnees_annee['ratio'] = donnees_annee['n'] / donnees_annee['total']
            donnees_annee['date'] = pd.to_datetime(donnees_annee['annee'].astype(str) + '-01-01')
            return donnees_annee
        elif resolution_api.lower() == 'mois': # Use resolution_api
            donnees['mois'] = donnees['mois'].astype(int).apply(lambda x: f'{x:02}')
            donnees_mois = donnees.groupby(['annee','mois'])[['n', 'total']].sum().reset_index()
            donnees_mois['ratio'] = donnees_mois['n'] / donnees_mois['total']
            donnees_mois['date'] = pd.to_datetime(donnees_mois['annee'].astype(str) + '-' + donnees_mois['mois'] + '-01', format='%Y-%m-%d')
            return donnees_mois
        return pd.DataFrame() # Should not be reached if resolution is 'année' or 'mois'
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur réseau ou API pour le terme '{terme}': {e}")
        return pd.DataFrame() # Return empty DataFrame on error
    except pd.errors.EmptyDataError:
        st.warning(f"Aucune donnée (CSV vide) retournée par l'API pour le terme '{terme}'.")
        return pd.DataFrame()
    except KeyError as e:
        st.error(f"Colonne manquante ({e}) dans les données de l'API pour '{terme}'.")
        return pd.DataFrame()
    except Exception as e: # Catch any other unexpected errors
        st.error(f"Erreur inattendue lors du traitement des données pour '{terme}': {e}")
        return pd.DataFrame()


def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        st.error(f"Fichier logo '{bin_file}' non trouvé.")
        return None

def get_img_with_href(local_img_path, target_url):
    img_format = os.path.splitext(local_img_path)[-1].replace('.', '')
    bin_str = get_base64_of_bin_file(local_img_path)
    if bin_str is None: return "" # Return empty string if logo not found

    # MODIFICATION ICI: Ajout de margin-top négatif avec !important
    # Ajustez la valeur de -30px selon vos besoins.
    # `!important` est utilisé pour s'assurer que cette règle outrepasse
    # la règle `img { margin-top: 0 !important; }` de votre CSS mobile.
    # `display: block; margin-left: auto; margin-right: auto;` sont ajoutés pour un centrage cohérent
    # et pour s'assurer que `margin-top` fonctionne comme attendu pour un élément de type bloc.
    html_code = f'''
        <a href="{target_url}" target="_self" style="display: block; text-align: center;">
            <img src="data:image/{img_format};base64,{bin_str}" 
                 alt="Gallicagram" 
                 style="width: 200px; margin-top: -70px !important; display: block; margin-left: auto; margin-right: auto;"/>
        </a>'''
    return html_code

# Utilisation de la fonction
logo_html = get_img_with_href('logo_gallicagram.png', 'https://gallicagram.com/')
if logo_html: # Only display if logo was loaded
    st.markdown(logo_html, unsafe_allow_html=True)


plot_container = st.empty()

if "search_count" not in st.session_state:
    st.session_state.search_count = 0
if 'graph_data' not in st.session_state:
    st.session_state.graph_data = None
if 'last_search_params' not in st.session_state:
    st.session_state.last_search_params = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

def lancer_recherche():
    with st.spinner('Recherche en cours...'):
        termes_groupes = [groupe.strip() for groupe in termes_recherche.split(',') if groupe.strip()] # Added check for empty group
        if not termes_groupes:
            st.warning("Veuillez entrer au moins un terme de recherche.")
            st.session_state.graph_data = pd.DataFrame() # Clear graph for empty search
            st.session_state.search_performed = True # Mark search as performed (even if empty)
            return

        data_frames = []
        for groupe in termes_groupes:
            termes = [terme.strip() for terme in groupe.split('+') if terme.strip()] # Added check for empty term
            if not termes: continue # Skip empty groups like 'term1, , term2' or 'term1, ++, term2'

            donnees_sommees_groupe = None # Use a more descriptive name

            for terme_simple in termes: # Renamed 'terme' to 'terme_simple' to avoid conflict
                donnees_terme = obtenir_donnees_gallicagram(terme_simple, annee_debut, annee_fin, resolution, corpus) # Pass correct resolution and corpus

                if donnees_terme is not None and not donnees_terme.empty:
                    if 'date' not in donnees_terme.columns or 'ratio' not in donnees_terme.columns:
                        st.warning(f"Données incomplètes (colonnes 'date' ou 'ratio' manquantes) pour '{terme_simple}'. Il sera ignoré.")
                        continue

                    if donnees_sommees_groupe is None:
                        donnees_sommees_groupe = donnees_terme[['date', 'ratio']].copy()
                    else:
                        # Outer merge to keep all dates, fill missing ratios with 0 before summing
                        merged = pd.merge(donnees_sommees_groupe, donnees_terme[['date', 'ratio']], on='date', how='outer', suffixes=('_summed', '_new'))
                        merged['ratio_summed'] = merged['ratio_summed'].fillna(0)
                        merged['ratio_new'] = merged['ratio_new'].fillna(0)
                        merged['ratio'] = merged['ratio_summed'] + merged['ratio_new']
                        donnees_sommees_groupe = merged[['date', 'ratio']].copy()
                # else: No specific warning here, `obtenir_donnees_gallicagram` already warns

            if donnees_sommees_groupe is not None and not donnees_sommees_groupe.empty:
                donnees_sommees_groupe['terme'] = groupe
                data_frames.append(donnees_sommees_groupe)

        if data_frames:
            toutes_donnees = pd.concat(data_frames)
            if 'date' in toutes_donnees.columns and 'ratio' in toutes_donnees.columns and 'terme' in toutes_donnees.columns:
                st.session_state.graph_data = toutes_donnees
                st.session_state.last_search_params = current_state.copy() # Use current_state
                st.session_state.search_performed = True
            else:
                st.error("Les données finales pour le graphique sont incomplètes.")
                st.session_state.graph_data = pd.DataFrame() # Use empty DataFrame
        else:
            st.info("Aucune donnée trouvée pour les termes et paramètres spécifiés.")
            st.session_state.graph_data = pd.DataFrame() # Use empty DataFrame
            st.session_state.search_performed = True # Mark search as performed


def afficher_graphique():
    if isinstance(st.session_state.get('graph_data'), pd.DataFrame) and not st.session_state.graph_data.empty:
        try:
            if not {'date', 'ratio', 'terme'}.issubset(st.session_state.graph_data.columns):
                plot_container.warning("Données graphiques incomplètes (colonnes manquantes).")
                return

            fig = px.line(st.session_state.graph_data, x='date', y='ratio', color='terme', line_shape='spline',
                          labels={'ratio': 'Fréquence', 'date': 'Date', 'terme': 'Terme(s)'}, # Changed label
                          color_discrete_sequence=px.colors.qualitative.Set1)

            is_mobile_display = st.session_state.get('is_mobile', False)

            if is_mobile_display:
                fig.update_layout(
                    xaxis_title=None,
                    yaxis_title=None,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, title=None), # Centered legend
                    margin=dict(l=10, r=10, t=20, b=60) # Adjusted margins
                )
            else:
                fig.update_layout(
                    legend=dict(orientation="h", yanchor="bottom", y=-0.20, xanchor="center", x=0.5, title=None), # Centered legend
                    margin=dict(l=20, r=20, t=20, b=40) # Adjusted margins
                )
            plot_container.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            plot_container.error(f"Erreur lors de la création du graphique : {e}")
            # st.error(f"Données en erreur:\n{st.session_state.graph_data.head()}")
    elif st.session_state.search_performed and (st.session_state.graph_data is None or st.session_state.graph_data.empty):
        # If a search was done and resulted in no data, clear the plot area or show a message
        plot_container.empty() # Clears previous chart
        # Optionally, display a message in the plot_container if you want
        # plot_container.info("Aucune donnée à afficher pour les paramètres actuels.")
    # else:
        # Initial load, or data cleared for other reasons.
        # plot_container.empty() # Clears previous content

# --- Main Logic ---

# Load offline data if default params and no search performed yet
if is_default_params() and not st.session_state.search_performed:
    # Check if files exist using os.path.exists
    if os.path.exists('guerre.csv') and os.path.exists('paix.csv'):
        offline_data = load_offline_data(annee_debut, annee_fin, resolution)
        if isinstance(offline_data, pd.DataFrame) and not offline_data.empty:
            st.session_state.graph_data = offline_data
            # Don't set search_performed here, this is pre-search default display
        # else:
            # load_offline_data will show a warning if files not found or data is empty
            # st.session_state.graph_data = pd.DataFrame() # Ensure it's an empty df
    else:
        # Files not found, load_offline_data will also show a warning if called,
        # but we can add a specific one here if we don't call it.
        # st.sidebar.warning("Fichiers par défaut (guerre.csv, paix.csv) non trouvés pour l'affichage initial.")
        st.session_state.graph_data = pd.DataFrame() # Ensure it's an empty df


# Sidebar buttons
sidebar_col1, sidebar_col2 = st.sidebar.columns(2) # Renamed to avoid conflict with other col1, col2

with sidebar_col1:
    trigger_search = st.button("🔎Rechercher", key="search_button_main", use_container_width=True)

# Logic to run search:
# 1. If search button is clicked.
# 2. On initial load IF NOT default params (meaning URL params were different from default).
# 3. On initial load IF default params BUT offline data failed to load/was empty AND no search has been done yet.

initial_load_trigger = False
if not st.session_state.search_performed: # Only consider initial load triggers if no search has happened
    if not is_default_params():
        initial_load_trigger = True
    elif is_default_params() and (st.session_state.graph_data is None or st.session_state.graph_data.empty):
        # This case handles when default files are missing/empty and we want to trigger an API search
        initial_load_trigger = True


if trigger_search or initial_load_trigger:
    # Check if params actually changed since last successful search OR if it's a fresh trigger
    # This prevents re-searching if button is spammed without param changes AFTER a successful search.
    # For initial_load_trigger, last_search_params would be None, so it always proceeds.
    if trigger_search or st.session_state.last_search_params != current_state or initial_load_trigger:
        st.session_state.search_count += 1
        lancer_recherche()
    # If trigger_search is true but params haven't changed from last_search_params,
    # it implies the user clicked search again on the same data.
    # We don't need to re-run lancer_recherche, afficher_graphique will handle it.

# --- Display Area ---
afficher_graphique()

# Warning for changed parameters
if st.session_state.get('last_search_params') and st.session_state.last_search_params != current_state:
    st.warning("Les paramètres ont changé. Cliquez sur 'Rechercher' pour mettre à jour le graphique.")

