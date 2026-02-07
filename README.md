# AI-Powered-Stock-Market-Press-Review-Document-Assistant

This repository contains an AI-driven system designed to automate financial press monitoring
and enable intelligent interaction with financial documents.

The project was developed following the CRISP-DM methodology and focuses on two main use cases:
1) Automated stock market press review
2) RAG-based PDF chatbot and document processing tools

The solution is tailored for financial analysts, investors, and institutions seeking faster,
more accurate access to market information.

---

## 🚀 Features

### 🔹 Automated Stock Market Press Review
- Multi-source web scraping of financial and economic news
- Keyword-based filtering for companies, intermediaries, and market events
- AI-powered article summarization using Large Language Models
- Fact-checking and relevance scoring of generated summaries
- Export of daily press reviews as Word documents
- Chrome extension for easy interaction
- Real-time execution logs and checkpoint recovery

### 🔹 RAG-Based PDF Chatbot & Document Tools
- Question-answering over multiple uploaded PDF documents
- Semantic search using vector embeddings (FAISS)
- Context-aware answers powered by Retrieval-Augmented Generation (RAG)
- PDF translation into multiple languages (including Arabic support)
- Word (.docx) to PDF conversion
- Conversation history tracking and CSV export
- Interactive Streamlit user interface

---

## 🧠 Architecture Overview

- **Backend**: Python, Flask
- **Frontend**: Streamlit
- **AI & NLP**:
  - Mistral (via Ollama) for local LLM inference
  - Gemini API for document-based reasoning
  - LangChain for orchestration
  - FAISS for vector similarity search
- **Data Processing**:
  - Selenium & Newspaper for web scraping
  - PyPDF2 for document parsing
  - docx2pdf for document conversion

---

## 📊 Evaluation

- Press summaries evaluated using:
  - LLM-based factual verification
  - Fuzzy matching (RapidFuzz)
  - Semantic similarity (SentenceTransformers)
- Average press summary accuracy score: **0.84**
- RAG chatbot evaluation shows high semantic consistency:
  - Cosine similarity ≈ **97%**

---

## 🛠️ Deployment

- Flask server launched via batch script for press review agent
- Chrome extension for triggering and monitoring scraping
- Streamlit application for PDF Q&A, translation, and conversion
- Modular and extensible architecture for future enhancements

---

## 🎯 Use Cases

- Financial press monitoring
- Market intelligence automation
- Regulatory and financial document analysis
- Multilingual financial reporting
- Decision support for analysts and institutions

---

## 📌 Future Improvements

- Persistent storage for chat history
- Support for larger documents and additional formats
- Integration of advanced financial analytics and sentiment detection
- Deployment on cloud infrastructure

---

## 📄 Reference

This project is based on an academic and professional study conducted in the context of
the Tunisian stock market, aiming to modernize financial information processing through AI.
