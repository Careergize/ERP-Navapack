/** @param {Record<string, string | undefined>} env */
export function validateHostedDemoConfig(env) {
  if (env.VITE_HOSTED_DEMO !== undefined && !['true','false'].includes(env.VITE_HOSTED_DEMO))
    throw new Error('VITE_HOSTED_DEMO must be true or false.');
  if (env.VITE_HOSTED_DEMO !== 'true') return;
  let url;
  try { url = new URL(env.VITE_API_BASE_URL ?? ''); } catch { throw new Error('Hosted demo requires an absolute HTTPS API URL.'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.hostname.includes('*')
      || url.pathname.replace(/\/$/,'') !== '/api/v1' || env.VITE_ENABLE_MOCK_LOGIN !== 'false')
    throw new Error('Hosted demo requires an exact HTTPS /api/v1 backend and VITE_ENABLE_MOCK_LOGIN=false.');
}
