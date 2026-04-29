# API Reference & Integration Details

This document covers both REST APIs that make up the Sakha platform.

| API | Base URL | Purpose |
|---|---|---|
| Main Product API | `http://localhost:8080/api/v1` | Products, cart, orders, reviews, analytics, etc. |
| Auth Microservice | `http://localhost:8001` | Registration, login, email verification, password reset |

The **frontend** (`http://localhost:3000`) routes all authentication calls to the Auth Microservice and all product/commerce calls to the Main Product API.

---

## Auth Microservice

The Auth Microservice handles the full user authentication lifecycle. All endpoints are prefixed with `/auth`.

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | — | Register a new account; triggers a verification email |
| `POST` | `/auth/register` | — | Alias for `/auth/signup` |
| `POST` | `/auth/login` | — | Log in; returns token pair — **requires verified email** |
| `POST` | `/auth/refresh` | — | Exchange a refresh token for a new token pair |
| `GET` | `/auth/me` | Bearer | Return the current user's profile |
| `GET` | `/auth/verify-email` | — | Confirm an email address using a code sent by email |
| `POST` | `/auth/reset-password/request` | — | Send a password reset link to an email address |
| `GET` | `/auth/reset-password/verify` | — | Validate a password reset code |
| `POST` | `/auth/reset-password/confirm` | — | Set a new password using a valid reset code |
| `POST` | `/auth/logout` | — | Revoke the current refresh token / session |

### Email Verification Requirement

Accounts must verify their email address before they can log in. Attempting to log in with an unverified account returns:

```
HTTP 403 — "Please verify your email before signing in"
```

The verification link is emailed at signup and is valid for `EMAIL_VERIFICATION_TTL_SECONDS` (default 1 hour).

### Token Flow

```bash
# 1. Register — triggers a verification email
POST /auth/signup
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "yourpassword"
}
# → returns the created user object (no token yet)

# 2. Verify email — user clicks the link in their inbox
GET /auth/verify-email?code=<code_from_email>
# → { "verified": true }

# 3. Log in — only works after verification
POST /auth/login
{ "email": "jane@example.com", "password": "yourpassword" }
# → { "access_token": "...", "refresh_token": "...", "token_type": "bearer" }

# 4. Get current user profile
GET /auth/me
Authorization: Bearer <access_token>

# 5. Refresh when the access token expires (TTL: 15 minutes)
POST /auth/refresh
{ "refresh_token": "<refresh_token>" }
# → new token pair

# 6. Log out — revokes the session
POST /auth/logout
{ "refresh_token": "<refresh_token>" }
```

### Password Reset Flow

```bash
# 1. Request a reset link
POST /auth/reset-password/request
{ "email": "jane@example.com" }
# → { "message": "If your email exists, a password reset link has been sent" }
# (always returns 200 to avoid email enumeration)

# 2. Validate the code (optional — the frontend does this on page load)
GET /auth/reset-password/verify?code=<code_from_email>
# → { "valid": true }

# 3. Set the new password
POST /auth/reset-password/confirm
{
  "code": "<code_from_email>",
  "password": "newpassword",
  "confirmPass": "newpassword"
}
# → { "success": true, "message": "Password reset successfully" }
```

Reset links are valid for `PASSWORD_RESET_TTL_SECONDS` (default 30 minutes) and can only be used once.

### Auth Microservice Error Codes

| Status | Meaning |
|---|---|
| `400` | Invalid or expired verification / reset code |
| `401` | Missing, invalid, or expired token; wrong credentials |
| `403` | Email not yet verified |

---

## Main Product API Environment Variables

All settings are in `config.py` and can be overridden via a `.env` file in the `backend/` directory or via shell environment variables.

| Variable | Default | Description |
|---|---|---|
| `SURREAL_URL` | `ws://localhost:8000` | SurrealDB WebSocket URL |
| `SURREAL_USER` | `root` | SurrealDB username |
| `SURREAL_PASS` | `root` | SurrealDB password |
| `SURREAL_NS` | `sakha` | SurrealDB namespace |
| `SURREAL_DB` | `products` | SurrealDB database name |
| `SECRET_KEY` | `CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND` | JWT signing key — **must change in production** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `MEDIA_DIR` | `media` | Directory for uploaded files |
| `MAX_UPLOAD_MB` | `20` | Max file upload size |
| `API_PREFIX` | `/api/v1` | URL prefix for all routes |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins — tighten in production |

