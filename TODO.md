# Green Bean Action Tracker (`TODO.md`)

> **Actionable execution checklist tracking Phase 1 through Phase 5.**

---

## Phase 1: Brand Ingress & Foundation Scaffolding
- [x] Initialize Git repository and multi-remote sync (`pushall` with GitHub, QNAP NAS, VPS Offsite)
- [x] Configure toolchain with Python >= 3.12 and `uv`
- [x] Configure `pyproject.toml` with `django`, `whitenoise`, and `django-environ`
- [x] Scaffold directory structure (`config/`, `apps/core/`, `static/`, `templates/`, `tests/`, `docs/`)
- [x] Implement settings module with `apps/` in `sys.path`
- [x] Configure namespaced session and CSRF cookies (`greenbean_sessionid`, `greenbean_csrftoken`)
- [x] Set session engine to signed cookies (`django.contrib.sessions.backends.signed_cookies`)
- [x] Configure WhiteNoise static asset delivery with compression and caching
- [x] Implement `static/css/brand.css` with exact brand color tokens
- [x] Provision brand logo medallion at `static/img/logo.png`
- [x] Build base and splash templates with centered medallion and status badges
- [x] Create automated test suite (`tests/test_settings.py`, `tests/test_views.py`)
- [x] Author comprehensive documentation suite (`README.md`, `ARCHITECTURE.md`, `DEVELOPER_GUIDE.md`, `ROADMAP.md`, `AGENT.md`)
- [x] Execute and verify test suite with 100% passing tests and zero warnings

---

## Phase 2: Multi-Form Coffee Catalog Engine
- [x] Scaffold `apps/catalog` application module
- [x] Implement `GreenCoffeeLot` data model with origin terroir, processing method, and harvest date
- [x] Implement `RoastProfile` data model with roast curve notes and temperature metrics
- [x] Implement `CoffeeProduct` and `ProductVariant` models (bag sizes: 12oz, 2lb, 5lb; grind formulations)
- [x] Create catalog administration views for roasters and batch management
- [x] Build consumer catalog listing and coffee detail pages
- [x] Add unit tests for catalog model constraints and inventory decrement logic

---

## Phase 3: Digital Ordering & Curbside Arrival Telemetry
- [x] Scaffold `apps/orders` and `apps/telemetry` modules
- [x] Implement cart session persistence and order creation workflow
- [x] Implement order lifecycle state machine (`PLACED`, `PREPARING`, `EN_ROUTE`, `ARRIVED_CURBSIDE`, `COMPLETED`)
- [x] Build real-time Barista Kitchen Display System (KDS) dashboard
- [x] Implement privacy-preserving curbside proximity handshake:
  - Ephemeral HMAC-signed arrival tokens
  - Zero-storage client geofence proximity trigger
  - Barista vehicle/spot notification alerts
- [x] Write integration tests for order checkout and arrival telemetry triggers
- [x] Implement idempotent seed_roastery command and active KDS test fixtures

---

## Phase 4: In-Shop POS & Financial Ledger Integration (`iyou_bean`)
- [ ] Build touch-optimized counter POS interface for in-shop baristas
- [ ] Implement receipt printing and cash drawer hardware integration
- [ ] Scaffold `apps/adapters/iyou_bean` ledger bridge
- [ ] Build double-entry transaction batching and sync runner
- [ ] Add COGS inventory depletion accounting sync
- [ ] Write automated tests for ledger balance reconciliation

---

## Phase 5: Democratic Governance & Mesh Federation (`iyou_poly` & `iyou_coop`)
- [ ] Scaffold `apps/adapters/iyou_poly` democratic patronage engine
- [ ] Ingest labor-hour logs and calculate quarterly member dividend allocations
- [ ] Build worker equity dashboard
- [ ] Scaffold `apps/adapters/iyou_coop` federation gateway
- [ ] Expose `/.well-known/coop-manifest.json` discovery endpoint
- [ ] Implement inter-roaster guest coffee exchange registry
- [ ] Write automated verification tests for federation manifest schemas
