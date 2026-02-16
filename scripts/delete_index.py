"""
Delete the Pinecone index.

Run: uv run python scripts/delete_index.py
"""

import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = os.getenv("PINECONE_INDEX_NAME")

existing = [idx.name for idx in pc.list_indexes()]
if index_name in existing:
    pc.delete_index(index_name)
    print(f"Deleted index '{index_name}'")
else:
    print(f"Index '{index_name}' not found — nothing to delete")
