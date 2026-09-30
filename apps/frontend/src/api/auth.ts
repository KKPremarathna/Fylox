import type { LoginResponse, User } from "../types/api";
import { API_BASE_URL, apiRequest } from "./client";

export async function login(
  username: string,
  password: string,
): Promise<LoginResponse> {
  const formData = new URLSearchParams();

  formData.set("username", username);
  formData.set("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);

    throw new Error(
      payload?.detail ?? "Unable to log in. Check your credentials.",
    );
  }

  return response.json() as Promise<LoginResponse>;
}

export function getCurrentUser(token: string): Promise<User> {
  return apiRequest<User>("/auth/me", {
    token,
  });
}

export function register(
  username: string,
  email: string,
  password: string,
): Promise<User> {
  return apiRequest<User>("/users", {
    method: "POST",
    body: JSON.stringify({
      username,
      email,
      password,
    }),
  });
}