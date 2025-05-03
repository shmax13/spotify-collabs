import csv
from neo4j import GraphDatabase

# Neo4j connection
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "knowledgegraphs")
driver = GraphDatabase.driver(URI, auth=AUTH)

def write_predictions_to_log(
    log_path="predictions/logical_rules.csv",
    weight_common_neighbors = 2.0,
    weight_genre_overlap = 5.0,
    weight_popularity = 5.0,
    weight_same_country = 2.0,
    weight_same_city = 5.0,
):
    query = """
        MATCH (a:Artist)-[:COLLABORATED_WITH]-(common)-[:COLLABORATED_WITH]-(b:Artist)
        WHERE a.id < b.id 
        AND NOT (a)-[:COLLABORATED_WITH]-(b)
        WITH a, b, 
            COUNT(DISTINCT common) AS shared,
            [g IN split(a.genres, ',') WHERE g IN split(b.genres, ',')] AS common_genres,
            abs(a.popularity - b.popularity) AS pop_diff,
            (a.country IS NOT NULL AND b.country IS NOT NULL AND a.country <> '' AND b.country <> '' AND a.country = b.country) AS same_country,
            (a.begin_area IS NOT NULL AND b.begin_area IS NOT NULL AND a.begin_area <> '' AND b.begin_area <> '' AND a.begin_area = b.begin_area) AS same_city
        WITH a.name AS artist_1, b.name AS artist_2,
            shared, 
            size(common_genres) AS genre_overlap,
            pop_diff,
            same_country,
            same_city,
            (shared * $weight_common_neighbors) +
            (size(common_genres) * $weight_genre_overlap) +
            (1.0 / (1 + pop_diff)) * $weight_popularity +
            (CASE WHEN same_country THEN $weight_same_country ELSE 0 END) +
            (CASE WHEN same_city THEN $weight_same_city ELSE 0 END) AS score
        RETURN artist_1, artist_2, shared, genre_overlap, pop_diff, same_country, same_city, score
        ORDER BY score DESC
    """

    with driver.session() as session:
        result = session.run(
            query,

            weight_common_neighbors=weight_common_neighbors,
            weight_genre_overlap=weight_genre_overlap,
            weight_popularity=weight_popularity,
            weight_same_country=weight_same_country,
            weight_same_city=weight_same_city,
        )

        # Open the log file as a CSV
        with open(log_path, 'w', newline='', encoding='utf-8') as log_file:
            writer = csv.writer(log_file)
            
            # Write header row
            writer.writerow([
                'Artist 1', 'Artist 2', 'Shared Neighbors',
                'Genre Overlap', 'Popularity Diff',
                'Same Country', 'Same City', 'Score'
            ])

            # Write the predicted collaborations
            for record in result:
                writer.writerow([
                    record['artist_1'],
                    record['artist_2'],
                    record['shared'],
                    record['genre_overlap'],
                    record['pop_diff'],
                    record['same_country'],
                    record['same_city'],
                    round(record['score'], 2)
                ])
        print("Prediction using logical rules complete.")

if __name__ == "__main__":
    write_predictions_to_log()