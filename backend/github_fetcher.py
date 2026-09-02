import os
import base64
import requests
from dotenv import load_dotenv

from chunker import SKIP_DIRS, SKIP_FILES, VALID_EXTENSIONS, chunk_text
from chunker import SKIP_DIRS, SKIP_FILES, VALID_EXTENSIONS, VALID_NO_EXT_FILES, chunk_text

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

def parse_repo_url(repo_url):
    repo_url = repo_url.rstrip('/')
    if repo_url.endswith('.git'):
        repo_url = repo_url[:-4]
    parts = repo_url.replace('https://github.com/', '').split('/')
    return parts[0], parts[1]

def get_default_branch(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()['default_branch']


def get_file_tree(owner, repo, branch):
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()['tree']


def is_valid_path(path):
    parts = path.split('/')
    for part in parts[:-1]:
        if part in SKIP_DIRS or part.startswith('.'):
            return False
    filename = parts[-1]
    if filename in SKIP_FILES:
        return False
    if filename in VALID_NO_EXT_FILES:
        return True
    ext = os.path.splitext(filename)[1]
    return ext in VALID_EXTENSIONS

def fetch_file_content(owner, repo, path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    data = res.json()
    if data.get('encoding') == 'base64':
        try:
            return base64.b64decode(data['content']).decode('utf-8', errors='ignore')
        except Exception:
            return None
    return None


def fetch_and_chunk_repo(repo_url):
    owner, repo = parse_repo_url(repo_url)
    branch = get_default_branch(owner, repo)
    tree = get_file_tree(owner, repo, branch)

    all_chunks = []
    file_count = 0

    for item in tree:
        if item['type'] != 'blob':
            continue
        path = item['path']
        if not is_valid_path(path):
            continue
        if item.get('size', 0) > 500_000:
            continue

        content = fetch_file_content(owner, repo, path)
        if content is None:
            continue

        chunks = chunk_text(path, content)
        all_chunks.extend(chunks)
        file_count += 1

    print(f"Fetched and processed {file_count} files, generated {len(all_chunks)} chunks from {repo_url}")
    return all_chunks


if __name__ == '__main__':
    test_repo = "https://github.com/nicobytes/interview-full-stack"
    chunks = fetch_and_chunk_repo(test_repo)
    for c in chunks[:3]:
        print('---')
        print(f"File: {c['file_path']}  Lines: {c['start_line']}-{c['end_line']}")
        print(c['content'][:150])
