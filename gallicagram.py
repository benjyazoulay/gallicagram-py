import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import json
from streamlit_javascript import st_javascript
from user_agents import parse
import html
import requests.utils
import os

st.set_page_config(page_title="Gallicagram", page_icon="https://github.com/user-attachments/assets/6011b645-fba6-4e16-9f39-d54add706fa2", layout="wide", menu_items=None)

# Injecter du CSS pour masquer la barre par défaut de Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
    cookies = st.experimental_get_query_params()
    return cookies.get('is_mobile', ['false'])[0] == 'true'

# Lire si c'est mobile à partir du cookie
is_mobile = get_is_mobile_from_cookie()


def generate_share_url():
    base_url = st.experimental_get_query_params().get('state', [''])[0]
    return f"https://gallicagram.streamlit.app/?state={base_url}"
def share_url():
    share_url = generate_share_url()
    st.text_input("URL de partage :", value=share_url, key="share_url_input")
    st.info("Copiez l'URL ci-dessus pour la partager.")

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

# Vérifier s'il y a un état dans l'URL
if 'state' in st.experimental_get_query_params():
    state = decode_state(st.experimental_get_query_params()['state'][0])
else:
    state = default_state.copy()

def load_offline_data(debut, fin, resolution):
    guerre_df = pd.read_csv('guerre.csv')
    paix_df = pd.read_csv('paix.csv')
    
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
            padding: 10px !important; /* Réduire le padding à zéro */
            margin-bottom: -20px !important; /* Ajuster la marge en bas pour réduire la hauteur */
        }
        </style>
        """
st.markdown(sidebar_header_style, unsafe_allow_html=True)
# Entrées dans la barre latérale
termes_recherche = st.sidebar.text_area("Termes de recherche", value=state['termes_recherche'])
col1, col2 = st.sidebar.columns(2)
with col1:
    annee_debut = st.number_input("Début", min_value=1700, max_value=2024, value=state['annee_debut'])
with col2:
    annee_fin = st.number_input("Fin", min_value=1700, max_value=2024, value=state['annee_fin'])
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
st.experimental_set_query_params(state=encode_state(current_state))

# Obtenir le code API correspondant au corpus sélectionné
corpus = corpus_mapping[titre_corpus]

# Fonction pour appeler l'API Gallicagram
def obtenir_donnees_gallicagram(terme, debut, fin, resolution, corpus):
    terme_encode = requests.utils.quote(terme)
    url = f"https://shiny.ens-paris-saclay.fr/guni/query?mot={terme_encode}&corpus={corpus}&from={debut}&to={fin}"
    if corpus == "query_persee" :
        url = f"https://shiny.ens-paris-saclay.fr/guni/query_persee?mot={terme_encode}&from={debut}&to={fin}"
    print(url)
    response = requests.get(url)
    if response.status_code == 200:
        donnees = pd.read_csv(url)
        if resolution.lower() == 'année':
            donnees_annee = donnees.groupby('annee')[['n', 'total']].sum().reset_index()
            donnees_annee['ratio'] = donnees_annee['n'] / donnees_annee['total']
            donnees_annee['date'] = pd.to_datetime(donnees_annee['annee'].astype(str) + '-01-01')
            return donnees_annee
        elif resolution.lower() == 'mois':
            donnees['mois'] = donnees['mois'].astype(int).apply(lambda x: f'{x:02}')
            donnees_mois = donnees.groupby(['annee','mois'])[['n', 'total']].sum().reset_index()
            donnees_mois['ratio'] = donnees_mois['n'] / donnees_mois['total']
            donnees_mois['date'] = pd.to_datetime(donnees_mois['annee'].astype(str) + '-' + donnees_mois['mois'] + '-01', format='%Y-%m-%d')
            return donnees_mois
    else:
        st.error("Erreur lors de la récupération des données depuis l'API")
        return None
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def get_img_with_href(local_img_path, target_url):
    img_format = os.path.splitext(local_img_path)[-1].replace('.', '')
    bin_str = get_base64_of_bin_file(local_img_path)
    html_code = f'''
        <a href="{target_url}" target="_self">
            <img src="data:image/{img_format};base64,{bin_str}" alt="Gallicagram" style="width: 200px;"/>
        </a>'''
    return html_code

# Utilisation de la fonction
logo_html = get_img_with_href('logo_gallicagram.png', 'https://gallicagram.com/')
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

# Modifiez la fonction lancer_recherche pour stocker les données dans l'état de session
def lancer_recherche():
    with st.spinner('Recherche en cours...'):
        termes_groupes = [groupe.strip() for groupe in termes_recherche.split(',')]
        if termes_groupes:
            data_frames = []
            for groupe in termes_groupes:
                termes = [terme.strip() for terme in groupe.split('+')]
                donnees_sommees = None
                for terme in termes:
                    donnees = obtenir_donnees_gallicagram(terme, annee_debut, annee_fin, resolution.lower(), corpus)
                    if donnees is not None:
                        donnees['ratio'] = donnees['n'] / donnees['total']
                        if donnees_sommees is None:
                            donnees_sommees = donnees[['date', 'ratio']].copy()
                        else:
                            donnees_sommees['ratio'] += donnees['ratio']

                if donnees_sommees is not None:
                    donnees_sommees['terme'] = '+'.join(termes)
                    data_frames.append(donnees_sommees)

            if data_frames:
                toutes_donnees = pd.concat(data_frames)
                st.session_state.graph_data = toutes_donnees
                st.session_state.last_search_params = {
                    'termes_recherche': termes_recherche,
                    'annee_debut': annee_debut,
                    'annee_fin': annee_fin,
                    'resolution': resolution,
                    'titre_corpus': titre_corpus
                }
            else:
                st.error("Aucune donnée disponible pour les termes recherchés.")

# Fonction pour afficher le graphique
def afficher_graphique():
    if st.session_state.graph_data is not None:
        fig = px.line(st.session_state.graph_data, x='date', y='ratio', color='terme', line_shape='spline',
              labels={'ratio': 'Fréquence', 'date': 'Date', 'terme': 'Terme de recherche'},
              color_discrete_sequence=px.colors.qualitative.Set1)
        
        if st.session_state.is_mobile:
            fig.update_layout(
                xaxis_title=None,
                yaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=-0.20, xanchor="left", x=0, title=None),
                margin=dict(l=0, r=0, t=0, b=60)
            )
        else:
            fig.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=-0.20, xanchor="left", x=0, title=None),
                margin=dict(l=0, r=0, t=0, b=40)
            )

        plot_container.plotly_chart(fig, use_container_width=True)

# Logique principale
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

if is_default_params() and not st.session_state.search_performed:
    # Charger et afficher les données hors ligne si les paramètres sont par défaut
    if os.path.exists('guerre.csv') and os.path.exists('paix.csv'):
        offline_data = load_offline_data(annee_debut, annee_fin, resolution)
        st.session_state.graph_data = offline_data
        afficher_graphique()
    else:
        st.warning("Fichiers de données hors ligne non trouvés. Utilisez le bouton 'Rechercher' pour obtenir les données en ligne.")

col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("🔎Rechercher") or not st.session_state.search_performed:
        st.session_state.search_count += 1
        lancer_recherche()
        st.session_state.search_performed = True

with col2:
    if st.button("📤Partager", key="share_button"):
        share_url()

# Affichez toujours le graphique s'il existe des données
afficher_graphique()

# Ajoutez un avertissement si les paramètres ont changé depuis la dernière recherche
if st.session_state.last_search_params:
    current_params = {
        'termes_recherche': termes_recherche,
        'annee_debut': annee_debut,
        'annee_fin': annee_fin,
        'resolution': resolution,
        'titre_corpus': titre_corpus
    }
    if current_params != st.session_state.last_search_params:
        st.warning("Cliquez sur 'Rechercher' pour mettre à jour le graphique.")
