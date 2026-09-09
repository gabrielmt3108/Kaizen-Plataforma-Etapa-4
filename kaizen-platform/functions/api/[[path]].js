function jsonError(message, status) {
  return new Response(JSON.stringify({ detail: message }), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store'
    }
  });
}

export async function onRequest(context) {
  const configuredOrigin = String(context.env.KAIZEN_BACKEND_ORIGIN || '').replace(/\/$/, '');
  if (!configuredOrigin) {
    return jsonError('A origem do backend ainda não foi configurada.', 503);
  }

  let backendOrigin;
  try {
    backendOrigin = new URL(configuredOrigin);
  } catch (error) {
    return jsonError('A origem do backend é inválida.', 503);
  }

  if (backendOrigin.protocol !== 'https:') {
    return jsonError('O backend precisa usar HTTPS.', 503);
  }

  const incomingUrl = new URL(context.request.url);
  if (backendOrigin.origin === incomingUrl.origin) {
    return jsonError('A origem do backend não pode apontar para o próprio site.', 503);
  }

  const targetUrl = new URL(incomingUrl.pathname + incomingUrl.search, backendOrigin);
  const headers = new Headers(context.request.headers);
  headers.delete('host');
  headers.set('x-forwarded-host', incomingUrl.host);
  headers.set('x-forwarded-proto', 'https');

  const requestOptions = {
    method: context.request.method,
    headers,
    redirect: 'manual'
  };
  if (!['GET', 'HEAD'].includes(context.request.method)) {
    requestOptions.body = context.request.body;
  }

  return fetch(targetUrl, requestOptions);
}
