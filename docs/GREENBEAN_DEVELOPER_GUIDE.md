# Green Bean Developer Guide

> **Welcome to the Green Bean Engineering Team.**  
> This guide details environment configuration, coding standards, design tokens, test suites, and delivery protocols for `greenbean_dotapp`.

---

## 1. Developer Onboarding & Environment Setup

### 1.1 Toolchain Prerequisites
- **Python**: `>= 3.12`
- **Package & Runtime Manager**: [`uv`](https://docs.astral.sh/uv/) (v0.5+)
- **Git**: Configured with proper author info and SSH keys.

### 1.2 Local Setup Walkthrough
```bash
# 1. Clone repository
git clone git@github.com:dcbyers13/greenbean_dotapp.git
cd greenbean_dotapp

# 2. Synchronize environment and install dependencies
uv sync

# 3. Provision local environment file
cp .env.example .env

# 4. Run database migrations
uv run python manage.py migrate

# 5. Verify local test suite execution
uv run python manage.py test tests

# 6. Boot the local development server
uv run python manage.py runserver 127.0.0.1:8000
```

---

## 2. Environment Configuration & Variables

Configuration is managed via `django-environ` reading from environment variables or a local `.env` file located at the project root.

| Variable Name | Type | Default Value | Description / Production Guidance |
| :--- | :--- | :--- | :--- |
| `DEBUG` | `bool` | `False` | Set to `True` strictly during local feature development. Must be `False` in production. |
| `SECRET_KEY` | `str` | `django-insecure-...` | Cryptographic signing key. In production, provide a minimum 50-character random string. |
| `ALLOWED_HOSTS`| `list` | `localhost,127.0.0.1,greenbean.app,*.greenbean.app` | Comma-delimited list of valid HTTP Host headers. |
| `DATABASE_URL` | `str` | `sqlite:///db.sqlite3` | Database connection URL. Supports PostgreSQL: `postgres://user:pass@host:5432/dbname`. |

### Security Invariants
- **Never Commit Secrets**: Never commit `.env` or any production credential into source control.
- **Namespaced Session Cookies**: Do not change `SESSION_COOKIE_NAME` (`greenbean_sessionid`) or `CSRF_COOKIE_NAME` (`greenbean_csrftoken`).

---

## 3. Brand Identity & Design System

The visual design system of Green Bean reflects its roots: organic, grounded, artisanal, and anti-corporate. All styles are declared as standard CSS custom properties in `static/css/brand.css`.

### 3.1 Brand Color Tokens

```css
:root {
  /* Brand Core Tokens */
  --clr-leaf-green: #80A629;   /* Canvas & Primary Hero */
  --clr-roast-brown: #472F18;  /* Outer Rim & Deep Contrast */
  --clr-brick-red: #9D2E16;    /* Accent Buttons & "BEAN" Typography */
  --clr-pure-white: #FFFFFF;   /* Medallion Background & Cards */
  --clr-canvas-dark: #12180B;  /* Dark mode backing */
}
```

### 3.2 Token Semantics & Usage Matrix

| Token Name | Hex Code | Visual Role & Usage Guidelines |
| :--- | :--- | :--- |
| `--clr-leaf-green` | `#80A629` | **Primary Brand Hero & Canvas**. Represents unroasted green coffee and cooperative life. Used for subtle radial hero backgrounds, borders, and active status indicators. |
| `--clr-roast-brown` | `#472F18` | **Deep Roast & High Contrast**. Represents small-batch artisanal roasting. Used for the medallion outer rim border, headings, primary typography, and footer text. |
| `--clr-brick-red` | `#9D2E16` | **Accent & Call-to-Action**. Represents the bold "BEAN" lettering in the logo and coffee cherry ripeness. Used for primary CTA buttons, highlighted links, and badges. |
| `--clr-pure-white` | `#FFFFFF` | **Medallion & Surface Elevation**. Clean crisp background for the centered brand medallion circle and content cards. |
| `--clr-canvas-dark` | `#12180B` | **Deep Contrast Dark Backing**. Grounding dark tone used for the site footer, dark mode backgrounds, and deep badge text. |

### 3.3 Medallion Presentation Guidelines
- The brand medallion (`static/img/logo.png`) must always be rendered within a circular white elevation frame with a 4px `--clr-roast-brown` border.
- The medallion requires a layered elevation shadow (`var(--shadow-medallion)`) that expands smoothly on hover.
- Never distort, stretch, or alter the color hues of the medallion artwork.

---

## 4. Testing & Verification Suites

Every contribution must pass the verification suites without warnings or regressions before being pushed.

### 4.1 Running Tests
```bash
# Execute entire test suite
uv run python manage.py test tests

# Execute specific test modules
uv run python manage.py test tests.test_settings
uv run python manage.py test tests.test_views
```

### 4.2 Test Standards
1. **Zero Warnings Policy**: All tests must complete with zero Python or Django runtime warnings.
2. **Deterministic & Fast**: Unit tests must rely on `SimpleTestCase` whenever database access is unnecessary to ensure sub-second feedback loops.
3. **Template Verification**: All views must verify status code, template resolution, and key contextual/brand markers.

---

## 5. Deployment & Multi-Remote Sync

Push verified branches to all mirrors via the `pushall` composite remote:

```bash
git push pushall main
```

Endpoints updated simultaneously:
1. **GitHub Primary**: `git@github.com:dcbyers13/greenbean_dotapp`
2. **QNAP On-Premise NAS**: `ssh://iyou@qnap:/share/homes/iyou/repos/greenbean_dotapp.git`
3. **VPS Edge Offsite**: `vps-offsite-backup:/home/gitbackup/greenbean_dotapp.git`
