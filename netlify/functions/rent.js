exports.handler = async (event) => {
  try {
    const payload = JSON.parse(event.body || '{}');
    if (!payload.movie_id || !payload.title) {
      return { statusCode: 400, body: JSON.stringify({ ok:false, error:'movie_id and title required' }) };
    }
    // Demo: pretend we recorded a rental. In a real setup we'd call the Flask API.
    const rentalId = Math.floor(Math.random() * 1_000_000);
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ok:true, rental_id: rentalId, message:`Rented '${payload.title}'` })
    };
  } catch (e) {
    return { statusCode: 500, body: JSON.stringify({ ok:false, error: e.message }) };
  }
};