Example `.env`:
```env
SECRET_KEY=your-very-long-random-secret-here
SURREAL_PASS=strongpassword
ALLOWED_ORIGINS=["https://yourfrontend.com"]
```

---

## Main Product API — Authentication

Most write endpoints and all admin endpoints require a JWT Bearer token. Tokens are issued by the **Auth Microservice** (see above) and accepted by the Main Product API.

```
Authorization: Bearer <access_token>
```

### Role levels

| Role | Access |
|---|---|
| *(unauthenticated)* | Read-only public endpoints (product list, reviews, search) |
| `user` | Own cart, orders, reviews, wishlist |
| `admin` | Everything, including analytics, bulk ops, coupon management, order status updates |

---

## Main Product API Reference

All routes are prefixed with `/api/v1`. Auth requirements are noted as **[user]** or **[admin]**.

---

### Auth (Main Product API)

> The frontend uses the **Auth Microservice** (`localhost:8001`) for all auth flows. The routes below are the Main Product API's own auth layer, used for direct API / admin access.

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/register` | — | Create account, returns token pair |
| `POST` | `/auth/login` | — | Login, returns token pair |
| `POST` | `/auth/refresh` | — | Exchange refresh token for new token pair |
| `GET` | `/auth/me` | [user] | Get current user profile |

**Register body:**
```json
{
  "email": "user@example.com",
  "password": "min8chars",
  "name": "Full Name",
  "role": "user"
}
```

---

### Products

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/` | [user] | Create product (starts as `draft`) |
| `GET` | `/products/` | — | List products (paginated) |
| `GET` | `/products/{id}` | — | Get single product |
| `PATCH` | `/products/{id}` | [user] | Update product fields |
| `DELETE` | `/products/{id}` | [user] | Archive product (soft delete) |
| `POST` | `/products/{id}/restore` | [user] | Restore archived product |
| `POST` | `/products/{id}/publish` | [user] | Set status to `active` |
| `POST` | `/products/{id}/unpublish` | [user] | Set status back to `draft` |
| `POST` | `/products/{id}/duplicate` | [user] | Clone product with variants and images |
| `GET` | `/products/{id}/changelog` | — | Audit log of all changes |

**Lifecycle (requires approval flow):**

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/{id}/submit-for-review` | [user] | Move to `pending_review` |
| `POST` | `/products/{id}/approve` | [admin] | Move to `approved` |
| `POST` | `/products/{id}/reject` | [admin] | Move to `rejected` with a reason |
| `POST` | `/products/{id}/lock` | [admin] | Prevent edits |
| `POST` | `/products/{id}/unlock` | [admin] | Re-allow edits |

**SEO & Shipping:**

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/products/{id}/seo` | — | Get SEO metadata |
| `PATCH` | `/products/{id}/seo` | [user] | Update SEO metadata |
| `PATCH` | `/products/{id}/shipping` | [user] | Update shipping dimensions/weight |
| `POST` | `/products/{id}/shipping-rates` | — | Get estimated shipping rates |

**List query parameters:**

| Param | Type | Description |
|---|---|---|
| `page` | int | Page number (default: 1) |
| `limit` | int | Items per page, max 200 (default: 20) |
| `category_id` | string | Filter by category |
| `brand_id` | string | Filter by brand |
| `status` | string | Filter by status (`draft`, `active`) |
| `sort_by` | string | Field to sort by (default: `created_at`) |
| `order` | string | `ASC` or `DESC` (default: `DESC`) |

**Create body:**
```json
{
  "name": "Blue Sneaker",
  "description": "Comfortable everyday sneaker",
  "sku": "SNKR-BLU-001",
  "price": 79.99,
  "category_id": "category:abc",
  "brand_id": "brand:xyz",
  "tags": ["shoes", "sale"],
  "status": "draft"
}
```

---

