import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "./ProductionPages";
import { renderWithClient } from "../test/test-utils";
import * as api from "../services/api";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.spyOn(api, "login").mockResolvedValue({ access_token: "access", refresh_token: "refresh", token_type: "bearer" });
    vi.spyOn(api, "register").mockResolvedValue({
      id: 1,
      email: "admin@example.com",
      full_name: "Admin User",
      role: "admin",
      is_active: true,
      created_at: "2026-06-16T00:00:00Z"
    });
  });

  it("logs in with email and password", async () => {
    const user = userEvent.setup();
    const onAuthenticated = vi.fn();
    renderWithClient(<LoginPage onAuthenticated={onAuthenticated} />);

    await user.type(screen.getByLabelText(/email/i), "admin@example.com");
    await user.type(screen.getByLabelText(/password/i), "strong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(api.login).toHaveBeenCalledWith({ email: "admin@example.com", password: "strong-password" }));
    expect(onAuthenticated).toHaveBeenCalled();
  });

  it("surfaces API errors during login", async () => {
    vi.mocked(api.login).mockRejectedValueOnce(new Error("bad credentials"));
    const user = userEvent.setup();
    renderWithClient(<LoginPage onAuthenticated={vi.fn()} />);

    await user.type(screen.getByLabelText(/email/i), "admin@example.com");
    await user.type(screen.getByLabelText(/password/i), "wrong-password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText(/authentication failed/i)).toBeInTheDocument();
  });
});
