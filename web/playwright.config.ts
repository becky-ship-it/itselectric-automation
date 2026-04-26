import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:8000',
    headless: true,
  },
  // Server must already be running — no webServer block
})
