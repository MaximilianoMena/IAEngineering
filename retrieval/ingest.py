"""
retrieval/ingest.py

Carga los documentos de data/raw/ (PDFs y .txt), los trocea en chunks,
genera embeddings y los guarda en una base vectorial local (Chroma).

Uso:
    python retrieval/ingest.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PERSIST_DIR = Path(__file__).resolve().parent.parent / "chroma_db"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150


def cargar_documentos(data_dir: Path) -> list:
    """Carga todos los PDFs y .txt encontrados en data_dir."""
    documentos = []
    archivos = list(data_dir.glob("*.pdf")) + list(data_dir.glob("*.txt"))

    if not archivos:
        print(f"⚠️  No se encontraron archivos .pdf o .txt en {data_dir}")
        print("   Agregá tus documentos (informes BYMA/CNV, noticias, etc.) ahí y volvé a correr este script.")
        sys.exit(1)

    for archivo in archivos:
        print(f"📄 Cargando {archivo.name}...")
        if archivo.suffix == ".pdf":
            loader = PyPDFLoader(str(archivo))
        else:
            loader = TextLoader(str(archivo), encoding="utf-8")
        documentos.extend(loader.load())

    return documentos


def trocear_documentos(documentos: list) -> list:
    """Divide los documentos en chunks manejables para el retrieval."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documentos)


def generar_embeddings_y_guardar(chunks: list) -> None:
    """Genera embeddings de los chunks y los persiste en Chroma.

    Usa un modelo local de HuggingFace (sentence-transformers), gratis y
    sin necesidad de API key. La primera vez que corras esto va a descargar
    el modelo (~90MB), después queda cacheado localmente.
    """
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print(f"🧠 Generando embeddings para {len(chunks)} chunks (modelo local, puede tardar la primera vez)...")
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(PERSIST_DIR),
    )
    print(f"✅ Base vectorial guardada en {PERSIST_DIR}")
    return vectorstore


def main():
    print(f"📂 Buscando documentos en {DATA_DIR}...")
    documentos = cargar_documentos(DATA_DIR)
    print(f"✅ {len(documentos)} documento(s) cargado(s)")

    chunks = trocear_documentos(documentos)
    print(f"✂️  {len(chunks)} chunk(s) generado(s)")

    generar_embeddings_y_guardar(chunks)
    print("\n🎉 Ingestión completa. Ya podés levantar la API con:")
    print("   uvicorn api.main:app --reload")


if __name__ == "__main__":
    main()
