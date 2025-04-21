import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import csv
import os
import time

# Spotify API credentials
# not concealed so this can be easily run
MY_CLIENT_ID = 'b2ff37d52bcc4441b0282edee1d54283'
MY_CLIENT_SECRET = '656be244cf7c4ca6b7134bc13c415f83'

# auth setup
client_credentials_manager = SpotifyClientCredentials(client_id=MY_CLIENT_ID, client_secret=MY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

ARTISTS_FILE = 'data/artists.csv'
COLLABORATIONS_FILE = 'data/collaborations.csv'

# get artist details from artist ID
def get_artist_info(artist_id):
    artist = sp.artist(artist_id)
    return {
        'id': artist['id'],
        'name': artist['name'],
        'followers': artist['followers']['total'],
        'genres': ', '.join(artist['genres']),
        'popularity': artist['popularity'],
    }

# get collaborations from artist ID
def get_collaborations(artist_id):
    collaborations = set()
    try:
        albums = sp.artist_albums(artist_id, album_type='album', limit=50)
        for album in albums['items']:
            tracks = sp.album_tracks(album['id'], limit=50)
            for track in tracks['items']:
                for artist in track['artists']:
                    if artist['id'] != artist_id:
                        collaborations.add(artist['id'])
        return sorted(collaborations)

    except Exception as e:
        print(f"Error retrieving collaborations for {artist_id}: {e}")
        return set()


# save artist info
def save_artist(artist):
    file_exists = os.path.exists(ARTISTS_FILE)
    with open(ARTISTS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['id', 'name', 'followers', 'genres', 'popularity']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(artist)

# save collaboration info
def save_collaboration(artist1, artist2):
    file_exists = os.path.exists(COLLABORATIONS_FILE)
    with open(COLLABORATIONS_FILE, 'a', newline='') as csvfile:
        fieldnames = ['artist_id', 'collaboration_id']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({'artist_id': artist1, 'collaboration_id': artist2})

# clear CSV files
def clear_csv_files():
    for file in [ARTISTS_FILE, COLLABORATIONS_FILE]:
        if os.path.exists(file):
            open(file, 'w').close()
    print("Cleared all CSV files.")

# get artists from a given genre
def search_artists_by_genre(genre_name, limit=50):
    artists = []
    seen_ids = set()
    offset = 0

    while len(artists) < limit:
        result = sp.search(q=f'genre:"{genre_name}"', type='artist', limit=50, offset=offset)
        new_artists = result.get('artists', {}).get('items', [])

        if not new_artists:
            break  # no more results

        for artist in new_artists:
            if artist['id'] not in seen_ids:
                artists.append({
                    'id': artist['id'],
                    'name': artist['name'],
                    'followers': artist['followers']['total'],
                    'genres': ', '.join(artist.get('genres', [])),
                    'popularity': artist['popularity']
                })
                seen_ids.add(artist['id'])
            if len(artists) >= limit:
                break

        offset += 50

    return artists

# save artist & collaboration info from a given genre
def build_genre_graph(genre_name, top_x=50):

    ensure_csv_headers()

    # Step 1: Get top X artists by genre
    print(f"Searching top {top_x} artists for genre: {genre_name}")
    artists = search_artists_by_genre(genre_name, limit=top_x)
    if not artists:
        print("No artists found.")
        return

    # Step 2: Save artist info
    discovered_ids = set()
    for artist in artists:
        artist_id = artist['id']
        save_artist(artist)
        discovered_ids.add(artist_id)

    # Step 3: Save intra-group collaborations
    print("Finding internal collaborations...")
    for artist in artists:
        artist_id = artist['id']
        collaborations = get_collaborations(artist_id)

        for collab_id in collaborations:
            if collab_id in discovered_ids:
                save_collaboration(artist_id, collab_id)

       # try not to hit API limits 
        time.sleep(1)

    print(f"Finished building genre graph with {len(discovered_ids)} artists.")

# add headers to CSV files so they can be parsed later
def ensure_csv_headers():
    header_artists = ["id", "name", "followers", "genres", "popularity"]
    header_collabs = ["artist_1", "artist_2"]
    
    if not os.path.exists(ARTISTS_FILE) or os.stat(ARTISTS_FILE).st_size == 0:
        with open(ARTISTS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header_artists) 

    if not os.path.exists(COLLABORATIONS_FILE) or os.stat(COLLABORATIONS_FILE).st_size == 0:
        with open(COLLABORATIONS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(header_collabs) 

def main():
    # Step 0: Clean up existing files (optional)
    clear_csv_files()

    # Step 1: Start building the artist graph
    genre = "Art Pop"  # Change this to any starting artist
    max_artists = 100  # Adjust based on how big you want the dataset to be

    print(f"Getting {max_artists} {genre} artists...")
    build_genre_graph(genre, max_artists)
    
    print("Data collection complete.")

if __name__ == "__main__":
    main()