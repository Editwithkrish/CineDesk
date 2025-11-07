exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    const data = JSON.parse(event.body || '{}');
    const { email } = data;
    // Demo auth: accept any email/password, return a fake token
    const token = 'demo-token-' + Math.random().toString(36).slice(2);
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ok: true, token, user: { email } })
    };
  } catch (err) {
    return { statusCode: 400, body: 'Invalid JSON' };
  }
};