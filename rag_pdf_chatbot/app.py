import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd
import asyncio
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import tempfile
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import textwrap
import pythoncom
from docx2pdf import convert
from textwrap import wrap
from reportlab.lib.colors import blue, black, darkblue, darkgreen, orange


# --- Init asyncio ---
try:
    asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# --- Session State ---
if 'chats' not in st.session_state:
    st.session_state.chats = {}
if 'current_chat' not in st.session_state:
    st.session_state.current_chat = None
if 'pending_new_chat' not in st.session_state:
    st.session_state.pending_new_chat = False

# --- Fonctions PDF & Texte ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text.strip()  # strip pour enlever les espaces vides


def get_text_chunks(text, model_name):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

def get_vector_store(text_chunks, model_name, api_key=None):
    if not text_chunks or len(text_chunks) == 0:
        raise ValueError("⚠️ Aucun texte trouvé dans le(s) PDF. Vérifie que le document contient bien du texte (et pas une image scannée).")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key
    )
    
    # Test embedding rapide
    test_emb = embeddings.embed_query("test")
    if not test_emb:
        raise ValueError("⚠️ Impossible de générer les embeddings. Vérifie la clé API ou le modèle.")
    
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    return vector_store


def get_conversational_chain(model_name, vectorstore=None, api_key=None):
    prompt_template = """
    Réponds de manière aussi détaillée que possible à partir du contexte fourni. 
    Si la réponse n'est pas dans le contexte, réponds : "Réponse indisponible dans le document."

    Contexte :
    {context}

    Question :
    {question}

    Réponse :
    """
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3, google_api_key=api_key)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def translate_with_google_ai(text, target_lang, api_key):
    prompt = f"""Traduire le texte suivant en {target_lang} :

Texte :
{text}

Traduction :
"""
    model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0, google_api_key=api_key)
    response = model.predict(prompt)
    return response

# --- Gestion des discussions ---
def user_input(user_question, model_name, api_key, pdf_docs):
    if api_key is None or pdf_docs is None:
        st.warning("Please upload PDF files and provide API key before processing.")
        return

    if st.session_state.current_chat is None:
        chat_name = f"Discussion {len(st.session_state.chats) + 1}"
        st.session_state.chats[chat_name] = {"history": [], "pdfs": pdf_docs}
        st.session_state.current_chat = chat_name
    else:
        chat_name = st.session_state.current_chat
        st.session_state.chats[chat_name]["pdfs"] = pdf_docs

    text_chunks = get_text_chunks(get_pdf_text(pdf_docs), model_name)
    vector_store = get_vector_store(text_chunks, model_name, api_key)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain("Google AI", vectorstore=new_db, api_key=api_key)
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    response_output = response['output_text']

    pdf_names = [pdf.name for pdf in pdf_docs] if pdf_docs else []

    st.session_state.chats[chat_name]["history"].append({
        "question": user_question,
        "answer": response_output,
        "model_name": model_name,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "pdf_files": ", ".join(pdf_names)
    })

