import requests
import json
from flask import Flask, request, jsonify

# --- Configuration ---
# Deezer API base URL for search
DEEZER_API_URL = "https://api.deezer.com/search"
# Target number of songs to return
TARGET_SONGS = 5
# Default search query
DEFAULT_QUERY = "lofi"

# --- Flask App Initialization ---
app = Flask(__name__)

@app.route('/playlist', methods=['GET'])
def get_playlist():
    """
    Fetches a list of songs from the Deezer API based on a query parameter.
    
    Query Parameter:
        q (str): The search term (e.g., 'lofi'). Defaults to 'lofi'.
    
    Returns:
        JSON list of song objects or an error message.
    """
    
    # 1. Get query parameter 'q' with a default value
    query = request.args.get('q', DEFAULT_QUERY)
    
    app.logger.info(f"Received request for query: {query}")
    
    # 2. Prepare API Request
    params = {
        'q': query,
        # Deezer API allows limiting the number of results, but we'll fetch a bit more 
        # to ensure we can meet the 5-song requirement after filtering for preview_url and duplicates.
        'limit': 20 
    }
    
    try:
        # 3. Call Deezer API
        response = requests.get(DEEZER_API_URL, params=params, timeout=10)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()
        
    # 7. Add error handling for API call failure
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Deezer API request failed: {e}")
        return jsonify({
            "error": "External API Error", 
            "message": "Could not connect to or retrieve data from the Deezer API."
        }), 503 # Service Unavailable
    
    
    # 4 & 5. Process and Filter API Response
    
    # Check if 'data' field exists and is a list (Deezer API structure)
    if 'data' not in data or not isinstance(data['data'], list):
        app.logger.warning("Deezer API response missing 'data' field or is malformed.")
        return jsonify({
            "error": "No Songs Found", 
            "message": f"No results found for query '{query}' or API response was unexpected."
        }), 404
        
    songs = data['data']
    filtered_playlist = []
    seen_track_ids = set() # For checking duplicates
    
    for song in songs:
        # Extract fields
        title = song.get('title')
        artist_name = song.get('artist', {}).get('name')
        preview_url = song.get('preview')
        track_id = song.get('id') # Use track ID for robust duplicate checking
        
        # 5. Only include if preview URL is available and it's not a duplicate
        if preview_url and track_id not in seen_track_ids:
            
            # 6. Format the result object
            track_info = {
                "title": title,
                "artist": artist_name,
                "preview_url": preview_url
            }
            
            filtered_playlist.append(track_info)
            seen_track_ids.add(track_id)
            
            # Stop once we have 5 songs
            if len(filtered_playlist) >= TARGET_SONGS:
                break
                
    # 7. Error handling for not enough songs found
    if not filtered_playlist:
        app.logger.info(f"No songs with preview URL found for query: {query}")
        return jsonify({
            "error": "No Songs Found", 
            "message": f"Could not find any songs with a preview URL for query '{query}'. Try a different search term."
        }), 404
    
    # 8. Success: Return the final list of songs
    return jsonify(filtered_playlist), 200

# --- Run the App ---
if __name__ == '__main__':
    # Setting debug=True for local development
    # In a production environment, use a proper WSGI server (e.g., Gunicorn, Waitress)
    app.run(debug=True, port=5000)