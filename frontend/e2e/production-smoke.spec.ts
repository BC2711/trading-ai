import { expect, test } from "@playwright/test";

const smokeEmail = process.env.E2E_SMOKE_EMAIL || "smoke-admin@example.com";
const smokePassword = process.env.E2E_SMOKE_PASSWORD || "strong-smoke-password";
const apiKey = process.env.E2E_API_KEY || "";

function apiHeaders() {
  return apiKey ? { "X-API-Key": apiKey } : {};
}

test("production smoke: auth, protected UI, and risk validation", async ({ page, request }) => {
  const health = await request.get("/api/health", { headers: apiHeaders() });
  expect(health.ok()).toBeTruthy();

  await request.post("/api/auth/register", {
    headers: apiHeaders(),
    data: {
      email: smokeEmail,
      full_name: "Smoke Admin",
      password: smokePassword,
      role: "admin"
    }
  });

  const login = await request.post("/api/auth/login", {
    headers: apiHeaders(),
    data: {
      email: smokeEmail,
      password: smokePassword
    }
  });
  expect(login.ok()).toBeTruthy();
  const token = (await login.json()).access_token as string;

  const me = await request.get("/api/me", {
    headers: {
      ...apiHeaders(),
      Authorization: `Bearer ${token}`
    }
  });
  expect(me.ok()).toBeTruthy();

  const risk = await request.post("/api/risk/validate-trade", {
    headers: {
      ...apiHeaders(),
      Authorization: `Bearer ${token}`
    },
    data: {
      symbol: "BTCUSDT",
      side: "buy",
      price: 65000,
      quantity: 0.001,
      stop_loss: 64900,
      take_profit: 67000,
      execution_mode: "paper"
    }
  });
  expect(risk.ok()).toBeTruthy();
  expect((await risk.json()).approved).toBe(true);

  await page.goto("/#/login");
  await page.getByLabel("Email").fill(smokeEmail);
  await page.getByLabel("Password").fill(smokePassword);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Workspace")).toBeVisible();
  await expect(page.getByRole("button", { name: "Open user profile menu" })).toBeVisible();
});
