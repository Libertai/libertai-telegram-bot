import os
import json
import numpy as np
import aiohttp
import asyncio
from PyPDF2 import PdfReader
from .. import config

# Define a global variable for the default API URL
DEFAULT_API_URL = "https://curated.aleph.cloud/vm/ee1b2a8e5bd645447739d8b234ef495c9a2b4d0b98317d510a3ccf822808ebe5/embedding"

# Async function to embed text using the external embedding tool
async def embed_text(text, session, api_url, tries=3):
    backoff = 1  # Start with 1 second backoff
    params = {
        'content': text,
    }

    response = None
    errors = []
    for _ in range(tries):
        try:
            async with session.post(api_url, json=params) as resp:
                resp.raise_for_status()
                response = await resp.json()
                break
        except aiohttp.ClientError as error:
            errors.append(str(error))
            print(f"Error embedding text: {error}")
            await asyncio.sleep(backoff)
            backoff *= 2

    if response is None:
        raise Exception('Failed to generate embedding: ' + '; '.join(errors))

    return response.get('embedding', [])

class KnowledgeBase:
    def __init__(self, db_path, api_url=DEFAULT_API_URL):
        self.db_path = db_path
        self.api_url = api_url
        self.session = None
        self.load_db()

    async def close(self):
        if self.session is not None:
            await self.session.close()

    def load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {}

    def save_db(self):
        with open(self.db_path, 'w') as f:
            json.dump(self.db, f)

    async def add_entry(self, title, content):
        if self.session == None:
            self.session = aiohttp.ClientSession()

        embedding = await embed_text(content, self.session, self.api_url)
        self.db[title] = {
            'content': content,
            'embedding': embedding
        }
        self.save_db()

    async def query(self, query_text, top_k=3, min=0.1):
        if self.session is None:
            self.session = aiohttp.ClientSession()

        query_embedding = await embed_text(query_text, self.session, self.api_url)
        results = []

        for title, data in self.db.items():
            entry_embedding = np.array(data['embedding'])
            similarity = np.dot(query_embedding, entry_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(entry_embedding))
            results.append((title, data['content'], similarity))

        # Sort results by similarity in descending order and return top_k results
        results.sort(key=lambda x: x[2], reverse=True)
        return [r for r in results[:top_k] if r[2] > min]

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def chunk_text(text, chunk_size=200):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield ' '.join(words[i:i + chunk_size])

async def populate_db_from_pdf(db_path, api_url, pdf_path):
    kb = KnowledgeBase(db_path, api_url)
    try:
        text = extract_text_from_pdf(pdf_path)
        for i, chunk in enumerate(chunk_text(text)):
            title = f"Chunk {i+1}"
            await kb.add_entry(title, chunk)
    finally:
        await kb.close()

async def search_knowledgebase(query_text: str, top_k: int = 3, min: float = 0.2) -> list[tuple[str, str, float]]:
    """
    Search the knowledge base for entries that match the query text.

    Args:
        query_text (str): The text to query the knowledge base with.
        top_k (int, optional): The maximum number of top results to return. Defaults to 3.
        min (float, optional): The minimum similarity threshold for results to be included. Defaults to 0.2.

    Returns:
        list[tuple[str, str, float]]: A list of tuples containing the title, content, and similarity score of the top matching entries.
    """
    kb = config.KNOWLEDGEBASE
    return await kb.query(query_text, top_k, min)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Populate the knowledge database from a PDF.')
    parser.add_argument('db_path', type=str, help='Path to the knowledge database file.')
    parser.add_argument('pdf_path', type=str, help='Path to the PDF file containing the lorebook.')
    parser.add_argument('--api_url', type=str, default=DEFAULT_API_URL, help='API URL for the embedding service (default: %(default)s).')

    args = parser.parse_args()
    asyncio.run(populate_db_from_pdf(args.db_path, args.api_url, args.pdf_path))




