import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Sidebar } from "./Sidebar";
import { renderWithClient } from "../../test/test-utils";
import * as api from "../../services/api";

vi.mock("../../services/api", async () => {
  const actual = await vi.importActual<typeof import("../../services/api")>("../../services/api");
  return {
    ...actual,
    fetchCurrentUser: vi.fn(),
    fetchNavigation: vi.fn()
  };
});

const adminPermissions = [
  "dashboard:view",
  "portfolio:view",
  "signals:view",
  "users:manage",
  "manage_users",
  "audit:view",
  "api-credentials:manage",
  "notifications:manage",
  "logs:view",
  "strategies:view",
  "strategies:update",
  "backtests:view",
  "backtests:run",
  "ai-models:view",
  "ai-analyses:view",
  "ai-models:manage",
  "orders:view",
  "orders:create",
  "positions:view",
  "risk-settings:view",
  "notifications:view"
];

function mockUser(permissions = adminPermissions) {
  vi.mocked(api.fetchCurrentUser).mockResolvedValue({
    id: 1,
    name: "Admin User",
    role: "admin",
    permissions
  });
  vi.mocked(api.fetchNavigation).mockResolvedValue([]);
}

describe("Sidebar", () => {
  beforeEach(() => {
    mockUser();
  });

  it("renders primary sidebar navigation and expands child links", async () => {
    const user = userEvent.setup();
    renderWithClient(<Sidebar collapsed={false} onToggle={vi.fn()} />);

    expect(await screen.findByRole("navigation", { name: /main navigation/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /trading/i }));

    expect(screen.getByRole("link", { name: /paper trading/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /broker connections/i })).toBeInTheDocument();
  });

  it("shows collapsed submenu tooltip on hover", async () => {
    const user = userEvent.setup();
    renderWithClient(<Sidebar collapsed onToggle={vi.fn()} />);

    await screen.findByRole("button", { name: /administration/i });
    await user.hover(screen.getByRole("button", { name: /administration/i }));

    expect(await screen.findByRole("tooltip")).toHaveTextContent("Roles & Permissions");
  });

  it("hides menu groups that the current role cannot access", async () => {
    mockUser(["dashboard:view", "portfolio:view", "signals:view"]);
    renderWithClient(<Sidebar collapsed={false} onToggle={vi.fn()} />);

    expect(await screen.findByRole("button", { name: /overview/i })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("button", { name: /administration/i })).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /trading/i })).not.toBeInTheDocument();
  });
});
