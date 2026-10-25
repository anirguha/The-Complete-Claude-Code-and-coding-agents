# Forma

One board, five renameable columns. Add and delete cards; move them with a drag handle. For keyboard movement, focus a handle, press Space, use Left/Right, then Space to drop or Escape to cancel.

Use Node.js 26 (verified with 26.5.0).

```sh
npm ci
npm run dev
```

If an existing npm 12 configuration reports `EALLOWSCRIPTS`, install with `npm --userconfig=/dev/null ci`.

Open the URL printed by Next.js. Changes live in memory; reload restores sample cards.

```sh
npm run lint
npm run typecheck
npm test
npx playwright install chromium
npm run test:e2e
npm run build
```

Browser tests start their own server on port 3100. No accounts, database, or environment variables required.
