import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import json
from streamlit_javascript import st_javascript
from user_agents import parse
import html # <-- Ajouté pour html.escape
import requests.utils
import os
import time # <-- Ajouté pour les ID uniques

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
    # Utiliser st.query_params.get qui retourne une liste, ou None
    is_mobile_param = st.query_params.get('is_mobile')
    if is_mobile_param:
        return is_mobile_param[0] == 'true'
    return False # Par défaut à False si le param n'existe pas

# Lire si c'est mobile à partir du cookie
is_mobile = get_is_mobile_from_cookie()


def generate_share_url():
    # Utiliser st.query_params.get qui retourne une liste, ou None
    state_param = st.query_params.get('state')
    if state_param:
        base_url_param = state_param[0] # Accéder au premier élément si la liste n'est pas vide
        return f"https://gallicagram.streamlit.app/?state={base_url_param}"
    return "https://gallicagram.streamlit.app/" # URL par défaut si pas de state


# MODIFICATION ICI: Fonction pour afficher l'URL et un bouton de copie
def display_share_interface():
    share_url_value = generate_share_url()
    
    # Ce conteneur est optionnel mais peut aider à regrouper la sortie
    # Surtout si vous voulez l'effacer plus tard.
    # Pour l'instant, nous allons écrire directement dans la sidebar.
    # share_container = st.sidebar.container() # Ou st.container() si ailleurs

    # Avec st.sidebar.container() ou st.container(), utiliser share_container.write, .code, .markdown
    # Sinon, utiliser st.write, st.code, st.markdown directement (pour affichage direct dans la sidebar)

    st.write("Lien de partage :")
    st.code(share_url_value, language="text")

    button_id = f"copy_button_{int(time.time() * 1000)}"
    status_id = f"copy_status_{int(time.time() * 1000)}"
    escaped_url_for_js = json.dumps(share_url_value) # Correctement échappe l'URL pour JS

    # 1. Afficher le HTML visible (bouton et span)
    visible_html = f"""
        <button id="{button_id}" style="padding: 0.25em 0.5em; margin-top: 5px; border-radius: 4px; border: 1px solid #ccc; background-color: #f0f0f0; cursor: pointer;">
            Copier dans le presse-papiers
        </button>
        <span id="{status_id}" style="margin-left: 10px; font-size: 0.9em;"></span>
    """
    st.markdown(visible_html, unsafe_allow_html=True)

    # 2. Injecter le script JavaScript séparément
    # Le script trouvera les éléments par ID car ils sont déjà dans le DOM
    script_js = f"""
        <script>
            (function() {{ // IIFE pour éviter de polluer le scope global
                var copyButton = document.getElementById('{button_id}');
                var copyStatus = document.getElementById('{status_id}');
                
                if (copyButton && copyStatus) {{
                    copyButton.addEventListener('click', function() {{
                        navigator.clipboard.writeText({escaped_url_for_js}).then(function() {{
                            copyStatus.textContent = 'Copié !';
                            copyStatus.style.color = 'green';
                            setTimeout(function() {{ copyStatus.textContent = ''; }}, 2000);
                        }}, function(err) {{
                            copyStatus.textContent = 'Échec copie';
                            copyStatus.style.color = 'red';
                            console.error('Erreur de copie dans le presse-papiers: ', err);
                            // Afficher une alerte peut être utile si la console n'est pas visible
                            // alert('Erreur de copie. Assurez-vous que la page a le focus et que vous utilisez HTTPS.');
                            setTimeout(function() {{ copyStatus.textContent = ''; }}, 3000);
                        }});
                    }});
                }} else {{
                    if (!copyButton) console.error("Bouton de copie non trouvé : {button_id}");
                    if (!copyStatus) console.error("Élément de statut de copie non trouvé : {status_id}");
                }}
            }})();
        </script>
    """
    st.markdown(copy_js, unsafe_allow_html=True)

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
# Utiliser st.query_params.get qui retourne une liste, ou None
state_param_from_url = st.query_params.get('state')
if state_param_from_url:
    try:
        state = decode_state(state_param_from_url[0])
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
        return pd.DataFrame() # Retourner un DataFrame vide en cas d'erreur

    # Filtrer les données selon la plage de dates spécifiée
    guerre_df = guerre_df[(guerre_df['annee'] >= debut) & (guerre_df['annee'] <= fin)]
    paix_df = paix_df[(paix_df['annee'] >= debut) & (paix_df['annee'] <= fin)]
    
    # Appliquer le même traitement que dans obtenir_donnees_gallicagram
    if resolution.lower() == 'année':
        guerre_df = guerre_df.groupby('annee')[['n', 'total']].sum().reset_index()
        paix_df = paix_df.groupby('annee')[['n', 'total']].sum().reset_index()
        
        guerre_df['ratio'] = guerre_df['n'] / guerre_df['total']
        paix_df['ratio'] = paix_df['n'] / paix_df['total']
        
        guerre_df['date'] = pd.to_datetime(guerre_df['annee'].astype(str) + '-01-01')
        paix_df['date'] = pd.to_datetime(paix_df['annee'].astype(str) + '-01-01')
    elif resolution.lower() == 'mois':
        guerre_df['mois'] = guerre_df['mois'].astype(int).apply(lambda x: f'{x:02}')
        paix_df['mois'] = paix_df['mois'].astype(int).apply(lambda x: f'{x:02}')
        
        guerre_df['date'] = pd.to_datetime(guerre_df['annee'].astype(str) + '-' + guerre_df['mois'] + '-01', format='%Y-%m-%d')
        paix_df['date'] = pd.to_datetime(paix_df['annee'].astype(str) + '-' + paix_df['mois'] + '-01', format='%Y-%m-%d')
        
        guerre_df['ratio'] = guerre_df['n'] / guerre_df['total']
        paix_df['ratio'] = paix_df['n'] / paix_df['total']
    
    guerre_df['terme'] = 'guerre'
    paix_df['terme'] = 'paix'
    
    all_data = pd.concat([guerre_df, paix_df])
    if 'date' in all_data.columns and 'ratio' in all_data.columns and 'terme' in all_data.columns:
        return all_data[['date', 'ratio', 'terme']]
    else:
        st.warning("Les données hors ligne n'ont pas pu être formatées correctement.")
        return pd.DataFrame()


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
            padding: 10px !important; /* Réduire le padding à zéro */
            margin-bottom: -20px !important; /* Ajuster la marge en bas pour réduire la hauteur */
        }
        </style>
        """
st.markdown(sidebar_header_style, unsafe_allow_html=True)
# Entrées dans la barre latérale
termes_recherche = st.sidebar.text_area("Termes de recherche", value=state.get('termes_recherche', default_state['termes_recherche']))
col1, col2 = st.sidebar.columns(2)
with col1:
    annee_debut = st.number_input("Début", min_value=1600, max_value=2024, value=state.get('annee_debut', default_state['annee_debut']))
with col2:
    annee_fin = st.number_input("Fin", min_value=1600, max_value=2024, value=state.get('annee_fin', default_state['annee_fin']))

# S'assurer que les valeurs par défaut de selectbox sont valides
default_resolution_index = 0
if state.get('resolution', default_state['resolution']) in ["Année", "Mois"]:
    default_resolution_index = ["Année", "Mois"].index(state.get('resolution', default_state['resolution']))

default_corpus_index = 0
if state.get('titre_corpus', default_state['titre_corpus']) in list(corpus_mapping.keys()):
    default_corpus_index = list(corpus_mapping.keys()).index(state.get('titre_corpus', default_state['titre_corpus']))

resolution = st.sidebar.selectbox("Résolution", ["Année", "Mois"], index=default_resolution_index)
titre_corpus = st.sidebar.selectbox("Corpus", list(corpus_mapping.keys()), index=default_corpus_index)


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

# Obtenir le code API correspondant au corpus sélectionné
corpus = corpus_mapping[titre_corpus]

# Fonction pour appeler l'API Gallicagram
def obtenir_donnees_gallicagram(terme, debut, fin, resolution_api, corpus_api):
    terme_encode = requests.utils.quote(terme).lower()
    base_api_url = "https://shiny.ens-paris-saclay.fr/guni"
    
    if corpus_api == "query_persee":
        url = f"{base_api_url}/query_persee?mot={terme_encode}&from={debut}&to={fin}"
    elif corpus_api == "lemonde_rubriques":
         url = f"{base_api_url}/lemonde_rubriques?mot={terme_encode}&from={debut}&to={fin}"
    else:
        url = f"{base_api_url}/query?mot={terme_encode}&corpus={corpus_api}&from={debut}&to={fin}"
    
    # print(f"Appel API: {url}") # Utile pour le débogage
    try:
        response = requests.get(url, timeout=30) # Ajout d'un timeout
        response.raise_for_status() # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
        
        donnees = pd.read_csv(url) # ou io.StringIO(response.text) si response.text est utilisé
        
        if donnees.empty:
            # st.info(f"Aucune donnée trouvée pour le terme '{terme}' dans le corpus '{corpus_api}'.")
            return pd.DataFrame(columns=['date', 'ratio']) # Retourner un DataFrame vide avec les colonnes attendues

        if resolution_api.lower() == 'année':
            donnees_annee = donnees.groupby('annee')[['n', 'total']].sum().reset_index()
            donnees_annee['ratio'] = donnees_annee['n'] / donnees_annee['total']
            donnees_annee['date'] = pd.to_datetime(donnees_annee['annee'].astype(str) + '-01-01')
            return donnees_annee[['date', 'ratio']] # S'assurer de retourner que les colonnes nécessaires
        elif resolution_api.lower() == 'mois':
            if 'mois' not in donnees.columns: # Cas où le corpus ne renvoie pas de 'mois'
                # st.warning(f"Le corpus '{corpus_api}' ne supporte pas la résolution par mois. Affichage par année.")
                donnees_annee = donnees.groupby('annee')[['n', 'total']].sum().reset_index()
                donnees_annee['ratio'] = donnees_annee['n'] / donnees_annee['total']
                donnees_annee['date'] = pd.to_datetime(donnees_annee['annee'].astype(str) + '-01-01')
                return donnees_annee[['date', 'ratio']]

            donnees['mois'] = donnees['mois'].astype(int).apply(lambda x: f'{x:02}')
            donnees_mois = donnees.groupby(['annee','mois'])[['n', 'total']].sum().reset_index()
            donnees_mois['ratio'] = donnees_mois['n'] / donnees_mois['total']
            donnees_mois['date'] = pd.to_datetime(donnees_mois['annee'].astype(str) + '-' + donnees_mois['mois'] + '-01', format='%Y-%m-%d')
            return donnees_mois[['date', 'ratio']] # S'assurer de retourner que les colonnes nécessaires
            
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion à l'API pour '{terme}': {e}")
        return pd.DataFrame(columns=['date', 'ratio'])
    except pd.errors.EmptyDataError:
        st.info(f"Aucune donnée retournée par l'API pour '{terme}'.")
        return pd.DataFrame(columns=['date', 'ratio'])
    except Exception as e:
        st.error(f"Erreur lors du traitement des données pour '{terme}': {e}")
        return pd.DataFrame(columns=['date', 'ratio'])
    return None # Ne devrait pas être atteint si les return pd.DataFrame sont bien placés

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        st.error(f"Fichier image '{bin_file}' non trouvé.")
        return None


def get_img_with_href(local_img_path, target_url):
    img_format = os.path.splitext(local_img_path)[-1].replace('.', '')
    bin_str = get_base64_of_bin_file(local_img_path)
    if bin_str:
        html_code = f'''
            <a href="{target_url}" target="_self">
                <img src="data:image/{img_format};base64,{bin_str}" alt="Gallicagram" style="width: 200px;"/>
            </a>'''
        return html_code
    return ""


# Utilisation de la fonction
logo_html = get_img_with_href('logo_gallicagram.png', 'https://gallicagram.com/')
if logo_html: # Afficher seulement si l'image a été chargée
    st.markdown(logo_html, unsafe_allow_html=True)


plot_container = st.empty()

# Initialiser le compteur dans st.session_state
if "search_count" not in st.session_state:
    st.session_state.search_count = 0

# Ajoutez ces lignes pour initialiser l'état de session
if 'graph_data' not in st.session_state:
    st.session_state.graph_data = None
if 'last_search_params' not in st.session_state:
    st.session_state.last_search_params = None
if 'search_performed' not in st.session_state: # Initialize search_performed
    st.session_state.search_performed = False

# Modifiez la fonction lancer_recherche pour stocker les données dans l'état de session
def lancer_recherche():
    with st.spinner('Recherche en cours...'):
        termes_groupes = [groupe.strip() for groupe in termes_recherche.split(',') if groupe.strip()]
        if not termes_groupes:
            st.warning("Veuillez entrer au moins un terme de recherche.")
            st.session_state.graph_data = None # Effacer les données précédentes
            st.session_state.search_performed = True # Marquer qu'une "recherche" (vide) a été tentée
            return

        data_frames = []
        for groupe_label in termes_groupes: # 'groupe_label' est par ex. "terme1+terme2"
            termes_dans_groupe = [terme.strip() for terme in groupe_label.split('+') if terme.strip()]
            
            if not termes_dans_groupe:
                continue # Passer au groupe suivant si celui-ci est vide après nettoyage

            donnees_groupe_sommees = None

            for terme_simple in termes_dans_groupe:
                donnees_terme_simple = obtenir_donnees_gallicagram(terme_simple, annee_debut, annee_fin, resolution.lower(), corpus)

                if donnees_terme_simple is not None and not donnees_terme_simple.empty:
                    if 'date' not in donnees_terme_simple.columns or 'ratio' not in donnees_terme_simple.columns:
                        # st.warning(f"Données incomplètes pour '{terme_simple}'. Ignoré.")
                        continue
                    
                    if donnees_groupe_sommees is None:
                        donnees_groupe_sommees = donnees_terme_simple[['date', 'ratio']].copy()
                    else:
                        # Fusionner sur 'date' et sommer les 'ratio'
                        merged = pd.merge(donnees_groupe_sommees, donnees_terme_simple[['date', 'ratio']], on='date', how='outer', suffixes=('_left', '_right'))
                        merged['ratio'] = merged['ratio_left'].fillna(0) + merged['ratio_right'].fillna(0)
                        donnees_groupe_sommees = merged[['date', 'ratio']].copy()
                # else:
                    # st.info(f"Aucune donnée pour '{terme_simple}'.")


            if donnees_groupe_sommees is not None and not donnees_groupe_sommees.empty:
                donnees_groupe_sommees['terme'] = groupe_label # Utiliser le label du groupe
                data_frames.append(donnees_groupe_sommees)
            # elif groupe_label: # S'il y avait un label mais pas de données
                # st.warning(f"Aucune donnée trouvée pour le groupe de termes '{groupe_label}'.")


        if data_frames:
            toutes_donnees = pd.concat(data_frames)
            if 'date' in toutes_donnees.columns and 'ratio' in toutes_donnees.columns and 'terme' in toutes_donnees.columns:
               st.session_state.graph_data = toutes_donnees
               st.session_state.last_search_params = current_state.copy() # Utiliser current_state déjà défini
               st.session_state.search_performed = True
            else:
               st.error("Les données finales générées sont incomplètes.")
               st.session_state.graph_data = None
               st.session_state.search_performed = True # Marquer comme effectué même si erreur
        else:
            st.info("Aucune donnée disponible pour les termes recherchés après traitement.")
            st.session_state.graph_data = None
            st.session_state.search_performed = True


# Fonction pour afficher le graphique
def afficher_graphique():
    if isinstance(st.session_state.get('graph_data'), pd.DataFrame) and not st.session_state.graph_data.empty:
        try:
            if {'date', 'ratio', 'terme'}.issubset(st.session_state.graph_data.columns):
                # S'assurer que 'date' est bien de type datetime
                st.session_state.graph_data['date'] = pd.to_datetime(st.session_state.graph_data['date'])
                
                fig = px.line(st.session_state.graph_data, x='date', y='ratio', color='terme', line_shape='spline',
                      labels={'ratio': 'Fréquence relative (pour 1000 mots)', 'date': 'Date', 'terme': 'Terme(s) de recherche'},
                      color_discrete_sequence=px.colors.qualitative.Set1)

                is_mobile_display = st.session_state.get('is_mobile', False)

                fig.update_yaxes(title_text='Fréquence (pour 1000 mots)')


                if is_mobile_display:
                    fig.update_layout(
                        xaxis_title=None,
                        # yaxis_title=None, # Gardons le titre Y pour la clarté
                        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="left", x=0, title=None), # Augmenter y négatif
                        margin=dict(l=0, r=0, t=0, b=80) # Augmenter la marge du bas
                    )
                else:
                    fig.update_layout(
                        legend=dict(orientation="h", yanchor="bottom", y=-0.20, xanchor="left", x=0, title=None),
                        margin=dict(l=0, r=0, t=0, b=60) # Marge en bas un peu plus grande
                    )
                
                fig.update_traces(hovertemplate="<b>%{fullData.name}</b><br>Date: %{x|%Y-%m-%d}<br>Fréquence: %{y:.6f}<extra></extra>")


                plot_container.plotly_chart(fig, use_container_width=True)
            else:
                plot_container.warning("Les données à afficher sont incomplètes (colonnes manquantes).")
        except Exception as e:
            plot_container.error(f"Erreur lors de la création du graphique : {e}")
            # st.error(f"Données en erreur (premières lignes):\n{st.session_state.graph_data.head().to_markdown()}")
    elif st.session_state.search_performed and st.session_state.graph_data is None : # Si une recherche a été faite mais pas de données
        plot_container.info("Aucune donnée à afficher pour les paramètres actuels.")
    # else:
         # plot_container.empty() # Optionnel: vider si aucune donnée et aucune recherche effectuée


# --- Main Logic ---

# Charger les données hors ligne si c'est le premier chargement avec les paramètres par défaut
if not st.session_state.search_performed and is_default_params():
    if os.path.exists('guerre.csv') and os.path.exists('paix.csv'):
        offline_data = load_offline_data(annee_debut, annee_fin, resolution)
        if isinstance(offline_data, pd.DataFrame) and not offline_data.empty:
            st.session_state.graph_data = offline_data
            st.session_state.last_search_params = default_state.copy()
            # Ne pas mettre search_performed à True ici, pour que la première recherche en ligne soit possible
        # else:
            # st.sidebar.warning("Les données hors ligne n'ont pas pu être chargées correctement.")
            # st.session_state.graph_data = None
    # else:
        # st.sidebar.warning("Fichiers par défaut (guerre.csv, paix.csv) non trouvés. Lancez une recherche.")
        # st.session_state.graph_data = None


# Sidebar buttons
col_btn1, col_btn2 = st.sidebar.columns(2)

with col_btn1:
    if st.button("🔎Rechercher", key="search_button_main", use_container_width=True):
        st.session_state.search_count += 1
        lancer_recherche()

with col_btn2:
    if st.button("📤Partager", key="share_button", use_container_width=True):
        display_share_interface() # MODIFICATION ICI: Appel de la nouvelle fonction

# --- Display Area ---
# Afficher le graphique si des données sont disponibles (soit hors ligne, soit après recherche)
# ou si une recherche a été explicitement lancée (pour afficher les messages d'erreur/info)
if st.session_state.graph_data is not None or st.session_state.search_performed:
    afficher_graphique()


# Avertissement si les paramètres ont changé et qu'une recherche précédente a été effectuée
if st.session_state.get('last_search_params'):
    current_params_for_check = {
        'termes_recherche': termes_recherche, 'annee_debut': annee_debut,
        'annee_fin': annee_fin, 'resolution': resolution, 'titre_corpus': titre_corpus
    }
    if current_params_for_check != st.session_state.last_search_params:
        if plot_container.empty(): # Pour éviter d'écraser un message d'erreur de afficher_graphique
             plot_container.warning("Les paramètres ont changé. Cliquez sur 'Rechercher' pour mettre à jour le graphique.")
        else: # Si plot_container n'est pas vide, c'est qu'un graphique ou un message est déjà affiché.
              # On peut ajouter un avertissement séparé en dessous.
            st.warning("Les paramètres ont changé. Cliquez sur 'Rechercher' pour mettre à jour le graphique.")