### Variants

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/{id}/variants` | [user] | Add a variant (size, colour, etc.) |
| `GET` | `/products/{id}/variants` | — | List variants for a product |
| `PATCH` | `/products/{id}/variants/{variant_id}` | [user] | Update variant |
| `DELETE` | `/products/{id}/variants/{variant_id}` | [user] | Delete variant |
| `POST` | `/products/{id}/variants/bulk` | [user] | Create multiple variants at once |

---

### Inventory

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/products/{id}/stock` | — | Stock levels for product and all variants |
| `POST` | `/products/{id}/stock/adjust` | [user] | Add or subtract stock (`quantity` may be negative) |
| `POST` | `/products/{id}/stock/set` | [user] | Set stock to an absolute value |
| `POST` | `/products/{id}/stock/reserve` | [user] | Reserve units for a pending order |
| `POST` | `/products/{id}/stock/release` | [user] | Release a reservation |
| `GET` | `/products/{id}/stock/history` | [user] | Audit log of stock changes |
| `POST` | `/products/{id}/stock/bulk` | [user] | Update stock for multiple variants at once |
| `GET` | `/products/low-stock` | [user] | Products below reorder threshold |

**Adjust body:**
```json
{
  "quantity": -5,
  "reason": "damaged",
  "note": "Water damage on 3 units",
  "variant_id": "variant:abc"
}
```

---

### Pricing

| Method | Path | Auth | Description |
|---|---|---|---|
| `PATCH` | `/products/{id}/price` | [user] | Update price and compare-at price |
| `POST` | `/products/{id}/discounts` | [user] | Create a time-limited discount |
| `GET` | `/products/{id}/discounts` | — | List active discounts |
| `DELETE` | `/discounts/{id}` | [user] | Delete a discount |
| `POST` | `/pricing/rules` | [user] | Create a volume/tiered pricing rule |
| `GET` | `/pricing/rules/{id}` | — | Get pricing rules for a product |

**Pricing rule example** (buy 5+ for a lower price):
```json
{
  "product_id": "product:abc",
  "min_quantity": 5,
  "price": 9.99
}
```

---

### Categories & Collections

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/categories` | [user] | Create category |
| `GET` | `/categories` | — | List all categories (flat; build tree from `parent_id`) |
| `GET` | `/categories/{id}` | — | Get single category |
| `PATCH` | `/categories/{id}` | [user] | Update category |
| `DELETE` | `/categories/{id}` | [user] | Delete category |
| `POST` | `/categories/{id}/products` | [user] | Assign a product to a category |
| `POST` | `/collections` | [user] | Create a collection (manual or rule-based) |
| `GET` | `/collections` | — | List collections |
| `PATCH` | `/collections/{id}` | [user] | Update collection |
| `POST` | `/collections/{id}/products` | [user] | Add product to manual collection |

---

### Attributes

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/attributes` | [user] | Create an attribute definition (e.g. "Color") |
| `GET` | `/attributes` | — | List all attributes |
| `POST` | `/products/{id}/attributes` | [user] | Set attribute values on a product |
| `GET` | `/products/{id}/attributes` | — | Get a product's attribute values |

---

### Brands

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/brands/` | [user] | Create brand |
| `GET` | `/brands/` | — | List all brands |
| `GET` | `/brands/{id}` | — | Get single brand |
| `PATCH` | `/brands/{id}` | [user] | Update brand |
| `DELETE` | `/brands/{id}` | [user] | Delete brand |
| `GET` | `/brands/{id}/products` | — | All products for a brand |

---

### Tags

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/tags` | — | List all tags with usage counts |
| `POST` | `/products/{id}/tags` | [user] | Add tags to a product |
| `DELETE` | `/products/{id}/tags/{tag}` | [user] | Remove a tag from a product |

---

