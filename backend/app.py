from flask import Flask, request, jsonify
from flask_cors import CORS

from generate import answer_question
from embeddings import index_repo

app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

@app.route('/index', methods=['POST'])
def index():
    data = request.get_json()

    if not data or 'repo_url' not in data:
        return jsonify({"error": "Missing 'repo_url' in request body"}), 400

    repo_url = data['repo_url']
    force = data.get('force', False)

    try:
        chunk_count = index_repo(repo_url, force=force)

        if chunk_count == 0:
            # Could mean "already indexed" OR "nothing found" — check which
            from embeddings import is_repo_indexed
            if is_repo_indexed(repo_url):
                return jsonify({
                    "repo_url": repo_url,
                    "status": "already_indexed",
                    "message": "This repo is already indexed. Pass force=true to re-index."
                })
            else:
                return jsonify({
                    "repo_url": repo_url,
                    "status": "no_content",
                    "message": "No indexable files found in this repo."
                })

        return jsonify({
            "repo_url": repo_url,
            "status": "indexed",
            "chunks_created": chunk_count
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()

    if not data or 'question' not in data or 'repo_url' not in data:
        return jsonify({"error": "Missing 'question' in request body"}), 400

    question = data['question']
    repo_url = data['repo_url']
    top_k = data.get('top_k', 15)

    try:
        answer = answer_question(question, repo_url, top_k=top_k)
        return jsonify({
            "question": question,
            "repo_url": repo_url,
            "answer": answer
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
