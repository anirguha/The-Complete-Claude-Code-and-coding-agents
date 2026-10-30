# FinAlly Specification Review

The plan establishes a coherent demo scope, but several accounting, market-data, and API decisions still allow materially different implementations. Section 13 identifies many of these gaps accurately; its proposed resolutions need the changes below before becoming the build contract.

This review evaluates the specification and supporting design documents only. The absence of application code is expected.

## High-severity findings

### 1. Monetary rounding can create inconsistent trades

**Severity:** High  
**Sections:** 7, 8, 9; Section 13 item 8

SQLite `REAL` values and “round at write time” do not define a consistent accounting model. With fractional shares, quantity × price can produce fractions of a cent. Independently rounding cash, average cost, and trade values can make the recorded trade disagree with the cash movement. Rounding a positive quantity to four decimals can also turn it into zero.

**Suggested resolution:** Change item 8. Define quantity increments, supported price precision, rounding mode, and one authoritative calculation of the settlement amount. Use decimal arithmetic and an exact persisted representation, such as scaled integers. Reject nonfinite values, nonpositive values, and unsupported quantity precision. Define average-cost and closing-position calculations using the same representation; avoid an unrelated floating-point epsilon.

### 2. Atomic transactions alone do not prevent overspending or duplicate trades

**Severity:** High  
**Sections:** 7–9; Section 13 item 20

Manual trades, chat actions, multiple browser tabs, and background snapshots can overlap despite the single-user model. Two requests can both validate against the same cash balance before either writes. A retry after a lost HTTP response can execute a trade twice.

**Suggested resolution:** Agree with item 20’s configurable database path, WAL mode, and per-trade transaction, but require balance and position validation inside the serialized write transaction. Include cash, position, trade, and snapshot changes in that transaction. Add a client-generated request identifier with a uniqueness constraint for trade and chat execution; replay completed results without repeating actions. Do not hold database transactions open during LLM or market-data network calls.

### 3. Price coverage and trade subscription rules are circular

**Severity:** High  
**Sections:** 6, 8, 9; Section 13 items 4, 6, 32

The poller tracks watched tickers, while portfolio valuation needs held tickers too. Trading an unwatched ticker is undefined. Item 6 proposes both rejecting trades without prices and automatically adding traded tickers, without specifying which happens first or whether a rejected trade changes the watchlist.

**Suggested resolution:** Agree with items 4 and 32: track the watchlist union open positions, including on startup. Change item 6 to specify an exact sequence. A simple contract is that users or chat must add a ticker and obtain a usable quote before trading it; a rejected trade makes no watchlist changes. If automatic addition is retained, define its failure and rollback behavior explicitly.

### 4. Massive polling promises exceed the specified API contract

**Severity:** High  
**Sections:** 5, 6; Section 13 items 5, 29

“REST works on all tiers” does not establish access to a suitable price endpoint. At ten tickers, polling each ticker every 15 seconds requires 40 calls per minute. A batch endpoint could reduce calls, but endpoint access still matters: Massive’s full-market snapshot supports ticker filtering, excludes the Basic plan, and provides delayed data on some paid plans. Poll frequency therefore does not establish real-time pricing. [Massive snapshot documentation](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot)

**Suggested resolution:** Change item 29. Either explicitly defer Massive implementation and remove its core acceptance requirements, or specify one supported endpoint and plan, batching, quote timestamps, rate limiting, backoff, and delayed-data labeling. Retain mocked adapter tests if it ships; live-provider E2E need not be required. Do not classify authorization failures, rate limits, or temporary empty responses as invalid symbols under item 5.

### 5. Stale and missing quotes have no execution or valuation policy

**Severity:** High  
**Sections:** 6–9; Section 13 items 6, 16, 17

A quote can remain cached after a provider failure, market closure, or poller crash. A connected SSE stream does not mean its quotes are current. Neither trade execution nor snapshots specify how to handle stale or missing prices, so an agent could fill at an arbitrarily old price or value an unpriced holding at zero.

