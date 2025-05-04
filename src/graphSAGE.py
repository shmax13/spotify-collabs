
import csv
import torch
import pandas as pd
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv
from torch_geometric.utils import negative_sampling

ARTISTS_FILE = 'data/artists.csv'
COLLABORATIONS_FILE = 'data/collaborations.csv'
PREDICTIONS_FILE = 'predictions/graphSAGE.csv'

# load torch_geometric Data
def load_graph_data():
    artists = pd.read_csv(ARTISTS_FILE)
    collaborations = pd.read_csv(COLLABORATIONS_FILE)

    # map artist IDs to node indices
    id_to_index = {artist_id: idx for idx, artist_id in enumerate(artists["id"])}

    # build edge_index tensor
    edges = []
    for _, row in collaborations.iterrows():
        a1 = id_to_index.get(row['artist_1'])
        a2 = id_to_index.get(row['artist_2'])
        if a1 is not None and a2 is not None:
            edges.append([a1, a2])
            edges.append([a2, a1])  # ensure bi-directional edges

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    # select and normalize real features
    feature_cols = ['followers', 'popularity', 'num_albums', 'debut_year', 'last_active_year', 'active_years']
    artist_features = artists[feature_cols].fillna(0)
    artist_features = (artist_features - artist_features.mean()) / artist_features.std()

    x = torch.tensor(artist_features.values, dtype=torch.float)

    return Data(x=x, edge_index=edge_index)

# graphSAGE model
class GraphSAGE(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x

# train model for link prediction
def train(model, data, epochs=100, lr=0.01):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()

        out = model(data.x, data.edge_index)

        # positive edges (existing collaborations)
        pos_edge_index = data.edge_index

        # negative edges (non-collaborators)
        neg_edge_index = negative_sampling(
            edge_index=pos_edge_index,
            num_nodes=data.num_nodes,
            num_neg_samples=pos_edge_index.size(1) // 2,
        )

        # compute scores
        pos_scores = (out[pos_edge_index[0]] * out[pos_edge_index[1]]).sum(dim=1)
        neg_scores = (out[neg_edge_index[0]] * out[neg_edge_index[1]]).sum(dim=1)

        # labels: 1 for positive, 0 for negative
        labels = torch.cat([torch.ones_like(pos_scores), torch.zeros_like(neg_scores)])
        scores = torch.cat([pos_scores, neg_scores])

        loss = F.binary_cross_entropy_with_logits(scores, labels)
        loss.backward()
        optimizer.step()

        if epoch % 10 == 0 or epoch == epochs - 1:
            print(f"Epoch {epoch:3d} | Loss: {loss.item():.4f}")

# evaluate, then print output to CSV
def rank_collaborations(model, data, top_k=10, artists=None, artist_ids=None, existing_collabs=None):
    model.eval()
    out = model(data.x, data.edge_index)

    # normalize embeddings to unit vectors
    out = F.normalize(out, p=2, dim=1)

    # cosine similarity = dot product after normalization
    scores = torch.matmul(out, out.t())
    scores.fill_diagonal_(-float('inf'))

    top_k_scores, top_k_indices = torch.topk(scores, top_k, dim=1)

    collaborations = []

    for i in range(scores.size(0)):
        for j, score in zip(top_k_indices[i], top_k_scores[i]):
            id1 = artist_ids[i]
            id2 = artist_ids[j.item()]
            pair = frozenset([id1, id2])
            if existing_collabs is None or pair not in existing_collabs:
                collaborations.append([artists[i], artists[j.item()], score.item()])

    with open(PREDICTIONS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Artist 1", "Artist 2", "Score"])
        writer.writerows(collaborations)

    print(f"Collaborations saved to {PREDICTIONS_FILE}")

def main():
    artists_df = pd.read_csv(ARTISTS_FILE)
    artist_names = artists_df["name"].tolist()
    artist_ids = artists_df["id"].tolist()
    collabs_df = pd.read_csv(COLLABORATIONS_FILE)
    existing_collabs = {frozenset([a, b]) for a, b in zip(collabs_df["artist_1"], collabs_df["artist_2"])}

    data = load_graph_data()
    print(f"Graph loaded: {data.num_nodes} nodes, {data.num_edges} edges")

    model = GraphSAGE(in_channels=data.num_node_features, hidden_channels=32, out_channels=16)

    train(model, data)

    rank_collaborations(model, data, top_k=10, artists=artist_names, artist_ids=artist_ids, existing_collabs=existing_collabs)


if __name__ == "__main__":
    main()