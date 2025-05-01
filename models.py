from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

movie_genres = db.Table('movie_genres',
    db.Column('movie_id', db.Integer, db.ForeignKey('movies.id')),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'))
)

class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)  # TMDB genre ID
    name = db.Column(db.String(50), nullable=False)

class Movie(db.Model):
    __tablename__ = 'movies'
    id = db.Column(db.Integer, primary_key=True)  # internal ID
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    release_year = db.Column(db.Integer)
    poster_path = db.Column(db.String(300))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    genres = db.relationship('Genre', secondary=movie_genres, backref='movies')

    def serialize(self):
        return {
            "id": self.id,
            "tmdb_id": self.tmdb_id,
            "title": self.title,
            "release_year": self.release_year,
            "poster_path": self.poster_path,
            "added_at": self.added_at.isoformat(),
            "genres": [g.name for g in self.genres]
        }

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movies.id"))
    score = db.Column(db.Integer)
    review = db.Column(db.Text)
    watched_at = db.Column(db.DateTime, default=datetime.utcnow)

    movie = db.relationship("Movie", backref="ratings")





