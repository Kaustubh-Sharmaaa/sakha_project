const API_URL = "http://localhost:8001/auth";

export async function signup(data) {
  const response = await fetch(`${API_URL}/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Signup failed");
  }

  return response.json();
}

export async function login(data) {
  const response = await fetch(`${API_URL}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Login failed");
  }

  return response.json();
}

export async function logout(refreshToken) {
  const response = await fetch(`${API_URL}/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Logout failed");
  }

  return response.json();
}

export async function refreshAuthToken(refreshToken){
    const response = await fetch (`${API_URL}/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken}),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || "Login failed");
      }
    
      return response.json();
}

export async function requestPasswordReset(email) {
  const response = await fetch(`${API_URL}/reset-password/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Unable to request password reset");
  }

  return response.json();
}

export async function verifyPasswordReset(code) {
  const response = await fetch(
    `${API_URL}/reset-password/verify?code=${encodeURIComponent(code)}`,
    { method: "GET" }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Invalid or expired reset link");
  }

  return response.json();
}

export async function confirmPasswordReset({ code, password, confirmPass }) {
  const response = await fetch(`${API_URL}/reset-password/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, password, confirmPass }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Unable to reset password");
  }

  return response.json();
}