### Search & Discovery

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/products/search` | — | Full-text search across name and description |
| `GET` | `/products/filter` | — | Faceted filter with category/brand/price facets |
| `GET` | `/products/suggestions` | — | Autocomplete suggestions (`?q=sho`) |
| `GET` | `/products/related/{id}` | — | Products in the same category |
| `GET` | `/products/trending` | — | Most-viewed products in the last 7 days |
| `GET` | `/products/recently-viewed` | [user] | Recently viewed by the current user |
| `POST` | `/products/{id}/view` | — | Log a product view event |

**Search query parameters:**

| Param | Type | Description |
|---|---|---|
| `q` | string | Search term |
| `category_id` | string | Filter by category |
| `brand_id` | string | Filter by brand |
| `min_price` | float | Minimum price |
| `max_price` | float | Maximum price |
| `tags` | string | Comma-separated tag filter (e.g. `sale,new`) |
| `in_stock` | bool | Only show in-stock products |
| `sort_by` | string | Sort field (default: `created_at`) |
| `page` / `limit` | int | Pagination |

---

### Cart

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/cart/` | — | Create a new cart |
| `GET` | `/cart/{id}` | — | Get cart with all items |
| `GET` | `/cart/{id}/summary` | — | Subtotal, discount, tax, shipping, grand total |
| `POST` | `/cart/{id}/items` | — | Add an item (merges quantity if already in cart) |
| `PATCH` | `/cart/{id}/items/{item_id}` | — | Update item quantity (set to 0 to remove) |
| `DELETE` | `/cart/{id}/items/{item_id}` | — | Remove an item |
| `DELETE` | `/cart/{id}/clear` | — | Remove all items |
| `POST` | `/cart/{id}/coupon` | — | Apply a coupon code |
| `DELETE` | `/cart/{id}/coupon` | — | Remove the applied coupon |
| `POST` | `/cart/merge` | — | Merge a guest cart into a logged-in user's cart |

**Summary response:**
```json
{
  "subtotal": 80.00,
  "discount": 8.00,
  "coupon_code": "SAVE10",
  "tax": 5.76,
  "shipping_estimate": 0.00,
  "grand_total": 77.76
}
```

> Shipping is free for orders over $50. Tax rate is 8%.

---

### Coupons

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/coupons/` | [admin] | Create a coupon |
| `GET` | `/coupons/` | [admin] | List all coupons |
| `POST` | `/coupons/validate` | — | Check a code and preview the discount |
| `DELETE` | `/coupons/{id}` | [admin] | Deactivate a coupon |

**Coupon types:** `percentage`, `fixed`, `free_shipping`

**Create body:**
```json
{
  "code": "SUMMER20",
  "type": "percentage",
  "value": 20,
  "usage_limit": 100,
  "min_order_value": 30.00,
  "starts_at": "2026-06-01T00:00:00Z",
  "ends_at": "2026-08-31T23:59:59Z"
}
```

**Validate body:**
```json
{
  "code": "SUMMER20",
  "cart_id": "cart:abc123"
}
```

---

### Orders

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/orders/` | [user] | Place an order from a cart (validates stock, calculates totals, deducts stock) |
| `GET` | `/orders/` | [user] | List current user's orders |
| `GET` | `/orders/{id}` | [user] | Get order detail with line items |
| `PATCH` | `/orders/{id}/cancel` | [user] | Cancel a `pending` or `processing` order |
| `POST` | `/orders/{id}/refund` | [user] | Request a partial or full refund |
| `GET` | `/orders/{id}/tracking` | — | Get tracking number and carrier |
| `PATCH` | `/orders/{id}/status` | [admin] | Update status, tracking number, carrier |
| `POST` | `/orders/{id}/invoice` | [user] | Get invoice data |
| `POST` | `/orders/{id}/download/{asset_id}` | [user] | Generate a signed 24h download URL for digital products |

**Order statuses:** `pending` → `processing` → `shipped` → `delivered` → `refunded` / `cancelled`

**Place order body:**
```json
{
  "cart_id": "cart:abc123",
  "shipping_address": {
    "line1": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001",
    "country": "US"
  },
  "billing_address": { "...": "same shape as shipping_address" },
  "payment_method_id": "pm_stripe_token",
  "coupon_code": "SAVE10"
}
```

**Refund body:**
```json
{
  "items": [
    { "order_item_id": "order_item:abc", "quantity": 1 }
  ],
  "reason": "Item arrived damaged",
  "refund_method": "original"
}
```

---

