import pandas as pd
import torch
from torch_geometric.nn import Node2Vec
from sklearn.metrics.pairwise import cosine_similarity

artists_df = pd.read_csv("data/artists.csv")
collabs_df = pd.read_csv("data/collaborations.csv")

# keep only artists that appear in collaborations
connected_ids = set(collabs_df["artist_1"]) | set(collabs_df["artist_2"])
artists_df = artists_df[artists_df["id"].isin(connected_ids)].reset_index(drop=True)

# rebuild mappings
id_map = {artist_id: idx for idx, artist_id in enumerate(artists_df["id"])}

edges = []
for a, b in zip(collabs_df["artist_1"], collabs_df["artist_2"]):
    a1 = id_map.get(a)
    a2 = id_map.get(b)
    if a1 is not None and a2 is not None:
        edges.append([a1, a2])
        edges.append([a2, a1])  # ensure bi-directional edges

edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

node2vec = Node2Vec(
    edge_index,
    embedding_dim=32,
    walk_length=15,  
    context_size=10,
    walks_per_node=10,  
    num_negative_samples=5,  
    sparse=True
)

# Training setup
device = 'cuda' if torch.cuda.is_available() else 'cpu'
node2vec = node2vec.to(device)
loader = node2vec.loader(batch_size=128, shuffle=True)
optimizer = torch.optim.SparseAdam(list(node2vec.parameters()), lr=0.01)

# 1 epoch of training
def train():
    node2vec.train()
    total_loss = 0
    for pos_rw, neg_rw in loader:
        optimizer.zero_grad()
        loss = node2vec.loss(pos_rw.to(device), neg_rw.to(device))
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(loader)

# training loop
for epoch in range(1, 201):
    loss = train()
    print(f"Epoch {epoch:03d} | Loss: {loss:.4f}")

# prepare to score unconnected nodes
node2vec.eval()
embeddings = node2vec.embedding.weight.detach().cpu()
num_nodes = len(artists_df)
existing = set(tuple(sorted((id_map[a], id_map[b]))) for a, b in zip(collabs_df["artist_1"], collabs_df["artist_2"]))
scores = []

# scoring
for i in range(num_nodes):
    for j in range(i + 1, num_nodes):
        if (i, j) not in existing:
            sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
            scores.append((i, j, sim))

# sort top results - similar to how it is logged for prediction with logical rule
top_links = sorted(scores, key=lambda x: x[2], reverse=True)[:200]

# write results to CSV
csv_data = []
for i, j, score in top_links:
    artist_1_name = artists_df.loc[i, 'name']
    artist_2_name = artists_df.loc[j, 'name']
    csv_data.append([artist_1_name, artist_2_name, score])
csv_df = pd.DataFrame(csv_data, columns=["Artist 1", "Artist 2", "Score"])
csv_df.to_csv("predictions/node2vec.csv", index=False)