# --- Conversion Word -> PDF ---
def conversion_word_pdf():
    pythoncom.CoInitialize()
    st.title("Convertisseur Word (.docx) → PDF")
    uploaded_file = st.file_uploader("Uploader un fichier Word (.docx)", type=["docx"])
    if uploaded_file:
        original_filename = uploaded_file.name
        base_name = original_filename.rsplit(".", 1)[0]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name
        tmp_pdf_path = tmp_path.replace(".docx", ".pdf")
        try:
            convert(tmp_path, tmp_pdf_path)
            with open(tmp_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.success("Conversion réussie !")
            st.download_button(
                "Télécharger le PDF converti",
                pdf_bytes,
                file_name=f"{base_name}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Erreur lors de la conversion : {e}")
        finally:
            try:
                os.remove(tmp_path)
                os.remove(tmp_pdf_path)
            except Exception:
                pass

# --- Page Accueil ---
def accueil():
    st.title("📈 Bienvenue à la Bourse de Tunis")
    st.markdown("""<div style="background-color:#004080; padding:20px; border-radius:10px; color:white; font-family:sans-serif;">
        <h2>La Bourse de Tunis</h2>
        <p>La principale place boursière en Tunisie, jouant un rôle clé dans le financement des entreprises tunisiennes et dans l’économie du pays.</p>
        <ul>
            <li><strong>Créée en 1969</strong></li>
            <li><strong>Plus de 70 sociétés cotées</strong></li>
            <li><strong>Secteurs clés :</strong> banques, assurances, industries, services...</li>
        </ul>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("📰 Actualités du marché")
    news = [
        ("2025-08-10", "L’indice TunIndex poursuit sa croissance malgré un contexte mondial incertain."),
        ("2025-08-08", "Le secteur bancaire enregistre des résultats mitigés au second trimestre."),
        ("2025-08-05", "Plusieurs entreprises industrielles annoncent des plans d'investissement pour 2026."),
        ("2025-08-01", "Les investisseurs surveillent attentivement les décisions de la Banque Centrale.")
    ]
    for date, texte in news:
        st.markdown(f"**{date}** – {texte}")
    st.markdown("---")
    st.info("Cette application vous offre des outils de traduction et de question-réponse basés sur l’IA pour exploiter vos documents PDF et Word.")
    st.markdown("---")
    st.write("© 2025 Bourse de Tunis - Tous droits réservés")

# --- Fonction principale ---
def main():
    st.set_page_config(page_title="Application Bourse Tunis", page_icon="📈", layout="wide")

    st.sidebar.markdown("## Navigation")
    page = st.sidebar.radio("Aller à :", ["Accueil", "Chat & Traduction PDF", "Conversion Word -> PDF"])

    if page == "Accueil":
        accueil()
        return
    elif page == "Conversion Word -> PDF":
        conversion_word_pdf()
        return

    # --- Chat & Traduction PDF ---
    st.title("📚 Chat et Traduction PDF")
    model_name = st.sidebar.radio("Choisir le modèle :", ("Google AI",))
    api_key = st.sidebar.text_input("Entrez votre clé API Google ici :")
    st.sidebar.markdown("[Obtenir votre clé API Google](https://aistudio.google.com/app/apikey)")
    if not api_key:
        st.sidebar.warning("Veuillez entrer votre clé API Google pour continuer.")
        return

    pdf_docs = st.sidebar.file_uploader("Uploader les fichiers PDF", accept_multiple_files=True)
    if pdf_docs is None or len(pdf_docs) == 0:
        st.warning("Veuillez uploader au moins un fichier PDF.")
        return

    mode = st.sidebar.selectbox("Mode :", ["Question-Réponse", "Traduction du PDF"])
   # Si on est en mode Traduction, on cache la discussion
    if mode == "Traduction du PDF":
     st.session_state.current_chat = None

# --- Sidebar des discussions uniquement pour Question-Réponse ---
    # --- Sidebar des discussions uniquement pour Question-Réponse ---
    if mode == "Question-Réponse":
        st.sidebar.markdown("## Discussions")

        # Bouton Nouvelle discussion
        if st.sidebar.button("➕ Nouvelle discussion"):
            new_chat_name = f"Discussion {len(st.session_state.chats) + 1}"
            st.session_state.chats[new_chat_name] = {"history": [], "pdfs": pdf_docs}
            st.session_state.current_chat = new_chat_name
            st.rerun()  # <- rerun pour afficher la nouvelle discussion

        # Liste des discussions
        for chat_name in list(st.session_state.chats.keys()):
            col1, col2 = st.sidebar.columns([6, 1])
            if col1.button(chat_name, key=f"select_{chat_name}"):
                st.session_state.current_chat = chat_name
                st.rerun()
            if col2.button("❌", key=f"delete_{chat_name}"):
                st.session_state.chats.pop(chat_name)
                if st.session_state.current_chat == chat_name:
                    st.session_state.current_chat = None
                st.rerun()



    # --- Mode traduction ---
    full_text = get_pdf_text(pdf_docs)
    if mode == "Traduction du PDF":
        target_lang = st.sidebar.selectbox("Langue de traduction :", ["fr", "en", "ar", "es", "de", "it", "ru"])
        if st.button("Traduire le contenu du PDF"):
            with st.spinner("Traduction en cours..."):
                max_len = 20000
                text_to_translate = full_text[:max_len] + ("..." if len(full_text) > max_len else "")
                translated_text = translate_with_google_ai(text_to_translate, target_lang, api_key)

                st.subheader(f"Contenu traduit en {target_lang} :")
                with st.expander("Voir la traduction complète"):
                    st.write(translated_text)

                # --- Création PDF ---
                from reportlab.pdfbase.ttfonts import TTFont
                from reportlab.pdfbase import pdfmetrics
                import arabic_reshaper
                from bidi.algorithm import get_display
                from reportlab.pdfbase.pdfmetrics import stringWidth
                from reportlab.lib.colors import blue, black
                from reportlab.pdfgen import canvas
                import io
                from reportlab.lib.pagesizes import letter

                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, pagesize=letter)
                width, height = letter

                # --- Police et marges ---
                font_size = 10
                line_height = font_size * 1.6
                marge_gauche = 40
                marge_droite = 40
                max_width = width - marge_gauche - marge_droite
                paragraph_spacing = line_height / 2  # <- ESPACEMENT ENTRE PARAGRAPHES

                if target_lang == "ar":
                    pdfmetrics.registerFont(
                        TTFont("NotoArabic", r"C:\Users\hp\Desktop\stage d'ete bourse\rag_pdf_chatbot\fonts\Noto_Sans_Arabic\static\NotoSansArabic-Regular.ttf")
                    )
                    font_name = "NotoArabic"
                else:
                    font_name = "Helvetica"

                # --- Titre ---
                c.setFont("Helvetica-Bold", 14)
                c.drawCentredString(width / 2, height - 40, f"Traduction en {target_lang}")
                y = height - 70
                paragraphs = translated_text.split("\n\n")

                # --- Fonction pour dessiner du texte avec wrapping ---
                # --- Fonction pour dessiner texte avec wrapping et couleurs ---
                def draw_wrapped_line(c, text, y):
                            if target_lang == "ar":
                                reshaped = arabic_reshaper.reshape(text)
                                bidi_text = get_display(reshaped)
                                c.setFont(font_name, font_size)
                                c.setFillColor(black)
                                c.drawRightString(width - marge_droite, y, bidi_text)
                                y -= line_height
                            else:
                                words = text.split(" ")
                                line_accum = ""
                                for word in words:
                                    test_line = line_accum + (" " if line_accum else "") + word
                                    if stringWidth(test_line, font_name, font_size) > max_width:
                                        # Lien URL
                                        if word.startswith("http://") or word.startswith("https://"):
                                            c.setFont(font_name, font_size)
                                            c.setFillColor(blue)
                                            c.drawString(marge_gauche, y, word)
                                            c.linkURL(word, (marge_gauche, y - 2,
                                                            marge_gauche + stringWidth(word, font_name, font_size),
                                                            y + font_size))
                                            y -= line_height
                                            line_accum = ""
                                        else:
                                            # Vérifier si le mot est entre guillemets pour le mettre en gras
                                            if word.startswith('"') and word.endswith('"'):
                                                c.setFont("Helvetica-Bold", font_size)  # gras
                                                c.setFillColor(black)
                                                c.drawString(marge_gauche, y, line_accum + (" " if line_accum else "") + word)
                                            else:
                                                c.setFont(font_name, font_size)
                                                c.setFillColor(black)
                                                c.drawString(marge_gauche, y, line_accum)
                                            y -= line_height
                                            line_accum = word
                                            if y < 40:
                                                c.showPage()
                                                y = height - 40
                                                c.setFont(font_name, font_size)
                                                c.setFillColor(black)
                                    else:
                                        line_accum = test_line
                                if line_accum:
                                    # Dernier mot de la ligne
                                    if line_accum.startswith('"') and line_accum.endswith('"'):
                                        c.setFont("Helvetica-Bold", font_size)
                                    else:
                                        c.setFont(font_name, font_size)
                                    c.setFillColor(black)
                                    c.drawString(marge_gauche, y, line_accum)
                                    y -= line_height
                            return y


                # --- Découpage du texte par paragraphes ---
                paragraphs = translated_text.split("\n\n")
                for para in paragraphs:
                    wrapped_lines = wrap(para, width=120)
                    for line in wrapped_lines:
                        y = draw_wrapped_line(c, line, y)
                        if y < 40:
                            c.showPage()
                            y = height - 40
                            c.setFont(font_name, font_size)
                            c.setFillColor(black)
                    y -= paragraph_spacing  # <- ESPACEMENT ENTRE PARAGRAPHES pour toutes les langues

                # --- Finalisation PDF ---
                c.save()
                buffer.seek(0)

                base_name = pdf_docs[0].name.rsplit(".", 1)[0] if pdf_docs else "document"
                st.download_button(
                    label="📥 Télécharger la traduction en PDF",
                    data=buffer,
                    file_name=f"{base_name}_traduit_{target_lang}.pdf",
                    mime="application/pdf"
                )
    # --- Mode question-réponse ---
    elif mode == "Question-Réponse":
        user_question = st.text_input("Pose ta question sur le contenu du PDF :")
        if user_question:
            user_input(user_question, model_name, api_key, pdf_docs)

    # --- Affichage discussion courante ---
    if st.session_state.current_chat:
        chat_entry = st.session_state.chats[st.session_state.current_chat]
        chat_history = chat_entry.get("history", [])

        st.subheader(f"💬 Discussion : {st.session_state.current_chat}")
        for msg in chat_history:
            st.markdown(f"""
            <div style="display:flex; margin-bottom:10px;">
                <div style="flex-shrink:0; margin-right:10px;">
                    <span style="font-size:24px;">👤</span>
                </div>
                <div style="background-color:#706f6f; padding:10px; border-radius:10px; max-width:80%;">
                    <b>Vous :</b><br>{msg['question']}<br>
                    <i>PDF(s) utilisé(s) : {msg.get('pdf_files','')}</i>
                </div>
            </div>
            <div style="display:flex; margin-bottom:10px;">
                <div style="flex-shrink:0; margin-right:10px;">
                    <span style="font-size:24px;">🤖</span>
                </div>
                <div style="background-color:#383737; padding:10px; border-radius:10px; max-width:80%;">
                    <b>Bot :</b><br>{msg['answer']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export CSV des réponses
        if chat_history:
            st.markdown("---")
            st.subheader("📤 Export des réponses du chatbot")
            df_export = pd.DataFrame(chat_history)
            csv_bytes = df_export.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Télécharger les réponses en CSV",
                data=csv_bytes,
                file_name="chatbot_responses.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
