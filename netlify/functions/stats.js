const movies = [
  { movie_id: 1, title: 'The Matrix', genre: 'Sci-Fi', release_year: 1999 },
  { movie_id: 2, title: 'Inception', genre: 'Sci-Fi', release_year: 2010 },
  { movie_id: 3, title: 'Interstellar', genre: 'Sci-Fi', release_year: 2014 },
  { movie_id: 4, title: 'The Dark Knight', genre: 'Action', release_year: 2008 },
  { movie_id: 5, title: 'Parasite', genre: 'Thriller', release_year: 2019 }
];

exports.handler = async () => {
  const summary = {
    total_movies: movies.length,
    available_movies: movies.length, // demo: all available
    total_customers: 120,
    active_rentals: 7,
  };
  const payload = {
    status: 'success',
    server_time: new Date().toISOString(),
    summary,
    top_available: movies.slice(0, 5),
  };
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  };
};