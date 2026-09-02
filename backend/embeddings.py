import os
import psycopg2
from github_fetcher import fetch_and_chunk_repo

from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector

from chunker import walk_and_chunk

# --- DB connection settings ---
DB_NAME = "codecompass"
DB_USER = "codecompass_user"
DB_PASSWORD = "laksh2003"   # replace with the password you actually set
DB_HOST = "localhost"
DB_PORT = "5432"

# --- Load the embedding model once ---
print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")


def get_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    register_vector(conn)
    return conn
def is_repo_indexed(repo_url):
    """Check if a repo already has chunks stored."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM chunks WHERE repo_url = %s", (repo_url,))
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count > 0

def embed_chunks(chunks):
    """Generate embeddings for a list of chunk dicts. Returns chunks with 'embedding' added."""
    texts = [c['content'] for c in chunks]
    print(f"Generating embeddings for {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)

    for chunk, embedding in zip(chunks, embeddings):
        chunk['embedding'] = embedding.tolist()

    return chunks


def store_chunks(chunks, repo_url):
    """Insert chunks (with embeddings) into Postgres, tagged with their repo."""
    conn = get_connection()
    cur = conn.cursor()

    insert_query = """
        INSERT INTO chunks (file_path, start_line, end_line, content, embedding, repo_url)
        VALUES %s
    """
    values = [
        (c['file_path'], c['start_line'], c['end_line'], c['content'], c['embedding'], repo_url)
        for c in chunks
    ]

    execute_values(cur, insert_query, values)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Stored {len(chunks)} chunks for {repo_url}.")

def index_repo(repo_url, local_path=None, force=False):
    """
    Index a repo either from a local folder (fast, for local dev/testing)
    or via the GitHub API (for on-demand extension use, works on any repo).
    Skips if already indexed, unless force=True.
    """
    if not force and is_repo_indexed(repo_url):
        print(f"Repo already indexed: {repo_url} — skipping.")
        return 0

    if local_path:
        print(f"Indexing locally from: {local_path}")
        chunks = walk_and_chunk(local_path)
    else:
        print(f"Indexing via GitHub API: {repo_url}")
        chunks = fetch_and_chunk_repo(repo_url)

    if not chunks:
        print("No chunks generated — nothing to index.")
        return 0

    chunks = embed_chunks(chunks)
    store_chunks(chunks, repo_url)
    return len(chunks)

def search_similar(query_text, repo_url, top_k=15):
    """Given a question, find the most similar chunks within a specific repo."""
    query_embedding = model.encode([query_text])[0].tolist()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT file_path, start_line, end_line, content,
               embedding <-> %s::vector AS distance
        FROM chunks
        WHERE repo_url = %s
        ORDER BY distance ASC
        LIMIT %s
    """, (query_embedding, repo_url, top_k))

    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

def get_readme_chunks(repo_url):
    """Fetch README chunks for a repo directly, bypassing similarity search —
    used to guarantee project-summary context is always available."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT file_path, start_line, end_line, content
        FROM chunks
        WHERE repo_url = %s AND file_path ILIKE %s
    """, (repo_url, '%README%'))
    results = cur.fetchall()
    cur.close()
    conn.close()
    return results

if __name__ == '__main__':
    # Test with a small, different public repo via GitHub API (no local clone needed)
    test_repo_url = "https://github.com/pallets/flask"

    index_repo(test_repo_url)

    results = search_similar('how are routes defined?', test_repo_url)
    for r in results:
        file_path, start_line, end_line, content, distance = r
        print(f"[distance={distance:.4f}] {file_path} (lines {start_line}-{end_line})")
        print(content[:150])
        print('---')
