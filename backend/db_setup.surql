-- Sakha Product API — One-time DB setup script
-- Run with: /opt/homebrew/bin/surreal sql --conn http://localhost:8000 --user root --pass root --ns sakha --db products --hide-welcome

-- ── Indexes for fast queries ──────────────────────────────────────────────────

-- Users
DEFINE INDEX idx_user_email ON user FIELDS email UNIQUE;

-- Sessions
DEFINE INDEX idx_session_user ON sessions FIELDS user_id;
DEFINE INDEX idx_session_hash ON sessions FIELDS refresh_token_hash UNIQUE;

-- Email Verifications
DEFINE INDEX idx_email_verif_code ON email_verifications FIELDS code UNIQUE;
DEFINE INDEX idx_email_verif_user ON email_verifications FIELDS user_id;

-- Password Resets
DEFINE INDEX idx_pass_reset_code ON password_resets FIELDS code UNIQUE;
DEFINE INDEX idx_pass_reset_user ON password_resets FIELDS user_id;

-- Products
DEFINE INDEX idx_product_sku      ON product FIELDS sku UNIQUE;
DEFINE INDEX idx_product_status   ON product FIELDS status;
DEFINE INDEX idx_product_category ON product FIELDS category_id;
DEFINE INDEX idx_product_brand    ON product FIELDS brand_id;

-- Variants
DEFINE INDEX idx_variant_sku     ON variant FIELDS sku UNIQUE;
DEFINE INDEX idx_variant_product ON variant FIELDS product_id;

-- Cart
DEFINE INDEX idx_cart_user        ON cart FIELDS user_id;
DEFINE INDEX idx_cart_item_cart   ON cart_item FIELDS cart_id;
DEFINE INDEX idx_cart_item_lookup ON cart_item FIELDS cart_id, product_id, variant_id;

-- Orders
DEFINE INDEX idx_order_user       ON order FIELDS user_id;
DEFINE INDEX idx_order_item_order ON order_item FIELDS order_id;

-- Reviews & Q&A
DEFINE INDEX idx_review_product  ON review FIELDS product_id;
DEFINE INDEX idx_review_user     ON review FIELDS user_id;
DEFINE INDEX idx_question_product ON question FIELDS product_id;

-- Analytics
DEFINE INDEX idx_view_product ON product_view FIELDS product_id;
DEFINE INDEX idx_view_time    ON product_view FIELDS created_at;

-- Coupons
DEFINE INDEX idx_coupon_code ON coupon FIELDS code UNIQUE;

-- Brands
DEFINE INDEX idx_brand_slug ON brand FIELDS slug UNIQUE;

-- Categories
DEFINE INDEX idx_category_slug ON category FIELDS slug UNIQUE;

-- Stock reservations
DEFINE INDEX idx_reservation_product ON stock_reservation FIELDS product_id;
DEFINE INDEX idx_reservation_order   ON stock_reservation FIELDS order_ref;

-- Notifications
DEFINE INDEX idx_notif_sub ON notification_sub FIELDS product_id, email, type;

RETURN "✅ All indexes created";
