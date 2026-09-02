import os
import time
from dotenv import load_dotenv
from google import genai
from embeddings import search_similar, get_readme_chunks

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPT_TEMPLATE = """You are CodeCompass, an expert assistant that answers questions about a GitHub repository using only the code and documentation snippets provided below.

HOW TO ANSWER:
- Base your answer strictly on the provided snippets. Never invent file names, functions, or behavior that isn't shown.
- If the snippets fully answer the question, answer directly and confidently — don't hedge unnecessarily.
- If the snippets partially answer the question, give what you can and clearly state what's missing.
- If the snippets don't contain relevant information, say: "I don't have enough information in the indexed content to answer that." Do not guess.
- If the question asks about something structural (e.g. exact file/folder counts) that these snippets can't fully verify, say so rather than estimating from a partial view.
- If multiple snippets are relevant, synthesize them into one coherent answer rather than listing them separately.
- For "what does this do" or "explain X" questions, prioritize README/documentation snippets for intent and purpose, and code snippets for implementation detail.
- For debugging or "why" questions, trace logic across the provided snippets step by step if possible.
- Always cite the specific file and line numbers you used, like this: (see filename.ts, lines X-Y). Cite every distinct file you draw from.
- Keep answers concise and technical — skip filler like "Based on the provided code" or restating the question.

CODE AND DOCUMENTATION SNIPPETS:
{context}

QUESTION: {question}

ANSWER:"""


def format_context(chunks):
    """chunks: list of (file_path, start_line, end_line, content, distance) from
    search_similar, OR (file_path, start_line, end_line, content) from get_readme_chunks.
    Dedupes by (file_path, start_line, end_line) in case a README chunk also
    happened to rank in the top-k similarity results."""
    parts = []
    seen = set()
    for c in chunks:
        file_path, start_line, end_line, content = c[0], c[1], c[2], c[3]
        key = (file_path, start_line, end_line)
        if key in seen:
            continue
        seen.add(key)
        parts.append(
            f"--- {file_path} (lines {start_line}-{end_line}) ---\n{content}"
        )
    return "\n\n".join(parts)


def answer_question(question, repo_url, top_k=10):
    t0 = time.time()
    chunks = search_similar(question, repo_url, top_k=top_k)

    # Always pull README chunks separately and merge them in, regardless of
    # similarity ranking — fixes "what does this project do" style questions
    # that pure code-similarity search tends to miss.
    readme_chunks = get_readme_chunks(repo_url)

    t1 = time.time()
    print(f"Retrieval took {t1 - t0:.2f}s")

    all_chunks = list(chunks) + list(readme_chunks)

    if not all_chunks:
        return "No relevant code found in the indexed repository."

    context = format_context(all_chunks)
    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    try:
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        t2 = time.time()
        print(f"LLM generation took {t2 - t1:.2f}s")
        return response.text
    except Exception as e:
        return f"[Error generating answer: {e}]"


if __name__ == '__main__':
    test_repo_url = "https://github.com/pallets/flask"
    test_questions = [
        "where is the database connection configured?",
        "how are database migrations run?",
        "what does the middleware folder do?",
        "what routes does the API expose?",
        "how is payment processing handled?",
    ]
    for q in test_questions:
        print(f"\nQ: {q}")
        print("-" * 50)
        answer = answer_question(q, test_repo_url, top_k=15)
        print(answer)
        print("=" * 50)
