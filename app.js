/**
 * SAKHA — app.js
 * Auth-gated e-commerce SPA.
 * Shows sign-in / sign-up screen on load; reveals storefront after auth.
 */

/* ── Config ──────────────────────────────────────────────── */
// In Docker, nginx serves /config.js which sets window.SAKHA_CONFIG with
// relative paths so all traffic flows through the nginx reverse proxy.
// In local dev (no Docker), the fallback localhost URLs are used instead.
const _rc = window.SAKHA_CONFIG || {};
const CONFIG = {
  API:       _rc.API       ?? 'http://localhost:8080/api/v1',
  AUTH_API:  _rc.AUTH_API  ?? 'http://localhost:8001',
  LOW_STOCK: 10,
  PER_PAGE:  12,
};

/* ── Category display helpers ────────────────────────────── */
const CAT_GRAD = {
  audio:         'linear-gradient(135deg, oklch(35% 0.28 290), oklch(45% 0.26 320))',
  electronics:   'linear-gradient(135deg, oklch(30% 0.28 240), oklch(40% 0.25 200))',
  wearables:     'linear-gradient(135deg, oklch(32% 0.24 175), oklch(42% 0.22 145))',
  cameras:       'linear-gradient(135deg, oklch(35% 0.22 50),  oklch(45% 0.20 30))',
  'home-office': 'linear-gradient(135deg, oklch(28% 0.20 250), oklch(38% 0.18 230))',
  default:       'linear-gradient(135deg, oklch(28% 0.22 270), oklch(38% 0.20 250))',
};
const CAT_EMOJI = {
  audio: '🎧', electronics: '💻', wearables: '⌚',
  cameras: '📷', 'home-office': '🏠', default: '📦',
};

/* ── ID lookup maps (filled at init) ─────────────────────── */
const CATS = {};    // id → { name, slug }
const BRANDS = {};  // id → { name, slug }

/* ================================================================
   TOKEN STORE
   ================================================================ */
const TokenStore = {
  access: null,
  set(access, refresh) {
    this.access = access;
    if (refresh) localStorage.setItem('sakha_refresh', refresh);
  },
  getRefresh() { return localStorage.getItem('sakha_refresh'); },
  clear() { this.access = null; localStorage.removeItem('sakha_refresh'); },
};

/* ================================================================
   AUTH API HELPER  (points at the surreal-auth-api microservice)
   ================================================================ */
