import subprocess
import logging
import json
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from sentence_transformers import SentenceTransformer, util
from mots_listes import SOCIETES, INTERMEDIAIRES, MOTS_CLES

CHECKPOINT_FILE = "checkpoint8.json"

# --- Charger checkpoint ---
def charger_checkpoint(path=CHECKPOINT_FILE):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            contenu = f.read().strip()
            if not contenu:
                raise ValueError("Fichier checkpoint vide")
            return json.loads(contenu)
    except Exception as e:
        logging.error(f"Erreur chargement checkpoint: {e}")
        return {"articles_resume": []}

# --- Scraper article ---
def recuperer_contenu_article(url):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        article_tag = soup.find("article")
        if article_tag:
            paragraphs = article_tag.find_all("p")
        else:
            paragraphs = soup.find_all("p")
        return "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
    except Exception as e:
        logging.error(f"Erreur récupération contenu {url} : {e}")
        return ""

# --- Factuel Ollama ---
def verifier_resume_factuel(article):
    contenu = article.get("contenu", "")
    resume = article.get("resume", "")
    if not resume or not contenu:
        return 0

    prompt = (
        "Tu es un assistant expert en finance.\n"
        "Compare le résumé suivant avec le texte original et réponds par un score de 0 à 1 :\n"
        "- 1 = résumé parfaitement fidèle.\n"
        "- 0 = résumé incorrect ou hors sujet.\n\n"
        f"Texte original :\n{contenu[:4000]}\n\n"
        f"Résumé :\n{resume}\n\n"
        "Réponds uniquement par un nombre entre 0 et 1."
    )
    try:
        cmd = ['ollama', 'run', 'mistral', prompt]
        resultat = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=180, encoding='utf-8')
        score = float(resultat.stdout.strip())
        return max(0, min(score, 1))
    except Exception as e:
        logging.error(f"Erreur vérification factuelle Ollama : {e}")
        return 0

# --- Contexte fuzzy ---
def score_fuzzy(resume, mots_cles, societes, intermediaires, seuil=80):
    if not resume:
        return 0
    resume = resume.lower()
    total = len(mots_cles) + len(societes) + len(intermediaires)
    if total == 0:
        return 1
    trouves = sum(fuzz.partial_ratio(mot.lower(), resume) >= seuil 
                  for mot in mots_cles + societes + intermediaires)
    return trouves / total

# --- Contexte embeddings ---
model = SentenceTransformer('all-MiniLM-L6-v2')
def score_contexte_embeddings(contenu, resume):
    emb_article = model.encode(contenu, convert_to_tensor=True)
    emb_resume = model.encode(resume, convert_to_tensor=True)
    return util.cos_sim(emb_article, emb_resume).item()

# --- Calcul score global avec alerte contexte ---
def calcul_score_global(article, seuil_contexte=0.3, contexte_minimal=0.2):
    resume = article.get("resume", "")
    contenu = article.get("contenu", "")

    score_factuel = verifier_resume_factuel(article)
    score_fuzzy_c = score_fuzzy(resume, MOTS_CLES, SOCIETES, INTERMEDIAIRES)
    score_emb = score_contexte_embeddings(contenu, resume)

    # Score contexte combiné
    score_contexte = 0.5*score_fuzzy_c + 0.5*score_emb
    # Limite minimale pour ne pas trop pénaliser les résumés courts mais corrects
    score_contexte = max(score_contexte, contexte_minimal)

    # Score global pondéré
    score_global = 0.7*score_factuel + 0.3*score_contexte

    # Alerte si contexte initial < seuil_contexte
    contexte_hors_sujet = (score_contexte < seuil_contexte)

    return score_global, score_factuel, score_contexte, contexte_hors_sujet

# --- Exécution ---
checkpoint = charger_checkpoint()
articles_resume = checkpoint.get("articles_resume", [])

for art in tqdm(articles_resume, desc="Récupération du contenu"):
    art["contenu"] = recuperer_contenu_article(art["lien"])

resultats = []
for art in tqdm(articles_resume, desc="Évaluation globale contextuelle ajustée"):
    score_global, score_factuel, score_contexte, hors_sujet = calcul_score_global(art)
    resultats.append({
        "titre": art.get("titre"),
        "score_global": score_global,
        "score_factuel": score_factuel,
        "score_contexte": score_contexte,
        "hors_sujet": hors_sujet
    })

# --- Affichage ---
if resultats:
    moyenne_global = sum(r["score_global"] for r in resultats)/len(resultats)
    print(f"\n✅ Score global moyen ajusté : {moyenne_global:.2f}\n")
    print("Articles à relire ou hors contexte :")
    for r in resultats:
        flag = "⚠️ Hors contexte" if r["hors_sujet"] else ""
        if r["score_global"] < 0.75 or r["hors_sujet"]:
            print(f"- {r['titre']} | Factuel: {r['score_factuel']:.2f}, Contexte: {r['score_contexte']:.2f}, Global: {r['score_global']:.2f} {flag}")
else:
    print("⚠️ Aucun article dans le checkpoint.")
