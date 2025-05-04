# Spotify Collabs

This project was created as part of the Lecture *Knowledge Graphs* at TU Wien during summer semester 2025. Its goal is to perform link prediction on a musical knowledge graph. Nodes represent artists, edges represent collaborations. Therefore, predicting links means predicting potential new collaborations. The source code consists of several pythons scripts which perform different tasks. Their respective tasks are described below.

If you accidentally delete any of the CSV files, there is a backup file for each CSV in the same folder.

## Folder Structure

```
.
├── data/                  # Artist and Collaboration CSV files
├── predictions/           # CSV files containing scored predicted links
├── src/                   # Source code for data processing and models
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile             # Docker image definition for the Neo4j instance
└── requirements.txt       # Python dependencies
```

## Setup

1. Extract the ZIP or clone the repository:

   ```
   git clone https://github.com/shmax13/spotify-collabs.git
   ```

2. Install dependencies (preferably in a new virtual environment):

   ```
   pip install -r requirements.txt
   ```

## Using Docker

To start the Neo4j instance, which is used for the `populate_neo4j.py` and `logical_knowledge.py`  scripts and to look at the data in the Neo4j browser UI.

```
docker-compose up
```

## Running the Project

The project was implemented using VS Code. The `.vscode/launch.json` file contains run configurations for all scripts of the project. If you're not using VS Code, just run them using Python.
Main scripts in `src/`:

- `load_spotify_data.py` – Load and prepare artist data. Warning: It's quite easy to hit Spotify's API request limit.
- `populate_neo4j.py` – Insert data into Neo4j. Uses the CSV files in the `data` folder as input. Requires the Docker instance to be running.
- `logical_knowledge.py` – Run logical rule-based predictions. Requires the Docker instance to be running.
- `node2vec.py` – Run Node2Vec link prediction. Uses CSV files as input.
- `graphSAGE.py` – Run GraphSAGE link prediction. Uses CSV files as input.

## Output

Prediction results are written to the `predictions/` directory as CSV files, one per method.