**Suggested resolution:** Define source timestamp, freshness status, and a source-appropriate maximum execution age. Reject execution without an acceptable quote. Preserve last-known prices for display with a visible stale state; mark valuation incomplete rather than silently substituting zero. Specify whether incomplete snapshots are skipped or explicitly flagged. Keep transport connectivity separate from quote freshness.

### 6. Chat execution can contradict its own conversational message

**Severity:** High  
**Sections:** 9; Section 13 items 11, 12

The LLM writes its message before validation and execution. It may say “Bought 10 TSLA” even when the backend rejects the action. Item 12 correctly identifies that no later LLM call exists, but displaying an error beside a success claim still leaves contradictory output.

Item 11 also leaves action ordering unresolved: trades and watchlist changes live in separate arrays, and the outcome can depend on execution order.

**Suggested resolution:** Agree with independent actions and avoiding a second LLM call, with amendments. Require the model to describe proposed actions without claiming completion. Render backend-generated execution results as authoritative confirmations. Define deterministic ordering, validate each action against state updated by earlier successful actions, and return requested quantity, actual fill price, action status, and error code. Persist those same results.

### 7. Automatic execution lacks a clear authorization boundary

**Severity:** High  
**Sections:** 9; Section 13 items 11, 15

“Suggest trades,” “execute trades when the user asks or agrees,” and proactive watchlist management are not precise enough to distinguish analysis from permission to mutate state. A question such as “What if I bought 10 AAPL?” must not become a purchase merely because it contains a trade phrase.

**Suggested resolution:** Preserve execution without confirmation for explicit trading requests, but define that hypothetical, quoted, analytical, and recommendation requests produce no trades. Define what a later “yes” authorizes. Validate all generated actions server-side, limit action counts, and enforce the same domain rules as manual requests. Change item 15’s mock to anchored command fixtures so it does not teach or test accidental execution of hypothetical requests.

### 8. Restarting the simulator can change persisted portfolio wealth arbitrarily

**Severity:** High  
**Sections:** 6, 7, 11

Positions, cash, and portfolio history persist, but simulated prices exist only in memory and start from seed values. Restarting the container can therefore reset every held asset’s price while preserving its cost basis and historical valuations.

**Suggested resolution:** Persist the simulator’s latest prices and restore them on startup. For simplicity, resume from those prices without simulating elapsed downtime. Define the initial baseline for newly tracked symbols and make account reset a separate, explicit operation.

## Medium-severity findings

### 9. Endpoint descriptions are not sufficient integration contracts

**Severity:** Medium  
**Sections:** 8, 9; Section 13 items 11, 13

Most endpoints specify their purpose but not their response shape. Agents must invent portfolio field names, error envelopes, status codes, timestamp formats, and duplicate-add or missing-delete behavior. The chat request body itself is unspecified.

**Suggested resolution:** Add compact request and response examples for every endpoint and a common error structure. Define nullable prices, numeric serialization, UTC timestamps, collection ordering, and idempotent watchlist behavior. Adopt item 11’s execution-result concept with the amendments above. Change item 13’s blanket HTTP 200 recommendation: configuration and upstream failures should have explicit machine-readable states, using appropriate HTTP errors or a documented failure envelope rather than masquerading as successful assistant replies.

### 10. Persisted conversation history cannot be restored through the API

**Severity:** Medium  
**Sections:** 7–10; Section 13 items 13, 14

The UI promises conversation history and the database stores messages, but there is no read endpoint. Reloading the page may show an empty chat while the model remembers earlier messages. Ordering by timestamps alone also leaves ties ambiguous.

**Suggested resolution:** Add a bounded chat-history endpoint with stable ordering and persisted action results. Agree with item 14’s last-20-message starting point, but also impose a context-size budget and define whether the pending message is included. Store the user message once before inference and retain a visible failure outcome if inference fails. Serialize chat turns or define their concurrent ordering.

