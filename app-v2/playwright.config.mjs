import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',use:{baseURL:'http://127.0.0.1:8767',viewport:{width:1440,height:1000}},webServer:{command:'node server.mjs --demo',url:'http://127.0.0.1:8767/api/status',reuseExistingServer:!process.env.CI},reporter:'list',outputDir:'test-results'});
