"""
Ingestion pipeline: load → chunk → embed → upsert to Pinecone.

Run: uv run python scripts/ingest.py
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from langchain_text_splitters import RecursiveCharacterTextSplitter


class IngestPipeline:
    """Loads markdown docs, chunks, embeds, and upserts to Pinecone."""

    EMBED_BATCH_SIZE = 50
    UPSERT_BATCH_SIZE = 100

    PRIORITY_MAP: dict[str, str] = {
        # High — flagship projects
        "03_cloud_webapp_project.md": "high",
        "01_locall_project.md": "high",
        "02_sidekick_project.md": "high",
        # Medium
        "08_dsa_leetcode.md": "medium",
        "07_adv_bigdata_project.md": "medium",
        "04_hospital_management_project.md": "medium",
        # Low
        "05_amazon_prototype_project.md": "low",
        "06_student_management_project.md": "low",
        "09_population_analysis_project.md": "low",
        # General files — high
        "00_flagship_overview.md": "high",
        "00_secondary_projects.md": "medium",
        "10_work_experience.md": "high",
        "11_technical_skills.md": "high",
        "12_about_education.md": "high",
    }

    def __init__(self) -> None:
        load_dotenv()

        self.raw_dir = Path(__file__).parent.parent / "data" / "raw"
        self.embedding_model = os.getenv("EMBEDDING_MODEL")
        self.index_name = os.getenv("PINECONE_INDEX_NAME")
        self.dimension = int(os.getenv("EMBEDDING_DIMENSIONS"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP"))

        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            add_start_index=True,
        )

    def load(self) -> list[dict]:
        """Load all .md files from data/raw/."""
        docs: list[dict] = []
        for md_file in sorted(self.raw_dir.glob("*.md")):
            text = md_file.read_text(encoding="utf-8")
            docs.append({"text": text, "source": md_file.name})
            print(f"  Loaded: {md_file.name} ({len(text):,} chars)")
        return docs

    def _get_priority(self, filename: str) -> str:
        """Return priority level for a given filename."""
        return self.PRIORITY_MAP.get(filename, "medium")

    def chunk(self, docs: list[dict]) -> list[dict]:
        """Split docs into chunks."""
        chunks: list[dict] = []
        for doc in docs:
            splits = self.splitter.split_text(doc["text"])
            priority = self._get_priority(doc["source"])
            for idx, split_text in enumerate(splits):
                chunks.append({
                    "id": f"{doc['source']}_{idx}",
                    "text": split_text,
                    "source": doc["source"],
                    "priority": priority,
                })
        return chunks

    def embed(self, chunks: list[dict]) -> list[dict]:
        """Embed chunks in batches using OpenAI embeddings API."""
        embedded: list[dict] = []
        total = len(chunks)
        for i in range(0, total, self.EMBED_BATCH_SIZE):
            batch = chunks[i : i + self.EMBED_BATCH_SIZE]
            texts = [c["text"] for c in batch]
            response = self.openai_client.embeddings.create(
                model=self.embedding_model, input=texts
            )
            for chunk_item, emb_obj in zip(batch, response.data):
                embedded.append({**chunk_item, "values": emb_obj.embedding})
            print(f"  Embedded {min(i + self.EMBED_BATCH_SIZE, total)} / {total}")
        return embedded

    def _get_or_create_index(self):
        """Create Pinecone index if it doesn't exist, return Index client."""
        existing = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing:
            print(f"  Creating index '{self.index_name}' (dim={self.dimension}, cosine) ...")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            while not self.pc.describe_index(self.index_name).status["ready"]:
                print("  Waiting for index to be ready ...")
                time.sleep(2)
            print("  Index ready.")
        else:
            print(f"  Index '{self.index_name}' already exists.")

        return self.pc.Index(self.index_name)

    def upsert(self, index, embedded_chunks: list[dict]) -> int:
        """Upsert embedded chunks to Pinecone in batches."""
        total = 0
        for i in range(0, len(embedded_chunks), self.UPSERT_BATCH_SIZE):
            batch = embedded_chunks[i : i + self.UPSERT_BATCH_SIZE]
            vectors = [
                (
                    c["id"],
                    c["values"],
                    {"text": c["text"], "source": c["source"], "priority": c["priority"]},
                )
                for c in batch
            ]
            index.upsert(vectors=vectors)
            total += len(batch)
            print(f"  Upserted {total} / {len(embedded_chunks)}")
        return total

    def run(self) -> None:
        """Execute the full ingestion pipeline."""
        print("\n=== Portfolio Ingestion Pipeline ===\n")

        print("Step 1: Loading markdown files ...")
        docs = self.load()
        print(f"  → {len(docs)} files loaded\n")

        print("Step 2: Chunking documents ...")
        chunks = self.chunk(docs)
        print(f"  → {len(chunks)} chunks created\n")

        print("Step 3: Embedding chunks ...")
        embedded_chunks = self.embed(chunks)
        print(f"  → {len(embedded_chunks)} embeddings done\n")

        print("Step 4: Upserting to Pinecone ...")
        index = self._get_or_create_index()
        self.upsert(index, embedded_chunks)
        print()

        print("Step 5: Verifying ...")
        stats = index.describe_index_stats()
        print(f"  → Index '{self.index_name}' has {stats.total_vector_count} vectors")

        print(f"\n=== Done! {len(chunks)} chunks ingested ===\n")


if __name__ == "__main__":
    pipeline = IngestPipeline()
    pipeline.run()
