# %%
from embedder import Embedder

embed = Embedder()

q1 = "How does approximate nearest neighbor search work?"
q2 = "How to install Docker on Windows?"
d  = "You don't need to register. You're accepted. You can also just start learning and submitting homework without registering."

v1 = embed.encode(q1)
v2 = embed.encode(q2)
dv = embed.encode(d)

# %%
v1.dot(dv)

# %%
v1.dot(dv)

# %%
from gitsource import GithubRepositoryDataReader

reader = GithubRepositoryDataReader(
    repo_owner="DataTalksClub",
    repo_name="llm-zoomcamp",
    commit_id="8c1834d",
    allowed_extensions={"md"},
    filename_filter=lambda path: "/lessons/" in path,
)

documents = [file.parse() for file in reader.read()]

# %%
documents[0]

# %%
texts = [doc["filename"] + " " + doc["content"] for doc in documents]

# %%
from tqdm.auto import tqdm
import numpy as np

batch_size = 50
X = []

for i in tqdm(range(0, len(texts), batch_size)):
    batch = texts[i:i + batch_size]
    batch_vectors = embed.encode_batch(batch)
    X.extend(batch_vectors)

X = np.array(X)

# %%
query = "How does approximate nearest neighbor search work?"
v_query = embed.encode(query)

scores = X.dot(v_query)
idx = np.argmax(scores)

documents[idx]

# %%
v_query[0]

# %%
from sqlitesearch import VectorSearchIndex

vs_index = VectorSearchIndex(

    mode="ivf",
    db_path="vectors.db"
)

# %%
vs_index.fit(X, documents)

# %%
query_vector = embed.encode(query)

results = vs_index.search(query_vector, num_results=5)

# %%

similarity = np.dot(query_vector, results)

print(similarity)



# %%


# %%



