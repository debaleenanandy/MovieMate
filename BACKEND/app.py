print("Starting backend...")
# =============================
# Imports
# =============================
from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
from rapidfuzz import process, fuzz
from sklearn.metrics.pairwise import cosine_similarity

from transformers import pipeline

print("Loading QA model...")
qa_pipeline = pipeline(
    "question-answering",
    model="deepset/roberta-base-squad2",
    tokenizer="deepset/roberta-base-squad2"
)
print("QA model loaded!")

from transformers import pipeline
from difflib import get_close_matches
import random

print("Loading emotion model...")

emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)

print("Emotion model loaded ✅")

# =============================
# App setup
# =============================
app = Flask(__name__)
CORS(app)

# =============================
# Load data (ONLY ONCE)
# =============================
movie_df = pickle.load(open("DATA/PROCESSED/movies.pkl", "rb"))
similarity = pickle.load(open("DATA/PROCESSED/similarity_matrix.pkl", "rb"))
tfidf = pickle.load(open("DATA/PROCESSED/tfidf.pkl", "rb"))

# =============================
# Helper Functions
# =============================
def format_genres(genres):
    if isinstance(genres, list):
        return ", ".join(genres)

    if isinstance(genres, str):
        # handle different cases
        if "|" in genres:
            return ", ".join(genres.split("|"))
        elif "," in genres:
            return ", ".join([g.strip() for g in genres.split(",")])
        else:
            return genres  # fallback

    return ""

def extract_movie_name_QA(user_input):
    QA_input = {
        'question': 'What is the name of the movie?',
        'context': user_input
    }

    result = qa_pipeline(QA_input)["answer"]
    return result.replace("movie", "").strip()

# 🔍 Find closest movie name
def find_closest_movie(movie_title):
    movie_title = movie_title.lower().strip()
    choices = movie_df['original_title'].str.lower().tolist()

    best_match = process.extractOne(
        movie_title,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=60
    )

    if best_match:
        return movie_df.iloc[best_match[2]]['original_title']
    return None


# 🎬 Movie-based recommendation
def recommend_movies(movie_title, top_n=5):
    try:
        idx = movie_df[
            movie_df['original_title'].str.lower() == movie_title.lower()
        ].index[0]
    except:
        return []

    scores = list(enumerate(similarity[idx]))
    sorted_movies = sorted(scores, key=lambda x: x[1], reverse=True)[1:top_n+1]

    results = []
    for i, _ in sorted_movies:
        m = movie_df.iloc[i]
        results.append({
            "title": m["original_title"],
            "genres": format_genres(m["genres"]),
            "tagline": m.get("tagline", ""),
            "cast": m.get("cast", "")
        })

    return results


# 🔎 Text search recommendation
def recommend_by_text(query, top_n=5):
    vec = tfidf.transform([query])
    scores = cosine_similarity(vec, tfidf.transform(movie_df["tags"])).flatten()
    top_indices = scores.argsort()[::-1][:top_n]

    return [
        {
            "title": movie_df.iloc[i]["original_title"],
            "genres": format_genres(movie_df.iloc[i]["genres"])
        }
        for i in top_indices
    ]


# 🎭 Mood-based recommendation (lightweight)
mood_to_genres = {
    "joyful": ["Comedy", "Animation", "Adventure", "Family", "Music", "Romance"],
    "uplifting": ["Music", "Comedy", "Family", "Romance", "Animation"],
    "relaxed": ["Drama", "Family", "Comedy", "Music", "TV Movie"],
    "quirky": ["Comedy", "Foreign", "Fantasy"],
    "cheerful": ["Comedy", "Romance", "Family", "Music", "Animation"],
    "wholesome": ["Family", "Drama", "Comedy", "TV Movie"],

    # Romantic & Emotional Moods
    "romantic": ["Romance", "Drama", "Comedy", "Music"],
    "nostalgic": ["Family", "TV Movie", "Drama", "Music"],
    "thoughtful": ["Documentary", "Drama", "History", "Foreign"],
    "sad": ["Drama", "Romance", "Documentary", "War", "History"],
    "sentimental": ["Romance", "Drama", "Family", "Music"],
    "melancholic": ["Drama", "History", "War", "Romance"],

    # Thrilling & Intense Moods
    "exciting": ["Action", "Thriller", "Adventure", "Crime", "Science Fiction", "Western"],
    "adventurous": ["Adventure", "Action", "Fantasy", "Science Fiction", "Western"],
    "intense": ["Horror", "Mystery", "Thriller", "War"],
    "dark": ["Crime", "War", "Mystery", "Horror"],
    "epic": ["History", "War", "Adventure", "Science Fiction"],
    "suspenseful": ["Thriller", "Mystery", "Crime", "Horror"],
    "gritty": ["Crime", "Thriller", "War", "Drama"],

    # Challenging & Thought-Provoking Moods
    "imaginative": ["Fantasy", "Science Fiction", "Animation"],
    "scary": ["Horror", "Thriller", "Mystery"],
    "chill": ["TV Movie", "Comedy", "Documentary", "Family"],
    "angry": ["Action", "Thriller", "Crime", "War"],
    "thought-provoking": ["Documentary", "Drama", "History", "Science Fiction"],
    "mysterious": ["Mystery", "Thriller", "Horror", "Crime"],

    # Action-Packed & Energetic Moods
    "fast-paced": ["Action", "Thriller", "Crime", "Science Fiction"],
    "rebellious": ["Action", "Crime", "Thriller", "Western"],
    "powerful": ["War", "History", "Drama", "Adventure"],
    "heroic": ["Adventure", "Action", "Fantasy", "Science Fiction"],

    # Funny & Light-Hearted Moods
    "hilarious": ["Comedy", "Family", "Animation"],
    "sarcastic": ["Comedy", "Drama"],
    "witty": ["Comedy", "Drama", "Mystery"],

    # Dark & Psychological Moods
    "psychological": ["Thriller", "Mystery", "Drama", "Horror"],
    "disturbing": ["Horror", "Crime", "Thriller"],
    "mind-bending": ["Science Fiction", "Mystery", "Thriller"],
    "existential": ["Drama", "Science Fiction", "Documentary"]
}

