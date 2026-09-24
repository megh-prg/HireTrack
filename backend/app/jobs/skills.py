"""Skill vocabulary and extraction.

Each canonical skill maps to the aliases that recruiters actually write. Extraction is
boundary-aware so "sql" does not fire inside "postgresql" and "c++"/"node.js" still work.
"""

import re
from functools import lru_cache

SKILL_ALIASES: dict[str, list[str]] = {
    # Languages
    "python": ["python", "python3"],
    "java": ["java"],
    "javascript": ["javascript", "js", "es6"],
    "typescript": ["typescript"],
    "golang": ["golang"],
    "rust": ["rust"],
    "c++": ["c++", "cpp"],
    "sql": ["sql"],
    # Backend
    "fastapi": ["fastapi", "fast api"],
    "django": ["django", "django rest framework", "drf"],
    "flask": ["flask"],
    "node.js": ["node.js", "nodejs", "node js", "express.js", "expressjs"],
    "spring boot": ["spring boot", "springboot"],
    "rest api": ["rest api", "rest apis", "restful"],
    "graphql": ["graphql"],
    "grpc": ["grpc"],
    "microservices": ["microservices", "microservice", "micro-services"],
    "sqlalchemy": ["sqlalchemy"],
    "celery": ["celery"],
    "async programming": ["asyncio", "async/await", "asynchronous programming"],
    "pytest": ["pytest", "unit testing", "unittest"],
    # Data stores
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "elasticsearch": ["elasticsearch", "opensearch", "elastic search"],
    "kafka": ["kafka"],
    "rabbitmq": ["rabbitmq"],
    "nosql": ["nosql"],
    "vector databases": [
        "vector database",
        "vector databases",
        "vector db",
        "vector store",
        "pinecone",
        "weaviate",
        "faiss",
        "chromadb",
        "chroma",
        "pgvector",
        "qdrant",
        "milvus",
    ],
    # Infra
    "docker": ["docker", "containers", "containerization"],
    "kubernetes": ["kubernetes", "k8s", "eks", "gke", "aks"],
    "aws": ["aws", "amazon web services", "lambda", "s3", "ec2", "sagemaker"],
    "gcp": ["gcp", "google cloud", "vertex ai", "bigquery"],
    "azure": ["azure"],
    "terraform": ["terraform"],
    "ci/cd": ["ci/cd", "cicd", "github actions", "jenkins", "gitlab ci"],
    "linux": ["linux", "unix", "bash"],
    "git": ["git", "github", "gitlab"],
    # AI / ML
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "neural networks"],
    "nlp": ["nlp", "natural language processing"],
    "llm": ["llm", "llms", "large language model", "large language models", "gpt", "claude"],
    "genai": ["genai", "gen ai", "generative ai"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "embeddings": ["embeddings", "embedding models", "semantic search"],
    "prompt engineering": ["prompt engineering", "prompting", "prompt design"],
    "fine-tuning": ["fine-tuning", "fine tuning", "finetuning", "lora", "peft"],
    "ai agents": ["ai agents", "llm agents", "agentic", "tool calling", "function calling"],
    "llm evaluation": ["llm evaluation", "evals", "llm evals", "ragas"],
    "langchain": ["langchain", "langgraph"],
    "llamaindex": ["llamaindex", "llama index", "llama-index"],
    "hugging face": ["hugging face", "huggingface", "transformers"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "keras"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "mlops": ["mlops", "mlflow", "kubeflow"],
    "spark": ["spark", "pyspark", "databricks"],
    "airflow": ["airflow"],
    # Frontend
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs"],
    "html/css": ["html", "css", "tailwind"],
    # Fundamentals
    "system design": ["system design", "distributed systems", "scalability"],
    "data structures & algorithms": ["data structures", "algorithms", "dsa"],
}

# Which prep track closes the gap for a given skill (used for personalised prep).
SKILL_TO_TRACK: dict[str, str] = {
    "python": "python",
    "async programming": "python",
    "pytest": "python",
    "pandas": "python",
    "numpy": "python",
    "sql": "sql",
    "postgresql": "sql",
    "mysql": "sql",
    "sqlalchemy": "sql",
    "fastapi": "backend",
    "django": "backend",
    "flask": "backend",
    "rest api": "backend",
    "microservices": "backend",
    "redis": "backend",
    "celery": "backend",
    "docker": "backend",
    "kafka": "system-design",
    "rabbitmq": "system-design",
    "kubernetes": "system-design",
    "system design": "system-design",
    "elasticsearch": "system-design",
    "llm": "genai",
    "genai": "genai",
    "rag": "genai",
    "embeddings": "genai",
    "vector databases": "genai",
    "prompt engineering": "genai",
    "fine-tuning": "genai",
    "ai agents": "genai",
    "llm evaluation": "genai",
    "langchain": "genai",
    "llamaindex": "genai",
    "hugging face": "genai",
    "nlp": "genai",
    "data structures & algorithms": "dsa",
}


@lru_cache
def _patterns() -> list[tuple[str, re.Pattern[str]]]:
    compiled = []
    for canonical, aliases in SKILL_ALIASES.items():
        # Longest alias first so "rest api" wins over "rest".
        alternatives = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
        compiled.append(
            (canonical, re.compile(rf"(?<![A-Za-z0-9])(?:{alternatives})(?![A-Za-z0-9+#])", re.I))
        )
    return compiled


def extract_skills(text: str) -> list[str]:
    """Return canonical skills mentioned in free text, in vocabulary order."""
    if not text:
        return []
    return [canonical for canonical, pattern in _patterns() if pattern.search(text)]


def canonicalize(skills: list[str]) -> list[str]:
    """Normalise user-entered skills ("Postgres", "LLMs") to canonical names.

    Unknown skills are kept (lower-cased) so custom skills still participate in matching.
    """
    result: list[str] = []
    for raw in skills:
        raw = raw.strip()
        if not raw:
            continue
        found = extract_skills(raw) or [raw.lower()]
        for skill in found:
            if skill not in result:
                result.append(skill)
    return result
