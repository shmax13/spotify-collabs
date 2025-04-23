from neo4j import GraphDatabase
import csv

# neo4j connection
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "knowledgegraphs")
driver = GraphDatabase.driver(URI, auth=AUTH)

# clear all nodes and relationships
def clear_all():
    with driver.session() as session:
        print("Clearing all nodes and relationships...")
        session.run("MATCH (n) DETACH DELETE n")
        print("All nodes and relationships have been cleared.")

# create artists (nodes)
def create_artist(tx, artist_id, name, followers, genres, popularity, num_albums,
                   debut_year, last_active_year, active_years, country, begin_area):
    query = """
    MERGE (a:Artist {id: $artist_id})
    SET a.name = $name,
        a.followers = $followers,
        a.genres = $genres,
        a.popularity = $popularity,
        a.num_albums = $num_albums,
        a.debut_year = $debut_year,
        a.last_active_year = $last_active_year,
        a.active_years = $active_years,
        a.country = $country,
        a.begin_area = $begin_area
    """
    tx.run(query,
        artist_id=artist_id,
        name=name,
        followers=followers,
        genres=genres,
        popularity=popularity,
        num_albums=num_albums,
        debut_year=debut_year,
        last_active_year=last_active_year,
        active_years=active_years,
        country=country,
        begin_area=begin_area
    )

# create collaborations (edges)
def create_collaboration(tx, artist_1, artist_2):
    query = """
    MATCH (a1:Artist {id: $artist_1}), (a2:Artist {id: $artist_2})
    MERGE (a1)-[:COLLABORATED_WITH]->(a2)
    """
    tx.run(query, artist_1=artist_1, artist_2=artist_2)

# load artists from CSV
def load_artists(csv_file):
    with driver.session() as session:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                session.execute_write(
                    create_artist,
                    row["id"],
                    row["name"],
                    int(row["followers"]) if row["followers"] else 0,
                    row["genres"],
                    int(row["popularity"]) if row["popularity"] else 0,
                    int(row["num_albums"]) if row.get("num_albums") else 0,
                    int(row["debut_year"]) if row.get("debut_year") else 0,
                    int(row["last_active_year"]) if row.get("last_active_year") else 0,
                    int(row["active_years"]) if row.get("active_years") else 0,
                    row["country"],
                    row["begin_area"]
                )

# load collaborations from CSV
def load_collaborations(csv_file):
    with driver.session() as session:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                session.execute_write(create_collaboration, row["artist_1"], row["artist_2"])


def main():
    clear_all()
    load_artists("data/artists.csv")
    load_collaborations("data/collaborations.csv")
    driver.close()

if __name__ == "__main__":
    main()