const authApi = {
  async post(path, body) {
    try {
      const r = await fetch(`${CONFIG.AUTH_API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (r.status === 204) return {};
      const d = await r.json().catch(() => null);
      if (!r.ok) return { _err: r.status, _msg: d?.detail ?? null };
      return d;
    } catch { return null; }
  },
  async get(path, token = null) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
      const r = await fetch(`${CONFIG.AUTH_API}${path}`, { method: 'GET', headers });
      if (r.status === 204) return {};
      const d = await r.json().catch(() => null);
      return r.ok ? d : null;
    } catch { return null; }
  },
};

/* ================================================================
   API HELPER
   ================================================================ */
const api = {
  async req(path, opts = {}, auth = true) {
    const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
    if (auth && TokenStore.access) headers['Authorization'] = `Bearer ${TokenStore.access}`;

    let res;
    try { res = await fetch(`${CONFIG.API}${path}`, { ...opts, headers }); }
    catch { return null; }

    if (res.status === 401 && auth) {
      const ok = await Auth.refresh().catch(() => false);
      if (ok) {
        headers['Authorization'] = `Bearer ${TokenStore.access}`;
        try { res = await fetch(`${CONFIG.API}${path}`, { ...opts, headers }); }
        catch { return null; }
      } else {
        Auth.logout();
        return null;
      }
    }
    return api._parse(res);
  },

  async _parse(res) {
    if (!res) return null;
    if (res.status === 204) return {};
    try {
      const d = await res.json();
      return res.ok ? d : null;
    } catch { return null; }
  },

  get(path, params, auth = true) {
    const url = params ? `${path}?${new URLSearchParams(params)}` : path;
    return this.req(url, { method: 'GET' }, auth);
  },
  post(path, body, auth = true) {
    return this.req(path, { method: 'POST', body: JSON.stringify(body) }, auth);
  },
  patch(path, body, auth = true) {
    return this.req(path, { method: 'PATCH', body: JSON.stringify(body) }, auth);
  },
  del(path, auth = true) {
    return this.req(path, { method: 'DELETE' }, auth);
  },
};

/* ================================================================
   AUTH
   ================================================================ */
const Auth = {
  user: null,
  mode: 'login',   // 'login' | 'register'

  async tryRestoreSession() {
    const refresh = TokenStore.getRefresh();
    if (!refresh) return false;
    return this.refresh();
  },

  async refresh() {
    const refresh = TokenStore.getRefresh();
    if (!refresh) return false;
    const data = await authApi.post('/auth/refresh', { refresh_token: refresh });
    if (data?.access_token) {
      TokenStore.set(data.access_token, data.refresh_token);
      return true;
    }
    TokenStore.clear();
    return false;
  },

  async login(email, password) {
    const data = await authApi.post('/auth/login', { email, password });
    if (data?.access_token) {
      TokenStore.set(data.access_token, data.refresh_token);
      this.user = { email };
      await this._fetchMe();
      return { ok: true };
    }
    if (data?._err === 403) return { ok: false, unverified: true };
    return { ok: false };
  },

  async register(name, email, password) {
    const data = await authApi.post('/auth/signup', { name, email, password });
    // signup returns the created user (or array); no access_token yet — email verification required
    if (data && (Array.isArray(data) ? data.length > 0 : data.id || data.email)) {
      return true;
    }
    return false;
  },

  async _fetchMe() {
    const me = await authApi.get('/auth/me', TokenStore.access);
    if (me) this.user = me;
  },

  async verifyEmail(code) {
    const data = await authApi.get(`/auth/verify-email?code=${encodeURIComponent(code)}`);
    return !!data?.verified;
  },

  async requestPasswordReset(email) {
    const data = await authApi.post('/auth/reset-password/request', { email });
    return !!data;
  },

  async resetPassword(code, password, confirmPass) {
    const data = await authApi.post('/auth/reset-password/confirm', { code, password, confirmPass });
    return data?.success;
  },

  logout() {
    const refresh = TokenStore.getRefresh();
    if (refresh) {
      authApi.post('/auth/logout', { refresh_token: refresh }).catch(() => null);
    }
    TokenStore.clear();
    this.user = null;
    Cart.reset();
    showAuthScreen();
  },

  isLoggedIn() { return !!TokenStore.access; },

  setMode(mode) {
    this.mode = mode;
    const isReg = mode === 'register';
    $('auth-heading').textContent = isReg ? 'Create account' : 'Welcome back';
    $('auth-sub').textContent     = isReg ? 'Sign up to start shopping' : 'Sign in to your account to continue';
    $('auth-submit-btn').textContent = isReg ? 'Create account' : 'Sign in';
    $('auth-mode-label').textContent = isReg ? 'Already have an account?' : "Don't have an account?";
    $('auth-toggle-link').textContent = isReg ? 'Sign in' : 'Create one';
    $('name-group').classList.toggle('hidden', !isReg);
    const passInput = $('f-password');
    if (passInput) passInput.autocomplete = isReg ? 'new-password' : 'current-password';
    hideAuthError();
  },
};

/* ================================================================
   SCREEN SWITCHING
   ================================================================ */
function showAuthScreen() {
  $('auth-screen').classList.remove('hidden');
  $('app-screen').classList.add('hidden');
}

async function showAppScreen() {
  $('auth-screen').classList.add('hidden');
  $('app-screen').classList.remove('hidden');
  updateAuthArea();
  await Cart.init();
  await Promise.all([
    api.get('/categories', null, false).then(d => {
      toArray(d).forEach(c => { CATS[c.id] = { name: c.name, slug: slug(c.name) }; });
    }).catch(() => {}),
    api.get('/brands/', null, false).then(d => {
      toArray(d).forEach(b => { BRANDS[b.id] = { name: b.name, slug: slug(b.name) }; });
    }).catch(() => {}),
  ]);
  await Promise.all([loadHeroCard(), loadCategories(), loadTrending(), loadFeatured()]);
  Shop.loadBrands();
}

/* ================================================================
   CART
   ================================================================ */
const Cart = {
  cartId: localStorage.getItem('sakha_cart_id') || null,
  items: [],
  discount: 0,

  reset() {
    this.cartId = null;
    this.items = [];
    this.discount = 0;
    localStorage.removeItem('sakha_cart_id');
    this._render();
  },

  async init() {
    if (this.cartId) await this.load();
  },

  async load() {
    if (!this.cartId) return;
    const d = await api.get(`/cart/${this.cartId}`, null, false);
    if (d) { this.items = d.items || []; this._render(); }
  },

  async add(productId, variantId = null, qty = 1) {
    if (!this.cartId) {
      const cart = await api.post('/cart/', {}, false);
      if (!cart?.id) { Toast.show('Could not create cart', 'error'); return false; }
      this.cartId = cart.id;
      localStorage.setItem('sakha_cart_id', this.cartId);
    }
    const body = { product_id: productId, quantity: qty };
    if (variantId) body.variant_id = variantId;
    const d = await api.post(`/cart/${this.cartId}/items`, body, false);
    if (d) {
      await this.load();
      UI.openCart();
      Toast.show('Added to cart', 'success');
      return true;
    }
    Toast.show('Failed to add item', 'error');
    return false;
  },

  async remove(itemId) {
    if (!this.cartId) return;
    await api.del(`/cart/${this.cartId}/items/${itemId}`, false);
    await this.load();
  },

  async updateQty(itemId, qty) {
    if (!this.cartId || qty < 1) return;
    await api.patch(`/cart/${this.cartId}/items/${itemId}`, { quantity: qty }, false);
    await this.load();
  },

  async applyCoupon(code) {
    const d = await api.post('/coupons/validate', { code }, false);
    if (d?.valid) {
      this.discount = d.discount || 0;
      this._render();
      return { ok: true, discount: d.discount };
    }
    return { ok: false };
  },

  subtotal() { return this.items.reduce((s, i) => s + (i.unit_price || 0) * (i.quantity || 1), 0); },
  total()    { return Math.max(0, this.subtotal() - this.discount); },
  count()    { return this.items.reduce((s, i) => s + (i.quantity || 1), 0); },

  _render() {
    const cnt = this.count();
    const badge = $('cart-badge');
    if (badge) { badge.textContent = cnt; badge.style.display = cnt > 0 ? 'flex' : 'none'; }

    const wrap   = $('cart-items');
    const footer = $('cart-footer');
    if (!wrap) return;

    if (!this.items.length) {
      wrap.innerHTML = `<div class="empty-state"><div class="empty-icon">🛒</div><p>Your cart is empty.</p></div>`;
      if (footer) footer.style.display = 'none';
      return;
    }

    wrap.innerHTML = this.items.map(item => {
      const price = item.unit_price || 0;
      const qty   = item.quantity || 1;
      const name  = item.name || 'Product';
      const grad  = CAT_GRAD.default;
      return `
        <div class="cart-item">
          <div class="cart-item-thumb" style="background:${grad}">📦</div>
          <div class="cart-item-info">
            <p class="cart-item-name">${esc(name)}</p>
            <p class="cart-item-price">${fmt(price)}</p>
            <div class="cart-item-controls">
              <button class="qty-btn" data-dec="${item.id}">−</button>
              <span class="qty-val">${qty}</span>
              <button class="qty-btn" data-inc="${item.id}" data-qty="${qty}">+</button>
            </div>
          </div>
          <button class="cart-item-remove" data-remove="${item.id}">✕</button>
        </div>`;
    }).join('');

    if (footer) footer.style.display = 'flex';
    setText('cart-subtotal', fmt(this.subtotal()));
    setText('cart-total', fmt(this.total()));
    const dr = $('discount-row');
    if (dr) dr.style.display = this.discount > 0 ? 'flex' : 'none';
    if (this.discount > 0) setText('cart-discount', `-${fmt(this.discount)}`);
  },
};

/* ================================================================
   WISHLIST
   ================================================================ */
const Wishlist = {
  ids: new Set(JSON.parse(localStorage.getItem('sakha_wishlist') || '[]')),

  toggle(id) {
    id = String(id);
    if (this.ids.has(id)) { this.ids.delete(id); Toast.show('Removed from wishlist', 'success'); }
    else                  { this.ids.add(id);    Toast.show('Added to wishlist ♡', 'success'); }
    localStorage.setItem('sakha_wishlist', JSON.stringify([...this.ids]));
    this._badge();
    return this.ids.has(id);
  },
  has(id) { return this.ids.has(String(id)); },
  _badge() {
    const b = $('wishlist-badge');
    if (!b) return;
    b.textContent = this.ids.size;
    b.style.display = this.ids.size > 0 ? 'flex' : 'none';
  },
  async renderView() {
    const grid  = $('wishlist-grid');
    const empty = $('wishlist-empty');
    if (!grid) return;
    const ids = [...this.ids];
    if (!ids.length) { grid.innerHTML = ''; empty?.classList.remove('hidden'); return; }
    empty?.classList.add('hidden');
    grid.innerHTML = ids.map(() => `<div class="skeleton product-skeleton"></div>`).join('');
    const products = await Promise.all(ids.map(id => api.get(`/products/${id}`, null, false).catch(() => null)));
    grid.innerHTML = '';
    products.filter(Boolean).forEach((p, i) => grid.appendChild(productCard(p, i)));
    if (!grid.children.length) empty?.classList.remove('hidden');
  },
};

/* ================================================================
   TOAST
   ================================================================ */
const Toast = {
  show(msg, type = 'info', ms = 3000) {
    const c = $('toast-container');
    if (!c) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    t.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ'}</span><span>${esc(msg)}</span>`;
    c.appendChild(t);
    setTimeout(() => {
      t.style.cssText += 'opacity:0;transform:translateX(40px);transition:all 0.3s ease';
      setTimeout(() => t.remove(), 320);
    }, ms);
  },
};

/* ================================================================
   UI
   ================================================================ */
const UI = {
  view: 'home',
  showView(id) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    $(`view-${id}`)?.classList.remove('hidden');
    this.view = id;
    document.querySelectorAll('.nav-link').forEach(a => a.classList.toggle('active', a.dataset.view === id));
    if (id === 'wishlist') Wishlist.renderView();
    if (id === 'shop') { Shop.page = 1; Shop.load(); }
  },
  openCart()  {
    $('cart-drawer')?.classList.add('open');
    $('cart-overlay')?.classList.add('open');
    document.body.style.overflow = 'hidden';
  },
  closeCart() {
    $('cart-drawer')?.classList.remove('open');
    $('cart-overlay')?.classList.remove('open');
    document.body.style.overflow = '';
  },
};

function updateAuthArea() {
  const area = $('auth-area');
  if (!area) return;
  const u = Auth.user;
  const name = u?.name || u?.email || 'Account';
  const initial = name[0].toUpperCase();
  area.innerHTML = `
    <div style="position:relative">
      <button class="account-btn" id="acct-btn">
        <span class="avatar-circle">${esc(initial)}</span>
        <span>${esc(name.split(' ')[0])}</span>
        <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
      </button>
      <div class="account-dropdown" id="acct-dropdown">
        <div class="dropdown-item" data-view="orders">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20 7H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/><polyline points="16 3 12 7 8 3"/></svg>
          My Orders
        </div>
        <div class="dropdown-item" data-view="wishlist">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          Wishlist
        </div>
        <div class="dropdown-sep"></div>
        <div class="dropdown-item danger" id="sign-out-btn">
          <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          Sign Out
        </div>
      </div>
    </div>`;
  $('acct-btn')?.addEventListener('click', () => $('acct-dropdown')?.classList.toggle('open'));
  $('sign-out-btn')?.addEventListener('click', () => Auth.logout());
}

/* ================================================================
   PRODUCT CARD
   ================================================================ */
function productCard(p, idx = 0) {
  const card = document.createElement('div');
  card.className = 'product-card';
  card.style.setProperty('--i', idx);

  const catSlug  = (CATS[p.category_id] || {}).slug || slug(p.category || '');
  const grad     = CAT_GRAD[catSlug] || CAT_GRAD.default;
  const emoji    = CAT_EMOJI[catSlug] || '📦';
  const brand    = (BRANDS[p.brand_id] || {}).name || '';
  const price    = p.price || 0;
  const original = p.compare_at_price;
  const stock    = p.stock ?? null;
  const inWish   = Wishlist.has(p.id);
  const rating   = p.average_rating;
  const reviews  = p.review_count || 0;

  let stockBadge = '';
  if (stock === 0) stockBadge = `<span class="stock-badge out">Out of Stock</span>`;
  else if (stock !== null && stock <= CONFIG.LOW_STOCK) stockBadge = `<span class="stock-badge low">Low Stock</span>`;

  card.innerHTML = `
    <div class="card-thumb" style="background:${grad}">
      <span>${emoji}</span>
      ${stockBadge}
      <button class="card-wishlist${inWish ? ' active' : ''}" data-pid="${p.id}">
        <svg width="16" height="16" fill="${inWish ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
      </button>
    </div>
    <div class="card-body">
      <p class="card-brand">${esc(brand)}</p>
      <p class="card-name">${esc(p.name)}</p>
      ${rating ? `<div class="card-rating"><span class="stars">${stars(rating)}</span><span class="rating-count">(${reviews})</span></div>` : ''}
      <div class="card-footer">
        <span class="card-price">${fmt(price)}${original && original > price ? `<span class="original">${fmt(original)}</span>` : ''}</span>
        <button class="card-add-btn" data-pid="${p.id}" ${stock === 0 ? 'disabled' : ''}>${stock === 0 ? 'Sold Out' : 'Add to Cart'}</button>
      </div>
    </div>`;

  card.addEventListener('click', e => {
    if (e.target.closest('.card-wishlist, .card-add-btn')) return;
    openProductModal(p.id);
  });
  card.querySelector('.card-wishlist')?.addEventListener('click', e => {
    e.stopPropagation();
    const btn = e.currentTarget;
    const on = Wishlist.toggle(p.id);
    btn.classList.toggle('active', on);
    btn.querySelector('svg')?.setAttribute('fill', on ? 'currentColor' : 'none');
  });
  card.querySelector('.card-add-btn')?.addEventListener('click', e => {
    e.stopPropagation();
    if (stock === 0) return;
    Cart.add(p.id);
  });
  return card;
}

/* ================================================================
   HOME CONTENT LOADERS
   ================================================================ */
async function loadHeroCard() {
  const c = $('hero-featured-card');
  if (!c) return;
  const d = await api.get('/products/', { page: 1, limit: 1 }, false);
  const items = toArray(d);
  if (!items.length) return;
  const p = items[0];
  const catSlug = (CATS[p.category_id] || {}).slug || slug(p.category || '');
  const grad  = CAT_GRAD[catSlug] || CAT_GRAD.default;
  const emoji = CAT_EMOJI[catSlug] || '📦';
  const brand = (BRANDS[p.brand_id] || {}).name || 'Featured';
  c.innerHTML = `
    <div style="background:${grad};border-radius:20px;border:1px solid oklch(60% 0.26 240/0.25);padding:28px;display:flex;flex-direction:column;gap:16px">
      <div style="font-size:64px;text-align:center;padding:20px 0">${emoji}</div>
      <div>
        <p style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:oklch(60% 0.26 240);margin-bottom:6px">${esc(brand)}</p>
        <p style="font-size:18px;font-weight:600;color:oklch(95% 0.006 240);line-height:1.3;margin-bottom:10px">${esc(p.name)}</p>
        <p style="font-size:24px;font-weight:700;color:oklch(78% 0.20 72)">${fmt(p.price || 0)}</p>
      </div>
      <button class="btn btn-primary" data-pid="${p.id}" style="align-self:flex-start">View Product</button>
    </div>`;
  c.querySelector('[data-pid]')?.addEventListener('click', () => openProductModal(p.id));
}

async function loadCategories() {
  const row  = $('category-row');
  const list = $('filter-categories');
  if (!row) return;
  const d = await api.get('/categories', null, false);
  const cats = toArray(d);
  if (!cats.length) { row.innerHTML = '<p style="color:var(--text-3);font-size:14px">No categories found.</p>'; return; }

  row.innerHTML = cats.map(c => {
    const s = slug(c.name);
    return `<div class="category-chip" data-cat-id="${esc(c.id)}" data-cat="${esc(s)}">
      <div class="cat-thumb" style="background:${CAT_GRAD[s] || CAT_GRAD.default}">${CAT_EMOJI[s] || '📦'}</div>
      <div class="cat-name">${esc(c.name)}</div>
    </div>`;
  }).join('');

  if (list) {
    list.innerHTML = `<div class="filter-item active" data-filter-cat="" data-filter-cat-id=""><span class="filter-check"></span><span>All</span></div>`
      + cats.map(c => {
          const s = slug(c.name);
          return `<div class="filter-item" data-filter-cat="${esc(s)}" data-filter-cat-id="${esc(c.id)}"><span class="filter-check"></span><span>${esc(c.name)}</span></div>`;
        }).join('');
  }

  row.querySelectorAll('.category-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      Shop.filters.category    = chip.dataset.cat;
      Shop.filters.category_id = chip.dataset.catId;
      Shop.page = 1;
      UI.showView('shop');
    });
  });
}

