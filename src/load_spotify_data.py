import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import csv
import os
import time
import musicbrainzngs
import pandas as pd

# Spotify API credentials
# not concealed so this can be easily run
MY_CLIENT_ID = '171c422d25de4589a5f076d40dd57de2'
MY_CLIENT_SECRET = '17c4c41877244f85b3ed0e85355a5df1'

# auth setup
client_credentials_manager = SpotifyClientCredentials(client_id=MY_CLIENT_ID, client_secret=MY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager, requests_timeout=20)

# setup MusicBrainz
musicbrainzngs.set_useragent("spotifycollabs", "0.1", "maximilian.j.pfeil@gmail.com")

ARTISTS_FILE = 'data/artists.csv'
COLLABORATIONS_FILE = 'data/collaborations.csv'

# get artist country and begin_area from musicbrainz
def get_musicbrainz_info(artist_name):
    try:
        result = musicbrainzngs.search_artists(artist=artist_name, limit=1)
        if result['artist-list']:
            artist = result['artist-list'][0]
            return {
                'country': artist.get('country'),
                'begin_area': artist.get('begin-area', {}).get('name')
            }
    except Exception as e:
        print(f"MusicBrainz error for '{artist_name}': {e}")
    return {'country': None, 'begin_area': None}

# get most artist data from spotify API
def get_artist_info(artist_id):
    artist = sp.artist(artist_id)
    albums = sp.artist_albums(artist_id, album_type='album', limit=25)['items']
    years = []

    for album in albums:
        if 'release_date' in album:
            year = album['release_date'].split('-')[0]
            if year.isdigit():
                years.append(int(year))

    debut_year = min(years) if years else None
    last_active_year = max(years) if years else None
    active_years = last_active_year - debut_year + 1 if debut_year and last_active_year else None

    # get extra info from MusicBrainz
    mb_info = get_musicbrainz_info(artist['name'])

    return {
        'id': artist['id'],
        'name': artist['name'],
        'followers': artist['followers']['total'],
        'genres': ', '.join(artist['genres']),
        'popularity': artist['popularity'],
        'num_albums': len(albums),
        'debut_year': debut_year,
        'last_active_year': last_active_year,
        'active_years': active_years,
        'country': mb_info['country'],
        'begin_area': mb_info['begin_area']
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
    with open(ARTISTS_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'id', 'name', 'followers', 'genres', 'popularity',
            'num_albums', 'debut_year', 'last_active_year', 'active_years', 'country', 'begin_area'
        ]
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
            break  # no more results. can happen if searching a lesser known genre

        for artist in new_artists:
            if artist['id'] not in seen_ids:
                artist_info = get_artist_info(artist['id'])

                # try avoid API limits
                time.sleep(0.5)
                print(artist_info['name'])

                # Add the fetched artist info to the artists list
                artists.append({
                    'id': artist_info['id'],
                    'name': artist_info['name'],
                    'followers': artist_info['followers'],
                    'genres': artist_info['genres'],
                    'popularity': artist_info['popularity'],
                    'num_albums': artist_info['num_albums'],
                    'debut_year': artist_info['debut_year'],
                    'last_active_year': artist_info['last_active_year'],
                    'active_years': artist_info['active_years'],
                    'country': artist_info['country'],
                    'begin_area': artist_info['begin_area']
                })
                seen_ids.add(artist['id'])

            if len(artists) >= limit:
                break

        offset += 50

    return artists

# this is used to fill up the CSVs continuously 
# as API limits tend to shut down the main script occasionally.
def fill_collaborations_from_existing_artists():
    # Load existing artist IDs
    artists_df = pd.read_csv(ARTISTS_FILE)
    artist_ids = set(artists_df["id"])

    try:
        collab_df = pd.read_csv(COLLABORATIONS_FILE)
        existing_pairs = set(tuple(sorted([row['artist_1'], row['artist_2']])) for _, row in collab_df.iterrows())
        processed_artists = set((row['artist_1']) for _, row in collab_df.iterrows())
    except FileNotFoundError:
        existing_pairs = set()

    total = len(artist_ids)
    for idx, artist_id in enumerate(artist_ids):
        if artist_id in processed_artists:
            print(f"[{idx+1}/{total}] {artist_id} already processed.")
            continue
        else:
            print(f"[{idx+1}/{total}] Processing {artist_id}...")

        try:
            collabs = get_collaborations(artist_id)
        except Exception as e:
            print(f"Error for {artist_id}: {e}")
            continue

        new_entries = []
        for collab_id in collabs:
            if collab_id in artist_ids:
                pair = tuple(sorted([artist_id, collab_id]))
                if pair not in existing_pairs:
                    new_entries.append({"artist_1": pair[0], "artist_2": pair[1]})
                    existing_pairs.add(pair)

        if new_entries:
            pd.DataFrame(new_entries).to_csv(COLLABORATIONS_FILE, mode='a', header=False, index=False)

        time.sleep(0.5)  # avoid hitting rate limit

# save artist & collaboration info from a given genre
def build_genre_graph(genre_name, top_x=50):

    ensure_csv_headers()

    # Step 1: Get top X artists by genre
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

    # Step 3: Save collaborations
    print("Finding internal collaborations...")
    total_artists = len(artists)
    progress_interval = total_artists // 10  # log progress every 10% of artists processed
    processed = 0

    for artist in artists:
        artist_id = artist['id']
        collaborations = get_collaborations(artist_id)

        for collab_id in collaborations:
            if collab_id in discovered_ids:
                save_collaboration(artist_id, collab_id)

        # log progress
        processed += 1
        if processed % progress_interval == 0 or processed == total_artists:
            print(f"Progress: {processed}/{total_artists} artists processed...")

        # try avoid API limit
        time.sleep(0.5)

# add headers to CSV files so they can be parsed later
def ensure_csv_headers():
    header_artists = ["id", "name", "followers", "genres", "popularity", "num_albums",
                       "debut_year", "last_active_year", "active_years", "country", "begin_area"]
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
    # clean up existing files (optional)
    # there is backup CSV files in case these are accidentally deleted
    clear_csv_files()

    genre = "Pop" 
    max_artists = 1000 

    print(f"Getting {max_artists} {genre} artists...")
    build_genre_graph(genre, max_artists)
    
    print("Data collection complete.")

if __name__ == "__main__":
    # main()
    fill_collaborations_from_existing_artists()