### 11. Synchronous LLM examples can block market streaming

**Severity:** Medium  
**Sections:** 3, 6, 9; `.claude/skills/cerebras/SKILL.md`

The referenced skill uses synchronous `completion(...)`. Calling that directly inside an asynchronous FastAPI handler can block the event loop during inference, interrupting SSE and background work.

The specification also leaves worker count unspecified even though the price cache and producer are process-local.

**Suggested resolution:** Require an asynchronous LLM call or explicit thread offloading, with bounded timeouts. Run one Uvicorn worker for this architecture, and start and stop all background tasks through the application lifespan. State that multiple workers or replicas require a different shared-state design.

### 12. The SSE contract does not define bootstrap, freshness, or reconnection behavior

**Severity:** Medium  
**Sections:** 6, 10, 12; Section 13 items 17, 27

Item 17 supplies useful fields but uses an illustrative object rather than valid JSON. It does not say whether events contain all tracked symbols or only changed symbols. The main plan describes regular broadcasts, while the design reference describes version-based change detection.

Repeated unchanged quotes could create fake chart points or repeated price flashes. Reconnecting clients could also wait without receiving their initial valuation.

**Suggested resolution:** Agree with pinning the payload, but specify valid examples, timestamp units, direction values, `change` semantics, and full-snapshot versus delta behavior. Send a current snapshot immediately on connection, then publish changed quotes; use heartbeats separately. Define no replay requirement if reconnect always bootstraps current state. Specify when reconnecting becomes disconnected.

### 13. Live valuation rules do not cover synchronization between clients

**Severity:** Medium  
**Sections:** 8, 10; Section 13 items 16, 24

Client-side valuation from SSE is reasonable, but “refetch after every action” covers only actions originating in that browser. Another tab can change cash or holdings without notifying it. Removing prices from the watchlist response also requires a reliable SSE bootstrap.

**Suggested resolution:** Agree with item 16’s client-side calculation and item 24’s lean watchlist response once the SSE bootstrap is defined. Add a simple portfolio refresh on window focus and a modest polling interval, or explicitly constrain the supported experience to one active tab. Define that cached holdings remain provisional until the portfolio refresh completes.

### 14. P&L and visualization metrics have multiple plausible meanings

**Severity:** Medium  
**Sections:** 2, 7, 8, 10; Section 13 items 7, 9

The “P&L chart” actually stores total account value. “% change” could mean session price movement or unrealized return. Treemap weight could include cash or only invested assets, and color could encode absolute profit or percentage return.

**Suggested resolution:** Define formulas and labels explicitly:

- Account value = cash + marked value of holdings.
- Unrealized P&L = quantity × (current price − average cost).
- Position return = unrealized P&L ÷ position cost basis.
- Total account P&L = account value − initial funding, assuming no deposits or withdrawals.

Agree with item 9’s zero-position deletion and unchanged average cost on partial sales. Omitting a separately stored realized-P&L field is reasonable. Agree with item 7’s session-change simplification, but choose one baseline—preferably first observed client price—and label it consistently. Specify treemap sizing, color metric, cash handling, and empty state.

### 15. Portfolio and frontend history need bounded, deterministic behavior

**Severity:** Medium  
**Sections:** 6, 7, 10; Section 13 items 18, 21

Accumulating every frontend tick indefinitely grows memory. “Last ~500 points, or downsample” leaves both implementation and chart time horizon undefined. At 30-second intervals, 500 consecutive points cover only about four hours.

There is also no initial snapshot, so the fresh-start chart may remain empty until a timer fires.

**Suggested resolution:** Agree with item 18’s session-only main chart and defer the backend chart-history endpoint. Specify a bounded frontend ring buffer and how same-timestamp updates are handled. Amend item 21 to an exact query contract, such as the latest 500 snapshots returned chronologically, with the UI labeling that window. Seed an initial snapshot. Unlimited database retention is acceptable for this local demo if explicitly documented.

