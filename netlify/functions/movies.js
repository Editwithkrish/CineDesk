exports.handler = async () => {
  // Demo movie list (mirrors seed data in Flask app)
  const movies = [
    { movie_id: 1, title: 'The Matrix', genre: 'Sci-Fi', release_year: 1999 },
    { movie_id: 2, title: 'Inception', genre: 'Sci-Fi', release_year: 2010 },
    { movie_id: 3, title: 'Interstellar', genre: 'Sci-Fi', release_year: 2014 },
    { movie_id: 4, title: 'The Dark Knight', genre: 'Action', release_year: 2008 },
    { movie_id: 5, title: 'Parasite', genre: 'Thriller', release_year: 2019 }
  ];
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ok: true, movies })
  };
};