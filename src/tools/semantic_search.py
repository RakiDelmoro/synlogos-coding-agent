"""Semantic search using TF-IDF for code similarity"""
import re
import math
from collections import Counter
from pathlib import Path
from typing import List, Tuple
from returns.result import Result, Success, Failure


class CodeIndexer:
    """Simple TF-IDF based code indexer for semantic search"""
    
    def __init__(self):
        self.documents: dict[str, str] = {}  # path -> content
        self.term_freq: dict[str, Counter] = {}  # path -> term frequencies
        self.idf: dict[str, float] = {}  # term -> idf score
        self.N = 0  # number of documents
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize code into meaningful terms"""
        # Extract identifiers, function names, class names
        # Pattern: words, snake_case, camelCase
        tokens = []
        
        # Split by non-alphanumeric
        words = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', text)
        
        for word in words:
            # Split camelCase
            if len(word) > 3:  # Only meaningful words
                # Add the full word
                tokens.append(word.lower())
                # Split camelCase and snake_case
                parts = re.split(r'(?=[A-Z])|_', word)
                tokens.extend([p.lower() for p in parts if len(p) > 2])
        
        return tokens
    
    def add_document(self, path: str, content: str):
        """Add a document to the index"""
        self.documents[path] = content
        tokens = self.tokenize(content)
        self.term_freq[path] = Counter(tokens)
        self.N += 1
    
    def build_index(self):
        """Build IDF scores for all terms"""
        # Count document frequency for each term
        df: dict[str, int] = {}
        for tf in self.term_freq.values():
            for term in tf:
                df[term] = df.get(term, 0) + 1
        
        # Calculate IDF: log(N / df)
        for term, count in df.items():
            self.idf[term] = math.log(self.N / count) if count > 0 else 0
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search for documents similar to query"""
        query_tokens = self.tokenize(query)
        query_tf = Counter(query_tokens)
        
        scores: List[Tuple[str, float]] = []
        
        for path, tf in self.term_freq.items():
            # Calculate cosine similarity using TF-IDF
            dot_product = 0.0
            query_norm = 0.0
            doc_norm = 0.0
            
            # Calculate for query terms
            for term, qtf in query_tf.items():
                idf = self.idf.get(term, 0)
                query_tfidf = qtf * idf
                query_norm += query_tfidf ** 2
                
                if term in tf:
                    doc_tfidf = tf[term] * idf
                    dot_product += query_tfidf * doc_tfidf
            
            # Calculate doc norm
            for term, dtf in tf.items():
                idf = self.idf.get(term, 0)
                doc_tfidf = dtf * idf
                doc_norm += doc_tfidf ** 2
            
            # Cosine similarity
            if query_norm > 0 and doc_norm > 0:
                similarity = dot_product / (math.sqrt(query_norm) * math.sqrt(doc_norm))
                scores.append((path, similarity))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# Global indexer instance
_indexer: CodeIndexer | None = None


def get_indexer() -> CodeIndexer:
    """Get or create global code indexer"""
    global _indexer
    if _indexer is None:
        _indexer = CodeIndexer()
    return _indexer


def reset_indexer():
    """Reset the global indexer"""
    global _indexer
    _indexer = None


async def index_codebase(path: str = ".") -> Result[int, str]:
    """Index all code files in the codebase"""
    try:
        from src.tools.advanced_tools import create_glob_tool
        
        indexer = get_indexer()
        
        # Index Python files
        glob_tool = create_glob_tool()
        py_files = await glob_tool.execute(pattern="**/*.py", path=path)
        
        if not py_files.error:
            for file_path in py_files.output.strip().split('\n'):
                if file_path:
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            indexer.add_document(file_path, content)
                    except Exception:
                        pass  # Skip files we can't read
        
        indexer.build_index()
        return Success(len(indexer.documents))
        
    except Exception as e:
        return Failure(f"Failed to index codebase: {e}")


async def semantic_search(query: str, path: str = ".", top_k: int = 5) -> Result[str, str]:
    """Perform semantic search using indexed code"""
    try:
        indexer = get_indexer()
        
        # If not indexed, index first
        if indexer.N == 0:
            result = await index_codebase(path)
            if isinstance(result, Failure):
                return result
        
        results = indexer.search(query, top_k)
        
        if not results:
            return Success("No relevant files found.")
        
        output = f"Semantic search results for: '{query}'\n\n"
        for i, (file_path, score) in enumerate(results, 1):
            output += f"{i}. {file_path} (score: {score:.3f})\n"
            # Show first 3 lines of content
            content = indexer.documents.get(file_path, "")[:200]
            lines = content.split('\n')[:3]
            for line in lines:
                if line.strip():
                    output += f"   {line[:80]}\n"
            output += "\n"
        
        return Success(output)
        
    except Exception as e:
        return Failure(f"Search failed: {e}")
