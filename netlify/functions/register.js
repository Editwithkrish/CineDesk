exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    const data = JSON.parse(event.body || '{}');
    // Demo validation
    if (!data.email || !data.password) {
      return { statusCode: 422, body: 'email and password are required' };
    }
    return {
      statusCode: 201,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ok: true, id: Math.floor(Math.random() * 10000) })
    };
  } catch (err) {
    return { statusCode: 400, body: 'Invalid JSON' };
  }
};