// Injected by nginx in Docker — overrides localhost defaults in app.js.
// All paths are relative so nginx reverse-proxies them to the correct service.
window.SAKHA_CONFIG = {
  API:      '/api/v1',
  AUTH_API: '',
};