### Reviews & Ratings

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/{id}/reviews` | [user] | Submit a review (one per user per product) |
| `GET` | `/products/{id}/reviews` | — | List approved reviews |
| `GET` | `/products/{id}/rating-summary` | — | Average rating and star distribution |
| `PATCH` | `/reviews/{id}` | [user] | Edit own review |
| `DELETE` | `/reviews/{id}` | [user/admin] | Delete review |
| `POST` | `/reviews/{id}/helpful` | — | Increment helpful count |
| `POST` | `/reviews/{id}/report` | — | Report a review (`spam`, `offensive`, `irrelevant`, `fake`) |
| `PATCH` | `/reviews/{id}/moderate` | [admin] | Approve or reject a review |

**Sort options for listing:** `newest`, `highest`, `lowest`

---

### Q&A

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/{id}/questions` | [user] | Ask a question |
| `GET` | `/products/{id}/questions` | — | List questions and answers |
| `POST` | `/questions/{id}/answers` | [user] | Answer a question |
| `POST` | `/questions/{id}/helpful` | — | Mark a question as helpful |

---

### Wishlist

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/wishlist/` | [user] | Create a wishlist |
| `GET` | `/wishlist/` | [user] | List current user's wishlists |
| `GET` | `/wishlist/{id}` | [user] | Get a wishlist with items |
| `POST` | `/wishlist/{id}/items` | [user] | Add product to wishlist |
| `DELETE` | `/wishlist/{id}/items/{item_id}` | [user] | Remove from wishlist |
| `POST` | `/wishlist/{id}/move-to-cart` | [user] | Move all items to a cart |

---

### Bundles

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/bundles` | [user] | Create a product bundle / kit |
| `GET` | `/products/bundles` | — | List all bundles |
| `PATCH` | `/products/bundles/{id}` | [user] | Update bundle |
| `DELETE` | `/products/bundles/{id}` | [user] | Delete bundle |

---

### Compare

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/compare` | — | Compare up to 4 products side-by-side |

**Body:**
```json
{ "product_ids": ["product:a", "product:b", "product:c"] }
```

---

### Notifications

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/{id}/notify-restock` | — | Subscribe to back-in-stock alert |
| `GET` | `/products/{id}/notify-restock` | [admin] | List restock subscribers |

---

### Analytics

All analytics endpoints require **[admin]**.

| Method | Path | Description |
|---|---|---|
| `GET` | `/analytics/products/top-selling` | Best sellers by revenue or units |
| `GET` | `/analytics/products/views` | Product view counts by time range |
| `GET` | `/analytics/products/conversion` | Views → cart adds → purchases funnel |
| `GET` | `/analytics/products/revenue` | Revenue breakdown by product/category/brand |
| `GET` | `/analytics/inventory/turnover` | Stock rotation speed |
| `GET` | `/analytics/reviews/sentiment` | Average rating per product |

**Top-selling parameters:**

| Param | Default | Description |
|---|---|---|
| `metric` | `revenue` | `revenue` or `units` |
| `from_date` | — | ISO date string |
| `to_date` | — | ISO date string |
| `limit` | `10` | Max results |

---

### Bulk Operations

All bulk endpoints require **[admin]**.

| Method | Path | Description |
|---|---|---|
| `POST` | `/products/import` | Upload CSV or JSON to create/update products |
| `GET` | `/products/export` | Export product catalog as CSV or JSON |
| `POST` | `/products/bulk/publish` | Publish multiple products by ID |
| `POST` | `/products/bulk/update-price` | Update prices for multiple products |

**Import query params:** `mode=upsert` (default) or `mode=create_only`, `dry_run=true` to preview without writing.

---

### Media

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/products/{id}/images` | [user] | Upload an image for a product |
| `GET` | `/products/{id}/images` | — | List all images for a product |
| `PATCH` | `/products/{id}/images/{image_id}` | [user] | Update image metadata (alt text, sort order) |
| `DELETE` | `/products/{id}/images/{image_id}` | [user] | Delete an image |
| `POST` | `/products/{id}/images/{image_id}/primary` | [user] | Set as primary image |

Uploaded files are served from `/media/<filename>`. To use S3 instead, swap the implementation in `storage.py`.

---

## Error Codes

| Status | Meaning |
|---|---|
| `400` | Bad request — malformed input |
| `401` | Unauthorized — missing or invalid token |
| `403` | Forbidden — valid token but insufficient role |
| `404` | Not found |
| `409` | Conflict — e.g. duplicate SKU or email |
| `422` | Unprocessable entity — validation error or business rule violation |
| `423` | Locked — product is locked and cannot be edited |
| `500` | Internal server error |

All error responses follow FastAPI's standard shape:
```json
{
  "detail": "Human-readable error message"
}
```
