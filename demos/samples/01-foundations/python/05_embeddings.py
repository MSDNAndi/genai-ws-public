# /// script
# requires-python = ">=3.12"
# dependencies = ["genaiclass"]
#
# [tool.uv.sources]
# genaiclass = { path = "../../../shared/python", editable = true }
# ///
# %% [markdown]
# # 05 - Embeddings and similarity
#
# An embedding turns text into a point in a few-thousand-dimensional space where
# "close" means "about the same thing". That is the whole basis of semantic
# search, RAG, clustering, dedup and recommendation.
#
# ```bash
# uv run 05_embeddings.py --profile mock
# ```

# %%
import math

from genaiclass import banner, get_profile, make_client

profile = get_profile()
client = make_client(profile)
print(banner(profile) + f"  (embeddings: {profile.embed_model})")


def embed(text: str) -> list[float]:
    return client.embeddings.create(model=profile.embed_model, input=text).data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """1.0 = same direction, 0 = unrelated. Embeddings are usually unit length,
    so this is really just a dot product - but be explicit for teaching."""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


# %%
vector = embed("cute dog")
print(f"dimensions: {len(vector)}")
print(f"first five: {[round(v, 4) for v in vector[:5]]}")

# %% [markdown]
# ## The uncomfortable part
#
# Embeddings capture *topic*, not *truth*. "John likes ice cream" and "John
# dislikes ice cream" are near-identical neighbours: same words, same subject,
# opposite meaning. Retrieval that only ranks by cosine similarity will happily
# hand the model the sentence that says the opposite of what the user asked.

# %%
sentences = [
    "John really does like ice cream",
    "John really does dislike ice cream",
    "John does not like ice cream at all",
    "The quarterly revenue report is attached",
]
reference = embed(sentences[0])
for sentence in sentences:
    print(f"{cosine_similarity(reference, embed(sentence)):.4f}  {sentence}")

# %% [markdown]
# ## Ranking a tiny corpus
#
# This is RAG with the interesting parts removed: embed the documents once,
# embed the question, sort by similarity, put the winners in the prompt. Lab 2
# adds chunking, a real vector store, hybrid search and a reranker - all of which
# exist because the similarity above is a blunt instrument.

# %%
corpus = [
    "The espresso machine needs descaling every 200 shots.",
    "Cats sleep roughly 15 hours a day.",
    "Our refund window is 30 days from delivery.",
    "To reset the router, hold the button for ten seconds.",
]
corpus_vectors = [embed(document) for document in corpus]

question = "How long do I have to send something back?"
question_vector = embed(question)

ranked = sorted(
    ((cosine_similarity(question_vector, v), d) for v, d in zip(corpus_vectors, corpus)),
    reverse=True,
)
print(f"Q: {question}")
for score, document in ranked:
    print(f"  {score:.4f}  {document}")

# %% [markdown]
# Notes for production:
#
# * Dimensions cost money and memory. `text-embedding-3-large` is 3072-d but
#   supports shortening via `dimensions=` with modest quality loss.
# * **You cannot mix models.** Vectors from two different embedding models are
#   not comparable - changing the model means re-indexing everything.
# * Cheap local option: `bge-m3` on Ollama. Same code, `--profile ollama`.