### 16. Symbol acceptance and simulator reproducibility are underspecified

**Severity:** Medium  
**Sections:** 6, 8, 12; Section 13 item 5

Accepting arbitrary symbols is reasonable for a simulator, but silently assigning a new random seed price on each subscription can change an asset’s value after removal and re-addition. A one-to-five-letter rule is a product restriction rather than a general stock-symbol validator.

The plan also does not define GBM time units, parameter units, or a repeatable random source.

**Suggested resolution:** Change item 5 to explicitly describe synthetic symbol support. Normalize and validate using a documented restricted grammar; display unknown symbols as synthetic. Assign stable initial parameters per symbol and retain its last price within the chosen persistence policy. Define the simulator timestep and parameter units, plus a configurable random seed or deterministic test source. Do not infer symbol validity from temporary provider data absence.

### 17. LLM failure and routing guarantees need tightening

**Severity:** Medium  
**Sections:** 5, 9; Section 13 items 13, 19; `.claude/skills/cerebras/SKILL.md`

The plan says Cerebras is the inference provider, but the skill only prioritizes it with `provider.order`. OpenRouter allows fallback unless disabled, so this does not guarantee Cerebras-only execution. [OpenRouter provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)

Structured output also needs local semantic validation regardless of provider support.

**Suggested resolution:** Decide whether Cerebras is preferred or required. If required, explicitly disable fallback and return a clear unavailable result when it cannot serve the request. Validate the complete response before executing any action. Agree with item 19: the application must start without an LLM key, and mock mode must bypass credentials. Keep item 13’s bounded timeout, but define handling for refusal, truncation, malformed output, and invalid actions. Do not automatically repeat execution after partial completion.

### 18. Database startup and schema evolution remain ambiguous

**Severity:** Medium  
**Sections:** 4, 7; Section 13 items 10, 20, 30, 31

The plan alternates between first-request and startup initialization. Creating missing tables is not enough to distinguish a fresh database from an existing database needing a schema change. Seeding whenever tables are empty could restore deliberately removed watchlist entries.

**Suggested resolution:** Agree with item 30: initialize once in the lifespan handler. Seed defaults only for a newly created account, not an intentionally empty watchlist. Record a schema version and define a minimal incompatible-version policy. Agree with item 10’s clarification that `users_profile.id` is the user identifier and item 20’s configurable path. Item 31’s `backend/app/db/` location is reasonable; use an absolute resolved runtime database path to avoid dependence on the working directory.

### 19. The volume and launch instructions describe different persistence mechanisms

**Severity:** Medium  
**Sections:** 2, 4, 5, 11; Section 13 items 19, 26, 33

The example uses a named Docker volume, but the prose says the project’s `db/` directory maps into the container. Those are different arrangements. Startup also requires `--env-file .env` even though the simulator should run without credentials. A raw Docker command does not itself open the host browser.

**Suggested resolution:** Choose the named volume as the default and correct the directory description. Make an environment file optional, keep secrets out of image build inputs, and specify container naming, detached execution, readiness waiting, and script behavior when already running. Agree with dropping optional Compose under item 26. Amend item 33: browser opening belongs to platform scripts after readiness, with an opt-out and documented Linux/Windows behavior.

### 20. No-auth local use conflicts with unrestricted network and cloud deployment

**Severity:** Medium  
**Sections:** 2, 3, 11

The app intentionally has no authentication, but the Docker example publishes port 8000 without restricting the host interface. Any reachable client can mutate the shared portfolio and trigger requests charged to the configured LLM account. “Designed to deploy” to arbitrary container platforms also overlooks persistent-storage and single-process assumptions.

**Suggested resolution:** Bind the default host mapping to `127.0.0.1:8000:8000` and define the supported core deployment as a local, trusted workstation. Remove the general cloud-readiness claim or explicitly defer authentication, storage adaptation, and replica coordination to that stretch scope.

