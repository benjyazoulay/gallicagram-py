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

st.set_page_config(page_title="Gallicagram", layout="wide", menu_items=None)

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


# Mapping des titres de corpus vers leurs codes API
corpus_mapping = {
    "Le Monde (1944-2023)": "lemonde",
    "Presse de Gallica (1789-1950)": "presse",
    "Livres de Gallica (1600-1940)": "livres",
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
    "L'Humanité (1904-1952)": "huma",
    "Opensubtitles (français, 1935-2020)": "subtitles",
    "Opensubtitles (anglais, 1930-2020)": "subtitles_en",
    "Rap (Genius, 1989-février 2024)": "rap",
    "Persée (1789-2023)": "query_persee"
}

# Fonctions pour encoder et décoder l'état
def encode_state(state):
    json_str = json.dumps(state)
    return base64.urlsafe_b64encode(json_str.encode()).decode()

def decode_state(encoded_state):
    json_str = base64.urlsafe_b64decode(encoded_state.encode()).decode()
    return json.loads(json_str)

# Vérifier s'il y a un état dans l'URL
if 'state' in st.experimental_get_query_params():
    state = decode_state(st.experimental_get_query_params()['state'][0])
else:
    state = {
        'termes_recherche': "guerre, paix",
        'annee_debut': 1945,
        'annee_fin': 2022,
        'resolution': "Année",
        'titre_corpus': "Le Monde (1944-2023)"
    }

# Entrées dans la barre latérale
termes_recherche = st.sidebar.text_area("Termes de recherche", value=state['termes_recherche'])
col1, col2 = st.sidebar.columns(2)
with col1:
    annee_debut = st.number_input("Début", min_value=1700, max_value=2023, value=state['annee_debut'])
with col2:
    annee_fin = st.number_input("Fin", min_value=1700, max_value=2023, value=state['annee_fin'])
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
st.markdown("""
    <a href="https://gallicagram.streamlit.app/" target="_self">
        <img src="https://github.com/user-attachments/assets/58e05d4b-04de-45c7-8bbc-5e69e76ecfd4" alt="Gallicagram" style="width: 200px;"/>
    </a>
    """, unsafe_allow_html=True)


plot_container = st.empty()
# Fonction pour lancer la recherche
def lancer_recherche():
    with st.spinner('Recherche en cours...'):
        termes = [terme.strip() for terme in termes_recherche.split(',')]
        if termes:
            data_frames = []
            for terme in termes:
                donnees = obtenir_donnees_gallicagram(terme, annee_debut, annee_fin, resolution.lower(), corpus)
                if donnees is not None:
                    donnees['terme'] = terme
                    data_frames.append(donnees)
            if data_frames:
                toutes_donnees = pd.concat(data_frames)
                fig = px.line(toutes_donnees, x='date', y='ratio', color='terme', line_shape = 'spline",
                              labels={'ratio': 'Fréquence', 'date': 'Date', 'terme': 'Terme de recherche'})
                # Supprimer les titres des axes si on est sur mobile
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

                # Utiliser un conteneur pour mettre à jour ou remplacer le graphique
                plot_container.plotly_chart(fig, use_container_width=True)
            else:
                st.error("Aucune donnée disponible pour les termes recherchés.")


# Lancer la recherche automatiquement
lancer_recherche()

# Ajouter un bouton pour lancer la recherche manuellement
if st.sidebar.button("Rechercher"):
    lancer_recherche()
