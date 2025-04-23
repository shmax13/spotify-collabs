import csv
from neo4j import GraphDatabase

# Neo4j connection
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "knowledgegraphs")
driver = GraphDatabase.driver(URI, auth=AUTH)

def write_predictions_to_log(
    log_path="data/predicted_collaborations.csv",
    min_common_neighbors=1,
    min_common_genres=0,
    max_popularity_diff=10
):
    query = """
    MATCH (a:Artist)-[:COLLABORATED_WITH]-(common)-[:COLLABORATED_WITH]-(b:Artist)
    WHERE a.id < b.id 
      AND NOT (a)-[:COLLABORATED_WITH]-(b)
    WITH a, b, COUNT(DISTINCT common) AS shared,
         [g IN split(a.genres, ',') WHERE g IN split(b.genres, ',')] AS common_genres,
         abs(a.popularity - b.popularity) AS pop_diff
    WHERE shared >= $min_common_neighbors
      AND size(common_genres) >= $min_common_genres
      AND pop_diff <= $max_popularity_diff
    RETURN a.name AS artist_1, b.name AS artist_2, shared, size(common_genres) AS genre_overlap, pop_diff
    ORDER BY shared DESC
    """

    with driver.session() as session:
        result = session.run(
            query,
            min_common_neighbors=min_common_neighbors,
            min_common_genres=min_common_genres,
            max_popularity_diff=max_popularity_diff
        )

        # Open the log file as a CSV
        with open(log_path, 'w', newline='', encoding='utf-8') as log_file:
            writer = csv.writer(log_file)
            
            # Write header row
            writer.writerow(['Artist 1', 'Artist 2', 'Shared Neighbors', 'Genre Overlap', 'Popularity Diff'])

            # Write the predicted collaborations
            for record in result:
                writer.writerow([
                    record['artist_1'],
                    record['artist_2'],
                    record['shared'],
                    record['genre_overlap'],
                    record['pop_diff']
                ])

            # Optionally print out the results nicely formatted to the console
            print("Predicted Collaborations (Saved to CSV):\n")
            for record in result:
                print(f"{record['artist_1']} x {record['artist_2']} — Shared Neighbors: {record['shared']}, Genre Overlap: {record['genre_overlap']}, Popularity Diff: {record['pop_diff']}")

if __name__ == "__main__":
    write_predictions_to_log()