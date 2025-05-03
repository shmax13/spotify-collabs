import os
import sys
import torch
import pandas as pd

ARTISTS_FILE = 'data/artists.csv'
COLLABORATIONS_FILE = 'data/collaborations.csv'

try:
    from torch_geometric.data import Data
    from torch_geometric.nn import SAGEConv
except ImportError:
    print("❌ PyTorch Geometric is not installed.")
    print("Install with: pip install torch-geometric")
    sys.exit(1)

# === File Checks ===
required_files = [ARTISTS_FILE, COLLABORATIONS_FILE]
for file in required_files:
    if not os.path.exists(file):
        print(f"❌ Required file missing: {file}")
        sys.exit(1)

print("✅ All files and dependencies found.")

# === Load Data ===
def load_graph_data():
    artists = pd.read_csv("artists.csv")
    collaborations = pd.read_csv("collaborations.csv")

    # Map artist IDs to node indices
    id_to_index = {artist_id: idx for idx, artist_id in enumerate(artists["id"])}

    # Edge index (2, num_edges) tensor
    edges = []
    for _, row in collaborations.iterrows():
        a1 = id_to_index.get(row['artist_1'])
        a2 = id_to_index.get(row['artist_2'])
        if a1 is not None and a2 is not None:
            edges.append([a1, a2])
            edges.append([a2, a1])  # undirected graph

    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    # Use dummy features for now (you'll replace this later)
    x = torch.randn(len(artists), 16)

    return Data(x=x, edge_index=edge_index)

# === GraphSAGE Model ===
class GraphSAGE(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, hidden_channels)
        self.conv2 = SAGEConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index).relu()
        x = self.conv2(x, edge_index)
        return x

# === Entry Point ===
if __name__ == "__main__":
    data = load_graph_data()
    print(f"Graph loaded: {data.num_nodes} nodes, {data.num_edges} edges")

    model = GraphSAGE(in_channels=data.num_node_features, hidden_channels=32, out_channels=16)
    out = model(data.x, data.edge_index)
    print(f"✅ Model output shape: {out.shape}")