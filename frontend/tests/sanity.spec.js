import { test, expect } from '@playwright/test';

test.describe('Wildlife App Sanity Check', () => {
  test('landing page loads and has navigation', async ({ page }) => {
    await page.goto('http://localhost:5173');
    
    // Check title
    await expect(page).toHaveTitle(/Koyna Wildlife/i);
    
    // Check for main CTA
    const exploreBtn = page.getByText(/Get Started/i).or(page.getByText(/Explore/i));
    await expect(exploreBtn.first()).toBeVisible();
    
    // Check Navbar
    await expect(page.locator('nav')).toBeVisible();
  });

  test('navigation to login works', async ({ page }) => {
    await page.goto('http://localhost:5173');
    const loginBtn = page.getByRole('link', { name: /Sign In/i }).or(page.getByText(/Login/i));
    if (await loginBtn.count() > 0) {
      await loginBtn.first().click();
      await expect(page).toHaveURL(/.*auth/);
    }
  });

  test('dashboard loads (if authenticated/bypass)', async ({ page }) => {
    // Note: In a real test we'd login, but here we just check if it renders skeletons or content
    await page.goto('http://localhost:5173/dashboard');
    // It should either show the dashboard or redirect to auth
    const currentUrl = page.url();
    if (currentUrl.includes('dashboard')) {
      await expect(page.locator('.page-wrapper')).toBeVisible();
    } else {
      await expect(page).toHaveURL(/.*auth/);
    }
  });
});
