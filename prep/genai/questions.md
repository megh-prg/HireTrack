# GenAI / LLM engineering

## Explain RAG end to end.
Tags: rag

1. **Ingest**: load documents, clean, split into chunks (by tokens/headings with overlap).
2. **Embed** each chunk and store vectors with metadata in a vector DB (pgvector, Qdrant, Pinecone).
3. **Retrieve**: embed the query, fetch top-k by similarity, optionally hybrid search (BM25 + vectors) and re-rank.
4. **Generate**: put retrieved chunks in the prompt with instructions to answer only from them and cite sources.
5. **Evaluate**: retrieval recall and answer faithfulness on a labelled set.

## How do you choose chunk size?
Tags: rag, chunking

Trade-off: small chunks retrieve precisely but lose context; large chunks keep context but dilute similarity and waste tokens. Start around 300–800 tokens with 10–20% overlap, split on structure (headings, paragraphs), and tune against a retrieval eval rather than guessing.

## What are embeddings?
Tags: embeddings

Dense vectors where semantic similarity ≈ geometric closeness (cosine similarity). Used for semantic search, clustering, deduplication and classification. Query and documents must use the same embedding model; changing models means re-embedding.

## How do you reduce hallucinations?
Tags: reliability

Ground answers in retrieved context, instruct the model to say "I don't know", require citations and verify them, lower temperature for factual tasks, use structured outputs, add a verification/critique step, and measure faithfulness with evals.

## How do you evaluate an LLM application?
Tags: evaluation

Build a golden dataset of realistic inputs with expected outputs or rubrics. Measure retrieval (recall@k, MRR) separately from generation (faithfulness, relevance, correctness). Use deterministic checks where possible, LLM-as-judge with a clear rubric where not, and track results per prompt/model version in CI.

## What is prompt engineering beyond "write a good prompt"?
Tags: prompting

Clear role and task, explicit constraints and output format (JSON schema), few-shot examples, separating instructions from untrusted data with delimiters, chain-of-thought or step decomposition for complex tasks, and versioning prompts with evals so changes are measured.

## Fine-tuning vs RAG vs prompting — how do you choose?
Tags: fine-tuning, rag

Prompting first (cheapest). RAG when the model needs fresh or private knowledge. Fine-tuning (LoRA/PEFT) when you need a consistent style/format, a narrow skill, or lower latency/cost with a smaller model — not for injecting facts that change.

## What is an AI agent? What goes wrong with them?
Tags: agents

An LLM in a loop that chooses tools (function calling), observes results, and continues until done. Failure modes: infinite loops, wrong tool arguments, compounding errors, prompt injection via tool outputs, and cost blow-ups. Mitigate with step limits, validated tool schemas, human approval for risky actions, and tracing.

## What is prompt injection and how do you defend against it?
Tags: security

Untrusted text (a web page, email, document) containing instructions that hijack the model. Defences: treat retrieved content as data, least-privilege tools, confirmation for side-effecting actions, output filtering, and never letting the model directly execute privileged operations.

## How do you control LLM latency and cost in production?
Tags: production

Stream tokens, cache responses and prompt prefixes, use the smallest model that passes evals, trim context (better retrieval, summaries), batch offline work, set max tokens, and add timeouts, retries with backoff, and fallbacks between models.

## Explain temperature, top-p and max tokens.
Tags: basics

Temperature scales randomness (0 ≈ deterministic, higher = more diverse). Top-p samples from the smallest set of tokens whose probability sums to p. Max tokens caps output length (and cost). Low temperature for extraction/classification, higher for brainstorming.
