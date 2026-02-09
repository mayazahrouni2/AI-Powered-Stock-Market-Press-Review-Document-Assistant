import pandas as pd
import numpy as np
import nltk
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge import Rouge

# Télécharger les ressources nécessaires
nltk.download('punkt')

# --- Métriques ---
def exact_match(pred, ref):
    return int(pred.strip().lower() == ref.strip().lower())

def f1_score(pred, ref):
    pred_tokens = set(nltk.word_tokenize(pred.lower()))
    ref_tokens = set(nltk.word_tokenize(ref.lower()))
    common = pred_tokens.intersection(ref_tokens)
    if len(common) == 0:
        return 0
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(ref_tokens)
    return (2 * precision * recall) / (precision + recall)

def cosine_sim(pred, ref):
    vectorizer = TfidfVectorizer().fit_transform([pred, ref])
    return cosine_similarity(vectorizer[0], vectorizer[1])[0][0]

rouge = Rouge()
def rouge_l(pred, ref):
    scores = rouge.get_scores(pred, ref)
    return scores[0]['rouge-l']['f']

def bleu_score(pred, ref):
    smoothie = SmoothingFunction().method4
    return sentence_bleu([nltk.word_tokenize(ref.lower())],
                         nltk.word_tokenize(pred.lower()),
                         smoothing_function=smoothie)

# --- Lecture du CSV ---
df = pd.read_csv("chatbot_responses.csv")  # Nom de ton fichier
df["expected_answer"] = df.groupby("question")["generated_response"].transform("first")

# --- Calcul des scores ---
metrics = {"ExactMatch": [], "F1": [], "ROUGE-L": [], "BLEU": [], "CosineSim": []}

for _, row in df.iterrows():
    pred = str(row["generated_response"])
    ref = str(row["expected_answer"])
    metrics["ExactMatch"].append(exact_match(pred, ref))
    metrics["F1"].append(f1_score(pred, ref))
    metrics["ROUGE-L"].append(rouge_l(pred, ref))
    metrics["BLEU"].append(bleu_score(pred, ref))
    metrics["CosineSim"].append(cosine_sim(pred, ref))

# --- Résultats globaux ---
results = {m: np.mean(scores) for m, scores in metrics.items()}
print("\n📊 Scores moyens sur toutes les questions :")
for metric, score in results.items():
    print(f"{metric}: {score:.4f}")