def find_closest_mood(mood):
    matches = get_close_matches(mood, list(mood_to_genres.keys()), n=1, cutoff=0.5)
    return matches[0] if matches else None

def detect_mood(sentence):
    sentence = sentence.lower().strip()

    results = emotion_classifier(sentence)

    # FIX: handle nested list
    if isinstance(results, list) and isinstance(results[0], list):
        results = results[0]

    best = max(results, key=lambda x: x["score"])
    detected = best["label"].lower()

    # map to closest mood if not exact
    if detected not in mood_to_genres:
        detected = find_closest_mood(detected)

    return detected

def recommend_by_mood(mood, top_n=5):
    genres = mood_to_genres.get(mood)
    if not genres:
        return []

    def check_match(g):
        if isinstance(g, list):
            return any(genre in g for genre in genres)
        elif isinstance(g, str):
            return any(genre.lower() in g.lower() for genre in genres)
        return False

    filtered = movie_df[movie_df["genres"].apply(check_match)]

    return [
        {
            "title": row["original_title"],
            "genres": format_genres(row["genres"])
        }
        for _, row in filtered.head(top_n).iterrows()
    ]

# ⭐ Cast-based recommendation
search_history = set()

def recommend_by_cast(cast_name, top_n=5):
    global search_history

    matches = movie_df[
        movie_df["cast"].str.contains(cast_name, case=False, na=False)
    ]

    matches = matches[~matches["original_title"].isin(search_history)]

    results = matches.head(top_n)

    search_history.update(results["original_title"].tolist())

    return [
        {"title": row["original_title"],
         "genres": format_genres(row["genres"])
         }
        for _, row in results.iterrows()
    ]


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True)
    print("Incoming data:", data)

    input_type = data.get("input_type")
    user_input = data.get("user_input")

    if not input_type:
        return jsonify({"error": "input_type required"}), 400

    if not user_input:
        return jsonify({"error": "user_input required"}), 400

    # 🎬 Movie-based
    if input_type == "movie":
        # Step 1: Extract movie name using QA
        movie_name_QA = extract_movie_name_QA(user_input)
        print("Extracted movie:", movie_name_QA)

        # Step 2: Fuzzy match with dataset
        movie_name = find_closest_movie(movie_name_QA)

        # Step 3: Fallback (if QA fails)
        if not movie_name:
            movie_name = find_closest_movie(user_input)

        # Step 4: Final check
        if not movie_name:
            print("❌ Movie not found triggered")
            return jsonify({"error": "Movie not found. Try another movie 😊"}),200

        # ✅ return inside block
        recs = recommend_movies(movie_name)
        return jsonify({"recommendations": recs})

    # 🔎 Text search
    elif input_type == "text":
        recs = recommend_by_text(user_input)
        return jsonify({"recommendations": recs})

    # 🎭 Mood
    elif input_type == "mood":
        detected_mood = detect_mood(user_input)
        print("Detected mood:", detected_mood)

        # fallback if model fails
        if not detected_mood:
            detected_mood = random.choice(list(mood_to_genres.keys()))

        recs = recommend_by_mood(detected_mood)

        return jsonify({"recommendations": recs})

    # ⭐ Cast
    elif input_type == "cast":
        recs = recommend_by_cast(user_input)
        return jsonify({"recommendations": recs})

    else:
        return jsonify({"error": f"Invalid input_type: {input_type}"}), 400


# =============================
# Run app
# =============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)