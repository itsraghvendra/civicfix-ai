"""
CivicFix AI - Duplicate Complaint Detector
Advisory duplicate detection using TF-IDF vectorization and cosine similarity.
"""

from typing import Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import database

DUPLICATE_SIMILARITY_THRESHOLD = 0.58


def check_for_duplicates(title: str, description: str, locality: str = "", category: str = "", image_path: str = "") -> Dict[str, Any]:
    """
    Checks incoming complaint against existing complaints in the SQLite database.
    Evaluates text (title, description, locality, category) and image signals.
    Returns advisory duplicate status, tracking ID of the closest report, similarity score, and explanation.
    Never automatically rejects or deletes complaints.
    """
    default_result = {
        "is_duplicate": False,
        "duplicate_of": None,
        "similarity_score": 0.0,
        "matched_title": None,
        "matched_locality": None,
        "matched_status": None,
        "explanation": "No similar recent reports found in this locality.",
    }

    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT tracking_id, title, description, locality, category, status, image_path FROM complaints ORDER BY id DESC LIMIT 50")
        existing_records = cursor.fetchall()
        conn.close()

        if not existing_records:
            return default_result

        # Prepare corpus
        new_text = f"{title} {description} {locality} {category}".strip().lower()
        existing_texts = [
            f"{rec['title']} {rec['description']} {rec['locality']} {rec['category']}".strip().lower()
            for rec in existing_records
        ]

        all_documents = [new_text] + existing_texts

        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(all_documents)

        # Compute cosine similarity between the new complaint (index 0) and all existing ones (index 1..)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])[0]

        if len(similarities) == 0:
            return default_result

        max_idx = similarities.argmax()
        max_score = float(similarities[max_idx])

        # If identical image path or same image hash, boost score
        if image_path and existing_records[max_idx]["image_path"] and image_path == existing_records[max_idx]["image_path"]:
            max_score = min(1.0, max_score + 0.25)

        if max_score >= DUPLICATE_SIMILARITY_THRESHOLD:
            matched_rec = existing_records[max_idx]
            explanation = (
                f"Shares high similarity ({round(max_score * 100)}%) with report {matched_rec['tracking_id']} "
                f"in {matched_rec['locality']} regarding {matched_rec['title']}."
            )
            return {
                "is_duplicate": True,
                "duplicate_of": matched_rec["tracking_id"],
                "similarity_score": round(max_score, 2),
                "matched_title": matched_rec["title"],
                "matched_locality": matched_rec["locality"],
                "matched_status": matched_rec["status"],
                "explanation": explanation,
            }

        return default_result

    except Exception as e:
        # Fallback cleanly if TF-IDF fails (e.g. extremely short strings or vocab errors)
        return default_result