async function loadTrending() {
  const el = $('trending-strip');
  if (!el) return;
  const d = await api.get('/products/', { page: 1, limit: 6 }, false);
  const items = toArray(d);
  if (!items.length) { el.innerHTML = '<p style="color:var(--text-3);font-size:14px;padding:20px">No products found.</p>'; return; }
  el.innerHTML = '';
  items.forEach((p, i) => el.appendChild(productCard(p, i)));
}

async function loadFeatured() {
  const el = $('featured-grid');
  if (!el) return;
  const d = await api.get('/products/', { page: 1, limit: 8 }, false);
  const items = toArray(d);
  if (!items.length) { el.innerHTML = '<p style="color:var(--text-3);font-size:14px;padding:20px;grid-column:1/-1">No products found.</p>'; return; }
  el.innerHTML = '';
  items.forEach((p, i) => el.appendChild(productCard(p, i)));
}

/* ================================================================
   SHOP VIEW
   ================================================================ */
const Shop = {
  filters: { category: '', category_id: '', brand: '', brand_id: '', minPrice: '', maxPrice: '', inStock: false, sort: '' },
  page: 1, totalPages: 1, loading: false,

  async load() {
    if (this.loading) return;
    this.loading = true;
    const grid = $('shop-grid');
    if (!grid) { this.loading = false; return; }
    grid.innerHTML = Array(6).fill(`<div class="skeleton product-skeleton"></div>`).join('');

    try {
      const params = { page: this.page, limit: CONFIG.PER_PAGE };
      if (this.filters.category_id) params.category_id = this.filters.category_id;
      if (this.filters.brand_id)    params.brand_id    = this.filters.brand_id;
      if (this.filters.minPrice)  params.min_price   = this.filters.minPrice;
      if (this.filters.maxPrice)  params.max_price   = this.filters.maxPrice;
      if (this.filters.inStock)   params.in_stock    = true;
      if (this.filters.sort)      params.sort        = this.filters.sort;

      const d = await api.get('/products/', params, false);
      const items = toArray(d);
      const total = d?.total ?? items.length;
      this.totalPages = Math.ceil(total / CONFIG.PER_PAGE) || 1;

      const cEl = $('result-count');
      if (cEl) cEl.textContent = `${total.toLocaleString()} product${total !== 1 ? 's' : ''} found`;

      grid.innerHTML = '';
      if (!items.length) {
        grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🔍</div><p>No products match your filters.</p></div>`;
      } else {
        items.forEach((p, i) => grid.appendChild(productCard(p, i)));
      }
      this._pages();
      this._syncUI();
    } finally { this.loading = false; }
  },

  _pages() {
    const pg = $('shop-pagination');
    if (!pg) return;
    pg.innerHTML = '';
    if (this.totalPages <= 1) return;
    const prev = el('button', 'page-btn', '←');
    prev.disabled = this.page === 1;
    prev.addEventListener('click', () => { this.page--; this.load(); });
    pg.appendChild(prev);
    const start = Math.max(1, this.page - 3);
    const end   = Math.min(this.totalPages, start + 6);
    for (let i = start; i <= end; i++) {
      const b = el('button', `page-btn${i === this.page ? ' active' : ''}`, i);
      const p = i;
      b.addEventListener('click', () => { this.page = p; this.load(); });
      pg.appendChild(b);
    }
    const next = el('button', 'page-btn', '→');
    next.disabled = this.page === this.totalPages;
    next.addEventListener('click', () => { this.page++; this.load(); });
    pg.appendChild(next);
  },

  _syncUI() {
    document.querySelectorAll('[data-filter-cat]').forEach(e => e.classList.toggle('active', e.dataset.filterCatId === this.filters.category_id));
    document.querySelectorAll('[data-filter-brand]').forEach(e => e.classList.toggle('active', e.dataset.filterBrandId === this.filters.brand_id));
    const t = $('in-stock-toggle'); if (t) t.checked = this.filters.inStock;
    const s = $('sort-select');     if (s) s.value   = this.filters.sort;
    const mn = $('price-min');      if (mn) mn.value  = this.filters.minPrice;
    const mx = $('price-max');      if (mx) mx.value  = this.filters.maxPrice;
  },

  async loadBrands() {
    const list = $('filter-brands');
    if (!list) return;
    const d = await api.get('/brands/', null, false);
    const brands = toArray(d);
    if (!brands.length) { list.innerHTML = '<p style="font-size:13px;color:var(--text-3)">No brands found.</p>'; return; }
    list.innerHTML = `<div class="filter-item active" data-filter-brand="" data-filter-brand-id=""><span class="filter-check"></span><span>All Brands</span></div>`
      + brands.map(b => {
          const name = b.name || b;
          const id   = b.id || '';
          return `<div class="filter-item" data-filter-brand="${esc(name)}" data-filter-brand-id="${esc(id)}"><span class="filter-check"></span><span>${esc(name)}</span></div>`;
        }).join('');
  },
};

/* ================================================================
   PRODUCT MODAL
   ================================================================ */
let modalPid = null;

async function openProductModal(pid) {
  modalPid = pid;
  const overlay = $('product-modal-overlay');
  if (!overlay) return;
  overlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';

  const p = await api.get(`/products/${pid}`, null, false);
  if (!p) { closeProductModal(); Toast.show('Could not load product', 'error'); return; }

  const catSlug = (CATS[p.category_id] || {}).slug || slug(p.category || '');
  const grad    = CAT_GRAD[catSlug] || CAT_GRAD.default;
  const emoji   = CAT_EMOJI[catSlug] || '📦';
  const brand   = (BRANDS[p.brand_id] || {}).name || '';

  const thumb = $('modal-thumb');
  if (thumb) { thumb.style.background = grad; thumb.innerHTML = `<span style="font-size:80px">${emoji}</span>`; }

  setText('modal-brand', brand);
  setText('modal-name',  p.name || '');
  setText('modal-sku',   p.sku ? `SKU: ${p.sku}` : '');
  setText('modal-price', fmt(p.price || 0));
  setText('modal-desc',  p.description || '');

  const wBtn = $('modal-wishlist-btn');
  if (wBtn) {
    wBtn.dataset.pid = pid;
    const on = Wishlist.has(pid);
    wBtn.classList.toggle('active', on);
    wBtn.querySelector('svg')?.setAttribute('fill', on ? 'currentColor' : 'none');
  }

  const addBtn = $('modal-add-cart');
  if (addBtn) {
    addBtn.dataset.pid = pid;
    addBtn.disabled = p.stock === 0;
    addBtn.textContent = p.stock === 0 ? 'Out of Stock' : 'Add to Cart';
  }

  const [variants, rating, reviews, questions] = await Promise.all([
    api.get(`/products/${pid}/variants`, null, false).catch(() => null),
    api.get(`/products/${pid}/rating-summary`, null, false).catch(() => null),
    api.get(`/products/${pid}/reviews`, null, false).catch(() => null),
    api.get(`/products/${pid}/questions`, null, false).catch(() => null),
  ]);

  renderVariants(variants);
  renderRating(rating);
  renderReviews(reviews, rating);
  renderQA(questions);
  setTab('reviews');
}

function closeProductModal() {
  $('product-modal-overlay')?.classList.add('hidden');
  modalPid = null;
  if (!document.querySelector('.modal-overlay:not(.hidden)')) document.body.style.overflow = '';
}

function renderVariants(data) {
  const c = $('modal-variants');
  if (!c) return;
  const list = toArray(data);
  if (!list.length) { c.innerHTML = ''; return; }
  const groups = {};
  list.forEach(v => { const k = v.attribute || 'Variant'; (groups[k] = groups[k] || []).push(v); });
  c.innerHTML = Object.entries(groups).map(([k, vals]) => `
    <div class="variant-group">
      <p class="variant-group-label">${esc(k)}</p>
      <div class="variant-chips">
        ${vals.map(v => `<button class="variant-chip" data-vid="${v.id}" ${v.stock === 0 ? 'disabled style="opacity:0.4"' : ''}>${esc(v.value || v.name || v.id)}</button>`).join('')}
      </div>
    </div>`).join('');
  c.querySelector('.variant-chip')?.classList.add('selected');
  c.addEventListener('click', e => {
    const chip = e.target.closest('.variant-chip');
    if (!chip || chip.disabled) return;
    chip.closest('.variant-chips')?.querySelectorAll('.variant-chip').forEach(ch => ch.classList.remove('selected'));
    chip.classList.add('selected');
  });
}

function renderRating(r) {
  const el = $('modal-rating');
  if (!el) return;
  el.innerHTML = r?.average ? `<span class="stars" style="font-size:16px">${stars(r.average)}</span><span style="color:var(--text-2);font-size:14px">${r.average.toFixed(1)} (${r.total || 0} reviews)</span>` : '';
}

function renderReviews(data, r) {
  const panel = $('tab-reviews');
  if (!panel) return;
  const list = toArray(data);
  let html = '';
  if (r?.average) {
    html = `<div class="rating-summary"><span class="rating-big">${r.average.toFixed(1)}</span><div class="rating-info"><span class="stars" style="font-size:20px">${stars(r.average)}</span><span style="color:var(--text-2);font-size:13px">${r.total || 0} reviews</span></div></div>`;
  }
  if (!list.length) { panel.innerHTML = html + `<p style="color:var(--text-3);font-size:14px">No reviews yet.</p>`; return; }
  panel.innerHTML = html + list.map(r => `
    <div class="review-item">
      <div class="review-header">
        <span class="reviewer-name">${esc(r.user_name || 'Anonymous')}</span>
        <span class="stars">${stars(r.rating || 5)}</span>
        <span class="review-date">${r.created_at ? new Date(r.created_at).toLocaleDateString() : ''}</span>
      </div>
      <p class="review-body">${esc(r.body || r.comment || '')}</p>
    </div>`).join('');
}

function renderQA(data) {
  const panel = $('tab-qa');
  if (!panel) return;
  const list = toArray(data);
  if (!list.length) { panel.innerHTML = `<p style="color:var(--text-3);font-size:14px">No questions yet.</p>`; return; }
  panel.innerHTML = list.map(q => `
    <div class="qa-item">
      <p class="qa-question">Q: ${esc(q.question || q.body || '')}</p>
      ${q.answer ? `<p class="qa-answer">A: ${esc(q.answer)}</p>` : ''}
    </div>`).join('');
}

function setTab(name) {
  document.querySelectorAll('.modal-tabs .tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  const r = $('tab-reviews');
  const q = $('tab-qa');
  if (r) { r.classList.toggle('active', name === 'reviews'); r.classList.toggle('hidden', name !== 'reviews'); }
  if (q) { q.classList.toggle('active', name === 'qa');      q.classList.toggle('hidden', name !== 'qa'); }
}

/* ================================================================
   SEARCH
   ================================================================ */
let searchTimer;
async function handleSearch(q) {
  const box = $('search-suggestions');
  if (!box) return;
  if (!q.trim()) { box.classList.remove('open'); box.innerHTML = ''; return; }
  const d = await api.get('/products/suggestions', { q, limit: 6 }, false);
  const items = toArray(d);
  if (!items.length) { box.classList.remove('open'); return; }
  box.innerHTML = items.map(i => {
    const name = typeof i === 'string' ? i : (i.name || '');
    return `<div class="suggestion-item" data-name="${esc(name)}">${esc(name)}</div>`;
  }).join('');
  box.classList.add('open');
}

/* ================================================================
   AUTH SCREEN EVENTS
   ================================================================ */
function showAuthError(msg) {
  const el = $('auth-error');
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
}
function hideAuthError() {
  $('auth-error')?.classList.add('hidden');
}

function setupAuthScreen() {
  $('auth-toggle-link')?.addEventListener('click', e => {
    e.preventDefault();
    Auth.setMode(Auth.mode === 'login' ? 'register' : 'login');
  });

  // Toggle Forgot Password
  $('forgot-pass-link')?.addEventListener('click', e => {
    e.preventDefault();
    $('login-view')?.classList.add('hidden');
    $('forgot-view')?.classList.remove('hidden');
  });

  $('back-to-login-link')?.addEventListener('click', e => {
    e.preventDefault();
    $('forgot-view')?.classList.add('hidden');
    $('login-view')?.classList.remove('hidden');
  });

  // Forgot Password Form
  $('forgot-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = $('forgot-submit-btn');
    const email = $('forgot-email')?.value.trim();
    if (!email) return;
    
    btn.disabled = true;
    btn.textContent = 'Sending...';
    await Auth.requestPasswordReset(email);
    
    Toast.show('If your email exists, a password reset link has been sent.', 'info', 6000);
    btn.textContent = 'Link Sent!';
    setTimeout(() => {
       $('forgot-view')?.classList.add('hidden');
       $('login-view')?.classList.remove('hidden');
       btn.disabled = false;
       btn.textContent = 'Send Reset Link';
    }, 2000);
  });

  // Reset Password Form
  $('reset-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = $('reset-submit-btn');
    const pass = $('reset-pass')?.value;
    const confirm = $('reset-confirm')?.value;
    const err = $('reset-error');
    
    if (!pass || pass !== confirm) {
        if(err) { err.textContent = 'Passwords do not match'; err.classList.remove('hidden'); }
        return;
    }
    
    // Grab code from the URL, or from the dataset fallback we added on page load
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code') || $('reset-form').dataset.code;
    
    if (!code) {
        if(err) { err.textContent = 'Missing reset code.'; err.classList.remove('hidden'); }
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Updating...';
    
    const ok = await Auth.resetPassword(code, pass, confirm);
    if (ok) {
       Toast.show('Password updated successfully! Please log in.', 'success', 5000);
       window.history.replaceState({}, document.title, window.location.pathname);
       $('reset-view')?.classList.add('hidden');
       $('login-view')?.classList.remove('hidden');
    } else {
       if(err) { err.textContent = 'Invalid or expired reset link.'; err.classList.remove('hidden'); }
       btn.disabled = false;
       btn.textContent = 'Update Password';
    }
  });

  $('auth-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    hideAuthError();
    const btn   = $('auth-submit-btn');
    const email = $('f-email')?.value.trim();
    const pass  = $('f-password')?.value;
    const name  = $('f-name')?.value.trim();
    btn.disabled = true;
    btn.textContent = Auth.mode === 'login' ? 'Signing in…' : 'Creating account…';

    let ok = false;
    let isRegister = Auth.mode === 'register';

    if (!isRegister) {
      ok = await Auth.login(email, pass);
      if (!ok.ok) {
        if (ok.unverified) {
          showAuthError('Your email hasn\'t been verified yet. Please check your inbox for the verification link.');
        } else {
          showAuthError('Invalid email or password. Please try again.');
        }
      }
    } else {
      if (!name) { showAuthError('Please enter your full name.'); btn.disabled = false; btn.textContent = 'Create account'; return; }
      ok = await Auth.register(name, email, pass);
      if (!ok) {
        showAuthError('Registration failed. The email may already be in use.');
      } else {
        // Show success message and switch to login mode
        btn.disabled = false;
        btn.textContent = 'Create account';
        
        Toast.show('Success! Please check your email for a verification link.', 'success', 6000);
        Auth.setMode('login');
        
        // Don't auto-login, wait for user to verify email
        return;
      }
    }

    btn.disabled = false;
    btn.textContent = !isRegister ? 'Sign in' : 'Create account';
    if (ok?.ok && !isRegister) showAppScreen();
  });
}

/* ================================================================
   APP SCREEN EVENTS
   ================================================================ */
function setupAppEvents() {
  // Navigation
  document.addEventListener('click', e => {
    const v = e.target.closest('[data-view]:not(.view)');
    if (v && $('app-screen')?.contains(v)) { e.preventDefault(); UI.showView(v.dataset.view); $('acct-dropdown')?.classList.remove('open'); }

    const sc = e.target.closest('[data-scroll]');
    if (sc) { e.preventDefault(); UI.showView('home'); setTimeout(() => $(sc.dataset.scroll)?.scrollIntoView({ behavior: 'smooth' }), 50); }

    if (!e.target.closest('.auth-area, #acct-btn')) $('acct-dropdown')?.classList.remove('open');
    if (!e.target.closest('.header-search'))         $('search-suggestions')?.classList.remove('open');

    // Suggestion click
    const sug = e.target.closest('.suggestion-item');
    if (sug) {
      const name = sug.dataset.name;
      const inp = $('search-input');
      if (inp) inp.value = name;
      $('search-suggestions')?.classList.remove('open');
      Shop.filters.category = '';
      UI.showView('shop');
      api.get('/products/', { search: name, page: 1, limit: CONFIG.PER_PAGE }, false).then(d => {
        const grid = $('shop-grid');
        if (!grid) return;
        grid.innerHTML = '';
        toArray(d).forEach((p, i) => grid.appendChild(productCard(p, i)));
        setText('result-count', `${toArray(d).length} results for "${name}"`);
      });
    }
  });

  $('hero-shop-btn')?.addEventListener('click', () => UI.showView('shop'));

  // Cart drawer
  $('header-cart-btn')?.addEventListener('click', UI.openCart.bind(UI));
  $('close-cart')?.addEventListener('click', UI.closeCart.bind(UI));
  $('cart-overlay')?.addEventListener('click', UI.closeCart.bind(UI));

  // Cart item controls
  document.addEventListener('click', e => {
    const dec = e.target.closest('[data-dec]');
    if (dec) { const id = dec.dataset.dec; const qty = parseInt(dec.closest('.cart-item')?.querySelector('.qty-val')?.textContent || '1') - 1; if (qty < 1) Cart.remove(id); else Cart.updateQty(id, qty); return; }
    const inc = e.target.closest('[data-inc]');
    if (inc) { Cart.updateQty(inc.dataset.inc, parseInt(inc.dataset.qty || '1') + 1); return; }
    const rem = e.target.closest('[data-remove]');
    if (rem) { Cart.remove(rem.dataset.remove); return; }
  });

  // Coupon
  $('apply-coupon')?.addEventListener('click', async () => {
    const inp = $('coupon-input');
    const msg = $('coupon-message');
    if (!inp?.value.trim()) return;
    const r = await Cart.applyCoupon(inp.value.trim());
    if (msg) { msg.className = 'coupon-message ' + (r.ok ? 'success' : 'error'); msg.textContent = r.ok ? `Coupon applied! -${fmt(r.discount)}` : 'Invalid or expired coupon code.'; }
  });

  $('checkout-btn')?.addEventListener('click', () => Toast.show('Checkout coming soon!', 'info'));

  // Product modal
  $('close-product-modal')?.addEventListener('click', closeProductModal);
  $('product-modal-overlay')?.addEventListener('click', e => { if (e.target === $('product-modal-overlay')) closeProductModal(); });
  $('modal-add-cart')?.addEventListener('click', () => {
    if (!modalPid) return;
    const vid = document.querySelector('.variant-chip.selected')?.dataset.vid || null;
    Cart.add(modalPid, vid);
  });
  $('modal-wishlist-btn')?.addEventListener('click', () => {
    if (!modalPid) return;
    const on = Wishlist.toggle(modalPid);
    const btn = $('modal-wishlist-btn');
    btn?.classList.toggle('active', on);
    btn?.querySelector('svg')?.setAttribute('fill', on ? 'currentColor' : 'none');
    document.querySelectorAll(`.card-wishlist[data-pid="${modalPid}"]`).forEach(b => {
      b.classList.toggle('active', on);
      b.querySelector('svg')?.setAttribute('fill', on ? 'currentColor' : 'none');
    });
  });
  document.querySelectorAll('.modal-tabs .tab-btn').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));

  // Shop filters
  document.addEventListener('click', e => {
    const cat = e.target.closest('[data-filter-cat]');
    if (cat) { Shop.filters.category = cat.dataset.filterCat; Shop.filters.category_id = cat.dataset.filterCatId || ''; Shop.page = 1; Shop.load(); return; }
    const brand = e.target.closest('[data-filter-brand]');
    if (brand) { Shop.filters.brand = brand.dataset.filterBrand; Shop.filters.brand_id = brand.dataset.filterBrandId || ''; Shop.page = 1; Shop.load(); return; }
  });
  $('in-stock-toggle')?.addEventListener('change', e => { Shop.filters.inStock = e.target.checked; Shop.page = 1; Shop.load(); });
  $('apply-price')?.addEventListener('click', () => { Shop.filters.minPrice = $('price-min')?.value || ''; Shop.filters.maxPrice = $('price-max')?.value || ''; Shop.page = 1; Shop.load(); });
  $('sort-select')?.addEventListener('change', e => { Shop.filters.sort = e.target.value; Shop.page = 1; Shop.load(); });
  $('clear-filters')?.addEventListener('click', () => { Shop.filters = { category: '', category_id: '', brand: '', brand_id: '', minPrice: '', maxPrice: '', inStock: false, sort: '' }; Shop.page = 1; Shop.load(); });

  // Search
  $('search-input')?.addEventListener('input', e => { clearTimeout(searchTimer); searchTimer = setTimeout(() => handleSearch(e.target.value), 280); });

  // Header scroll
  window.addEventListener('scroll', () => $('site-header')?.classList.toggle('scrolled', scrollY > 20), { passive: true });

  // Escape
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    closeProductModal();
    UI.closeCart();
    $('search-suggestions')?.classList.remove('open');
    $('acct-dropdown')?.classList.remove('open');
  });
}

/* ================================================================
   UTILITIES
   ================================================================ */
function $(id)           { return document.getElementById(id); }
function esc(s)          { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmt(n)          { return '$' + (parseFloat(n) || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }
function setText(id, t)  { const e = $(id); if (e) e.textContent = t; }
function slug(s)         { return String(s).toLowerCase().replace(/\s+/g, '-'); }
function stars(r)        { let s = ''; const v = Math.round(r * 2) / 2; for (let i = 1; i <= 5; i++) s += v >= i ? '★' : v >= i - 0.5 ? '½' : '☆'; return s; }
function toArray(d)      { if (!d) return []; if (Array.isArray(d)) return d; if (Array.isArray(d.items)) return d.items; if (Array.isArray(d.products)) return d.products; return []; }
function el(tag, cls, txt) { const e = document.createElement(tag); e.className = cls; e.textContent = txt; return e; }

/* ================================================================
   BOOTSTRAP
   ================================================================ */
document.addEventListener('DOMContentLoaded', async () => {
  setupAuthScreen();
  setupAppEvents();
  Wishlist._badge();

  const urlParams = new URLSearchParams(window.location.search);
  const path = window.location.pathname;
  
  let code = urlParams.get('code');
  let view = urlParams.get('view');
  
  // Fallback for malformed URLs like ?view=reset-password?code=...
  if (view && view.includes('?code=')) {
     const parts = view.split('?code=');
     view = parts[0];
     code = parts[1];
  }

  // Handle email verification redirect
  if (path === '/auth/verify-email' && code) {
     const verified = await Auth.verifyEmail(code);
     window.history.replaceState({}, document.title, '/'); // Reset URL
     if (verified) {
        Toast.show('Email verified successfully! You can now log in.', 'success', 5000);
     } else {
        Toast.show('Verification link is invalid or expired.', 'error', 5000);
     }
     showAuthScreen();
     return;
  }

  // Handle password reset redirect
  if (view === 'reset-password' && code) {
     showAuthScreen();
     $('login-view')?.classList.add('hidden');
     $('reset-view')?.classList.remove('hidden');
     
     // Update the URL to remove the code so it doesn't stay in the address bar,
     // but we inject the code into a hidden field or dataset so the form can use it!
     window.history.replaceState({}, document.title, '/?view=reset-password');
     $('reset-form').dataset.code = code;
     return;
  }

  // Try to restore a previous session silently
  const restored = await Auth.tryRestoreSession();
  if (restored) {
    await Auth._fetchMe();
    await showAppScreen();
  } else {
    showAuthScreen();
  }
});