### 21. The proposed testing simplification removes useful behavioral coverage

**Severity:** Medium  
**Sections:** 12; Section 13 items 15, 27, 28, 29

Host-run Playwright is a sound simplification. However, a status-dot unit test does not demonstrate that prices resume after an interrupted stream. Mocking the LLM alone also does not make price-dependent tests deterministic, and persistent test volumes can leak state between scenarios.

**Suggested resolution:** Agree with host-run Playwright and trimming generic rendering tests. Change item 27’s recommendation to remove reconnection coverage: retain one controlled disconnect/reconnect integration test that asserts resumed updates. Use isolated databases and deterministic price fixtures for accounting tests. Keep focused tests for concurrent buys, retry deduplication, stale prices, rounding boundaries, partial chat failures, and restart persistence. If Massive ships, retain mocked transport and failure tests.

## Low-severity findings

### 22. Charting simplification introduces unnecessary custom algorithms

**Severity:** Low  
**Sections:** 6, 10; Section 13 item 23

Item 23 correctly identifies that Recharts is SVG-based, contradicting the canvas preference. However, writing a squarify algorithm adds custom layout code and edge cases solely to avoid a dependency. The correlated GBM design reference similarly introduces mathematical complexity that the demo may not need.

**Suggested resolution:** Partially agree with item 23: select one main charting library and use simple SVG sparklines. Use a maintained treemap implementation or explicitly accept a simpler proportional layout rather than requiring custom squarification. For correlated prices, consider a shared market/sector shock plus ticker-specific noise instead of a dynamically managed correlation matrix. Treat the summary’s module count and historical test counts as nonbinding reference information.

### 23. The build stage retains an obsolete runtime and weak lockfile instructions

**Severity:** Low  
**Sections:** 3, 11; Section 13 item 3

Node 20 is still specified even though item 3 identifies its end of life. The official release schedule lists its EOL as April 30, 2026. `npm install` and unqualified `uv sync` also leave reproducibility weaker than the stated rationale. [Node.js release schedule](https://github.com/nodejs/Release#release-schedule)

**Suggested resolution:** Agree with item 3 and choose one supported major, such as Node 24, rather than leaving alternatives open. Require committed dependency lockfiles, `npm ci`, and frozen Python dependency synchronization for image builds.

### 24. Accessibility and practical completion criteria are missing

**Severity:** Low  
**Sections:** 2, 10, 12

“Visually stunning,” “functional on tablet,” and “production-quality” are subjective. There are no measurable requirements for keyboard operation, chart alternatives, reduced motion, or distinguishing gains and losses without color.

**Suggested resolution:** Add a short acceptance checklist covering keyboard-accessible ticker selection and trading, labeled inputs, visible focus, textual action errors, reduced-motion price flashes, non-color gain/loss indicators, chart summaries, and one defined tablet viewport. Include no-position, no-price, loading, and provider-error states.

### 25. Section 13 is still a competing specification rather than a decision record

**Severity:** Low  
**Sections:** 3–13; Section 13 items 1, 2, 22, 25

Agents must reconcile normative text with unaccepted suggestions that contradict it. For example, database initialization, watchlist response contents, charting, and testing infrastructure currently have competing descriptions.

Items 1 and 2 are resolved consistently with the local documentation: this is a rebuild, and the `cerebras` skill exists. Other sound housekeeping suggestions remain unapplied.

**Suggested resolution:** Fold accepted decisions into Sections 3–12 before implementation and move unresolved decisions into an explicitly nonnormative list. Agree with item 22’s API-before-static mounting order; additionally ensure unknown `/api/*` requests return API errors rather than frontend content. Agree with item 25’s composite keys for watchlists and positions. Keep resolved items 1 and 2 closed, and state that the plan takes precedence over historical design references.

## Findings by severity

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 8 |
| Medium | 13 |
| Low | 4 |
| **Total** | **25** |