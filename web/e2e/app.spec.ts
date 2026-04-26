import { test, expect } from '@playwright/test'

// All tests run against the live server at localhost:8000.
// Start the server with ./run_server.sh before running these.

test.describe('Navigation', () => {
  test('sidebar links navigate to each page', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle("It's Electric")

    await page.getByRole('link', { name: 'Inbox' }).click()
    await expect(page).toHaveURL(/\/inbox/)

    await page.getByRole('link', { name: 'History' }).click()
    await expect(page).toHaveURL(/\/history/)

    await page.getByRole('link', { name: 'Config' }).click()
    await expect(page).toHaveURL(/\/config/)

    await page.getByRole('link', { name: 'Logs' }).click()
    await expect(page).toHaveURL(/\/logs/)

    await page.getByRole('link', { name: 'Dashboard' }).click()
    await expect(page).toHaveURL('http://localhost:8000/')
  })

  test('direct URL navigation works (SPA routing)', async ({ page }) => {
    for (const path of ['/inbox', '/history', '/config', '/logs']) {
      await page.goto(path)
      await expect(page).toHaveTitle("It's Electric")
      await expect(page.locator('nav')).toBeVisible()
    }
  })
})

test.describe('Dashboard', () => {
  test('shows pending and unparsed counts and pipeline buttons', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText('Pending')).toBeVisible()
    await expect(page.getByText('Unparsed')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Run Pipeline' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Run with fixtures' })).toBeVisible()
  })
})

test.describe('Inbox', () => {
  test('shows All / Pending / Unparsed tabs', async ({ page }) => {
    await page.goto('/inbox')
    // Use the tab strip — not contact row buttons which also contain these words
    const tabStrip = page.locator('div').filter({ has: page.getByRole('button', { name: 'All', exact: true }) }).first()
    await expect(tabStrip.getByRole('button', { name: 'All', exact: true })).toBeVisible()
    await expect(tabStrip.getByRole('button', { name: 'Pending', exact: true })).toBeVisible()
    await expect(tabStrip.getByRole('button', { name: 'Unparsed', exact: true })).toBeVisible()
  })

  test('All tab lists contacts', async ({ page }) => {
    await page.goto('/inbox')
    await expect(page.getByText(/\d+ contacts/)).toBeVisible()
  })

  test('Unparsed tab loads without error', async ({ page }) => {
    await page.goto('/inbox')
    // Click the Unparsed tab — it's in the first flex row of buttons
    await page.locator('button', { hasText: 'Unparsed' }).first().click()
    await expect(page.getByText(/contacts/)).toBeVisible()
  })

  test('selecting a contact shows detail panel with editable fields', async ({ page }) => {
    await page.goto('/inbox')
    // Click first contact row (text-left buttons with name + address)
    const firstContact = page.locator('button.text-left').first()
    await firstContact.click()
    // Detail panel: look for the field labels
    await expect(page.getByText('Name').first()).toBeVisible()
    await expect(page.getByText('Email').first()).toBeVisible()
    await expect(page.getByText('Address').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save & Route' })).toBeVisible()
  })

  test('contact detail shows email preview', async ({ page }) => {
    await page.goto('/inbox')
    const firstContact = page.locator('button.text-left').first()
    await firstContact.click()
    await expect(page.getByText('EMAIL PREVIEW')).toBeVisible()
  })
})

test.describe('History', () => {
  test('shows contacts table with search and download buttons', async ({ page }) => {
    await page.goto('/history')
    await expect(page.getByRole('heading', { name: 'History' })).toBeVisible()
    await expect(page.getByPlaceholder('Search by name, address, or email…')).toBeVisible()
    await expect(page.getByRole('link', { name: 'Download CSV' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Download JSON' })).toBeVisible()
  })

  test('table shows contact rows', async ({ page }) => {
    await page.goto('/history')
    await expect(page.getByRole('columnheader', { name: 'NAME' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'ADDRESS' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'STATUS' })).toBeVisible()
  })

  test('search filters contacts', async ({ page }) => {
    await page.goto('/history')
    const searchBox = page.getByPlaceholder('Search by name, address, or email…')
    await searchBox.fill('zzznomatch')
    await page.waitForTimeout(400)
    await expect(page.getByText('No contacts')).toBeVisible()
  })
})

test.describe('Config', () => {
  test('shows Templates and Decision Tree sections', async ({ page }) => {
    await page.goto('/config')
    await expect(page.getByRole('heading', { name: 'Templates' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Decision Tree' })).toBeVisible()
  })

  test('Guide buttons are present', async ({ page }) => {
    await page.goto('/config')
    const guideLinks = page.getByRole('link', { name: 'Guide' })
    await expect(guideLinks.first()).toBeVisible()
    expect(await guideLinks.count()).toBeGreaterThanOrEqual(2)
  })

  test('selecting a template shows editor with Save button', async ({ page }) => {
    await page.goto('/config')
    const firstTemplate = page.locator('button').filter({ hasText: /^[a-z_]+$/ }).first()
    await firstTemplate.click()
    await expect(page.getByPlaceholder(/Markdown/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Save template' })).toBeVisible()
  })

  test('Guide button navigates to template guide', async ({ page }) => {
    await page.goto('/config')
    await page.getByRole('link', { name: 'Guide' }).first().click()
    await expect(page).toHaveURL(/guide\/templates/)
    await expect(page.getByRole('heading', { name: 'Email Template Guide' })).toBeVisible()
    await expect(page.getByRole('link', { name: '← Back to Config' })).toBeVisible()
  })

  test('Decision Tree Guide page loads', async ({ page }) => {
    await page.goto('/guide/decision-tree')
    await expect(page.getByRole('heading', { name: 'Decision Tree Guide' })).toBeVisible()
    await expect(page.getByText('Available fields')).toBeVisible()
    await expect(page.getByText('Operators')).toBeVisible()
    await expect(page.getByRole('link', { name: '← Back to Config' })).toBeVisible()
  })

  test('decision tree editor is visible', async ({ page }) => {
    await page.goto('/config')
    await expect(page.getByRole('button', { name: 'Save decision tree' })).toBeVisible()
  })
})

test.describe('Logs', () => {
  test('shows logs page with controls', async ({ page }) => {
    await page.goto('/logs')
    await expect(page.getByRole('heading', { name: 'Logs' })).toBeVisible()
    await expect(page.getByLabel('Auto-scroll')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Clear' })).toBeVisible()
  })
})
