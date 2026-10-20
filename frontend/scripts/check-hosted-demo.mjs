import assert from 'node:assert/strict';
import { validateHostedDemoConfig } from './hosted-demo-config.mjs';
const valid = {VITE_HOSTED_DEMO:'true', VITE_API_BASE_URL:'https://demo-api.example.invalid/api/v1', VITE_ENABLE_MOCK_LOGIN:'false'};
validateHostedDemoConfig(valid);
validateHostedDemoConfig({}); // Preserve independent existing demos/development.
for (const change of [{VITE_API_BASE_URL:'http://demo-api.example.invalid/api/v1'}, {VITE_API_BASE_URL:'/api/v1'},
  {VITE_API_BASE_URL:'https://user:secret@example.invalid/api/v1'}, {VITE_API_BASE_URL:'https://example.invalid/api/v1?token=x'},
  {VITE_API_BASE_URL:'https://example.invalid/api'}, {VITE_ENABLE_MOCK_LOGIN:'true'}, {VITE_HOSTED_DEMO:'1'}])
  assert.throws(() => validateHostedDemoConfig({...valid,...change}));
console.log('PASS: hosted-demo HTTPS/API-prefix/mock-login build gates and legacy mode preservation.');
