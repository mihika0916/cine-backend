from flask import Flask, request
from flask_cors import CORS
from models import db, Movie, Rating, Genre, movie_genres
from sqlalchemy import text
from datetime import datetime, timedelta
from flask import request



app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)



def safe_iso(dt):
    if isinstance(dt, str):
        try:
            return datetime.fromisoformat(dt).isoformat()
        except ValueError:
            return dt
    elif isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)

with app.app_context():

    db.create_all()

    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_movie_id ON ratings(movie_id)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_genre_id ON movie_genres(genre_id)"))
    db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_watched_at ON ratings(watched_at)"))
    
    db.session.commit()

@app.route("/")
def home():
    return {"message": "Hello from Flask!"}

@app.route("/movies")
def get_movies():
    return [m.serialize() for m in Movie.query.all()]

@app.route("/rate", methods=["POST"])
def rate_movie():
    data = request.json
    tmdb_id = data.get("tmdb_id")
    score = data.get("score")

    if not tmdb_id or not score:
        return {"error": "Missing tmdb_id or score"}, 400

    # get the internal Movie ID
    movie = Movie.query.filter_by(tmdb_id=tmdb_id).first()
    if not movie:
        return {"error": "Movie not found in DB"}, 404

    rating = Rating(
        movie_id=movie.id,
        score=score,
        review=data.get("review", "")
    )
    db.session.add(rating)
    db.session.commit()
    return {"message": "Rating submitted!"}


@app.route("/rate/<int:rating_id>", methods=["PUT"])
def update_rating(rating_id):
    data = request.json
    rating = Rating.query.get_or_404(rating_id)

    if "score" in data:
        rating.score = data["score"]
    if "review" in data:
        rating.review = data["review"]

    db.session.commit()
    return {"message": "Rating updated successfully!"}


@app.route("/rate/<int:rating_id>", methods=["DELETE"])
def delete_rating(rating_id):
    rating = Rating.query.get_or_404(rating_id)
    db.session.delete(rating)
    db.session.commit()
    return {"message": "Rating deleted successfully!"}


@app.route("/rate/<int:rating_id>", methods=["GET"])
def get_rating(rating_id):
    rating = Rating.query.get_or_404(rating_id)
    movie = Movie.query.get(rating.movie_id)
    return {
        "movie_title": movie.title,
        "score": rating.score,
        "review": rating.review,
        "watched_at": rating.watched_at.isoformat()
    }

@app.route("/add-genres")
def add_genres():
    genre_map = {
        28: "Action",
        12: "Adventure",
        16: "Animation",
        35: "Comedy",
        80: "Crime",
        99: "Documentary",
        18: "Drama",
        10751: "Family",
        14: "Fantasy",
        36: "History",
        27: "Horror",
        10402: "Music",
        9648: "Mystery",
        10749: "Romance",
        878: "Science Fiction",
        10770: "TV Movie",
        53: "Thriller",
        10752: "War",
        37: "Western"
    }
    for id, name in genre_map.items():
        if not Genre.query.get(id):
            db.session.add(Genre(id=id, name=name))
    db.session.commit()
    return {"message": "Genres added!"}

@app.route("/genres")
def get_genres():
    return [{"id": g.id, "name": g.name} for g in Genre.query.all()]


@app.route("/rated-movies")
def rated_movies():
    ratings = Rating.query.all()
    result = []
    for r in ratings:
        movie = Movie.query.get(r.movie_id)
        result.append({
            "movie_title": movie.title,
            "rating": r.score,
            "review": r.review
        })
    return result

@app.route("/report/<int:movie_id>")
def report(movie_id):
    range_filter = request.args.get("range", "all")
    query = Rating.query.filter_by(movie_id=movie_id)

    if range_filter == "day":
        since = datetime.now() - timedelta(days=1)
        query = query.filter(Rating.created_at >= since)
    elif range_filter == "week":
        since = datetime.now() - timedelta(weeks=1)
        query = query.filter(Rating.created_at >= since)

    result = [
        {"score": r.score, "review": r.review}
        for r in query.all()
    ]
    return result

@app.route("/report-all")
def report_all():
    range_filter = request.args.get("range", "all")
    query = Rating.query.join(Movie).options(db.joinedload(Rating.movie))

    if range_filter == "day":
        since = datetime.now() - timedelta(days=1)
        query = query.filter(Rating.watched_at >= since)
    elif range_filter == "week":
        since = datetime.now() - timedelta(weeks=1)
        query = query.filter(Rating.watched_at >= since)

    result = [
        {
            "id": r.id,
            "score": r.score,
            "review": r.review,
            "watched_at": r.watched_at.isoformat(),
            "movie_title": r.movie.title  # ✅ now this works!
        }
        for r in query.all()
    ]
    return result

@app.route("/report-by-genre-ps")
def report_by_genre_prepared():
    genre_id = request.args.get("genre_id", type=int)
    range_filter = request.args.get("range", "all")


    base_sql = """
        SELECT ratings.id, ratings.score, ratings.review, ratings.watched_at, movies.title AS movie_title
        FROM ratings
        JOIN movies ON ratings.movie_id = movies.id
        JOIN movie_genres ON movies.id = movie_genres.movie_id
        WHERE movie_genres.genre_id = :genre_id
    """

    params = {"genre_id": genre_id}

    if range_filter == "day":
        base_sql += " AND ratings.watched_at >= :since"
        params["since"] = datetime.now() - timedelta(days=1)
    elif range_filter == "week":
        base_sql += " AND ratings.watched_at >= :since"
        params["since"] = datetime.now() - timedelta(weeks=1)

    result = db.session.execute(text(base_sql), params)
    # sql = "SELECT * FROM ratings WHERE genre_id = " + str(genre_id) 

    return [
        {
            "id": row.id,
            "score": row.score,
            "review": row.review,
            "watched_at": safe_iso(row.watched_at),
            "movie_title": row.movie_title,
        }
        for row in result
    ]


@app.route("/add-movie", methods=["POST"])
def add_movie():
    data = request.json
    tmdb_id = data.get("tmdb_id")
    genre_ids = data.get("genre_ids", [])

    existing = Movie.query.filter_by(tmdb_id=tmdb_id).first()
    if existing:
        return {"message": "Movie already exists in DB."}

    genres = Genre.query.filter(Genre.id.in_(genre_ids)).all()

    new_movie = Movie(
        tmdb_id=tmdb_id,
        title=data.get("title"),
        release_year=data.get("release_year"),
        poster_path=data.get("poster_path"),
        genres=genres
    )
    print(new_movie.genres)
    db.session.add(new_movie)
    db.session.commit()
    return {"message": "Movie added!"}

@app.route("/report-by-genre")
def report_by_genre():
    genre_id = request.args.get("genre_id")
    range_filter = request.args.get("range", "all")

    query = Rating.query \
        .join(Movie) \
        .join(movie_genres, movie_genres.c.movie_id == Movie.id) \
        .filter(movie_genres.c.genre_id == genre_id)

    if range_filter == "day":
        since = datetime.now() - timedelta(days=1)
        query = query.filter(Rating.watched_at >= since)
    elif range_filter == "week":
        since = datetime.now() - timedelta(weeks=1)
        query = query.filter(Rating.watched_at >= since)

    result = [
        {
            "id": r.id,
            "score": r.score,
            "review": r.review,
            "watched_at": r.watched_at.isoformat(),
            "movie_title": r.movie.title
        }
        for r in query.all()
    ]
    return result


#run the app
if __name__ == "__main__":
    app.run(debug=True)


