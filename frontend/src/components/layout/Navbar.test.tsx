import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Navbar } from "./Navbar";
import { renderWithClient } from "../../test/test-utils";
import * as api from "../../services/api";

vi.mock("../../services/api", async () => {
  const actual = await vi.importActual<typeof import("../../services/api")>("../../services/api");
  return {
    ...actual,
    fetchCurrentUser: vi.fn(),
    fetchAuditEvents: vi.fn(),
    logout: vi.fn()
  };
});

describe("Navbar logout", () => {
  beforeEach(() => {
    vi.mocked(api.fetchCurrentUser).mockResolvedValue({
      id: 1,
      name: "Admin User",
      role: "admin",
      permissions: []
    });
    vi.mocked(api.fetchAuditEvents).mockResolvedValue([]);
    vi.mocked(api.logout).mockResolvedValue(undefined);
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...window.location,
        reload: vi.fn()
      }
    });
  });

  it("logs out from the profile menu", async () => {
    const user = userEvent.setup();
    renderWithClient(<Navbar isDark={false} onThemeToggle={vi.fn()} onMobileMenu={vi.fn()} />);

    await user.click(await screen.findByRole("button", { name: /open user profile menu/i }));
    await user.click(screen.getByRole("button", { name: /sign out/i }));

    await waitFor(() => expect(api.logout).toHaveBeenCalled());
    expect(window.location.reload).toHaveBeenCalled();
  });
});
