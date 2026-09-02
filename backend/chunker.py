import os
from pathlib import Path

# Actual directory names to skip entirely.
# NOTE: this was previously a bug — SKIP_DIRS contained lock-file names
# instead of directory names, so node_modules/.git/venv etc. were never
# actually being skipped during os.walk.
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv', '.venv',
    'dist', 'build', '.next', 'target', 'vendor', '.idea', '.vscode'
}

# Lock files: not useful for Q&A, skip by filename
SKIP_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
    'poetry.lock', 'Cargo.lock'
}

# Filenames with no extension (or non-standard extension) worth indexing
VALID_NO_EXT_FILES = {
    'README', 'LICENSE', 'Dockerfile', 'Makefile', 'CHANGELOG', 'CONTRIBUTING',
    'docker-compose.yml', 'docker-compose.yaml',
    '.env.example', '.env.sample'
}

# File extensions we care about — source code + docs + config
VALID_EXTENSIONS = {
    '.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.go',
    '.rb', '.php', '.html', '.css', '.scss', '.json', '.md',
    '.yml', '.yaml', '.toml'
}

CHUNK_SIZE = 300   # lines per chunk — bigger chunks = fewer embeddings, faster scans on large repos
OVERLAP = 30        # scaled up proportionally with chunk size


def should_skip_dir(dirname):
    return dirname in SKIP_DIRS or dirname.startswith('.')

def is_valid_file(filepath):
    if filepath.name in SKIP_FILES:
        return False
    if filepath.suffix in VALID_EXTENSIONS:
        return True
    if filepath.name in VALID_NO_EXT_FILES:
        return True
    return False

def chunk_file(filepath):
    """Split a single file into overlapping line-based chunks."""
    chunks = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Skipping {filepath}: {e}")
        return chunks

    total_lines = len(lines)
    if total_lines == 0:
        return chunks

    start = 0
    while start < total_lines:
        end = min(start + CHUNK_SIZE, total_lines)
        chunk_text = ''.join(lines[start:end])

        if chunk_text.strip():  # skip empty chunks
            chunks.append({
                'file_path': str(filepath),
                'start_line': start + 1,
                'end_line': end,
                'content': chunk_text
            })

        if end == total_lines:
            break
        start = end - OVERLAP  # move forward with overlap

    return chunks

def chunk_text(file_path, content):
    """Same chunking logic as chunk_file, but works on in-memory content (e.g. from GitHub API)."""
    chunks = []
    lines = content.splitlines(keepends=True)
    total_lines = len(lines)

    if total_lines == 0:
        return chunks

    start = 0
    while start < total_lines:
        end = min(start + CHUNK_SIZE, total_lines)
        chunk_text_content = ''.join(lines[start:end])

        if chunk_text_content.strip():
            chunks.append({
                'file_path': file_path,
                'start_line': start + 1,
                'end_line': end,
                'content': chunk_text_content
            })

        if end == total_lines:
            break
        start = end - OVERLAP

    return chunks

def walk_and_chunk(root_dir):
    """Walk the entire repo and return all chunks from all valid files."""
    root_path = Path(root_dir)
    all_chunks = []
    file_count = 0

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Modify dirnames in-place to prevent os.walk from descending into skip dirs
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]

        for filename in filenames:
            filepath = Path(dirpath) / filename
            if is_valid_file(filepath):
                file_chunks = chunk_file(filepath)
                all_chunks.extend(file_chunks)
                file_count += 1

    print(f"Processed {file_count} files, generated {len(all_chunks)} chunks.")
    return all_chunks


if __name__ == '__main__':
    # Point this at your test repo's api folder
    target_dir = os.path.expanduser(
        '~/CodeCompass/test-repos/interview-full-stack/apps/api'
    )
    chunks = walk_and_chunk(target_dir)

    # Print first 2 chunks as a sanity check
    for c in chunks[:2]:
        print('---')
        print(f"File: {c['file_path']}  Lines: {c['start_line']}-{c['end_line']}")
        print(c['content'][:200])
