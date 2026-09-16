# AGENT.md — Rules of Engagement & System Invariants for `greenbean_dotapp`

This document binds every AI/IDE code agent operating in `greenbean_dotapp`. It represents the hard technical ground truth for the repository. Deviations require explicit human architectural waiver.

---

## 1. Mandatory Execution Invariant: Auto-Commit on Verification

1. **Asking to Commit Is a HARD FAILURE:** NEVER end a task with "Would you like me to commit?", "Should I commit?", "Ready to commit?", or any equivalent question.
2. **Commit Immediately — No Exceptions:** The moment your task is complete and passes all verification gates, stage it (`git add <files>`) and commit it (`git commit`) in this repository. Do not leave the working tree dirty.
3. **Conventional Commit Message:** Use strict conventional commit syntax:
   - `feat:` for new capabilities or domain components
   - `fix:` for bug fixes
   - `refactor:` for internal structure improvements
   - `test:` for test additions or updates
   - `docs:` for documentation updates
   - `chore:` for maintenance, toolchain, or dependency updates
4. **Final Status Output:** Every final handoff report MUST end with the outputs of:
   - `git log -n 1 --oneline`
   - `git status --short`
5. **No Question-Containing Final Lines:** Any report whose final line is an open-ended question is a failed handoff.

---

## 2. Hard Architectural Invariants

1. **Cookie Namespacing & Scoping**:
   - `SESSION_COOKIE_NAME = "greenbean_sessionid"` (strictly locked)
   - `CSRF_COOKIE_NAME = "greenbean_csrftoken"` (strictly locked)
   - Never rename, alter, or share cookie identifiers with sibling ecosystem applications.
2. **Stateless Session Engine**:
   - `SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"`.
   - Never introduce database-backed session tables unless explicitly mandated by an architectural decision record.
3. **Universal UUID Primary Keys**:
   - All models in `apps/` must use UUID primary keys:
     ```python
     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
     ```
   - Never introduce auto-incrementing integer primary keys.
4. **Privacy-Preserving Telemetry**:
   - Curbside arrival signals must rely on ephemeral, tokenized proximity handshakes.
   - Under no circumstances may customer GPS coordinates (latitude/longitude) be persisted to the database.
5. **Brand Color Fidelity**:
   - Always reference brand tokens from `static/css/brand.css`:
     - `--clr-leaf-green: #80A629;` (Canvas & Primary Hero)
     - `--clr-roast-brown: #472F18;` (Outer Rim & Deep Contrast)
     - `--clr-brick-red: #9D2E16;` (Accent Buttons & "BEAN" Typography)
     - `--clr-pure-white: #FFFFFF;` (Medallion Background & Cards)
     - `--clr-canvas-dark: #12180B;` (Dark mode backing)
   - Never hard-code arbitrary local hex colors into templates or CSS.
6. **Decoupled Application Layout**:
   - App modules reside inside `apps/<app_name>/`.
   - `apps/` is registered in `sys.path` within `config/settings.py`.
   - Business logic must reside in service classes (`apps/<app_name>/services/`), keeping views and models concise.
7. **Multi-Remote Synchronization**:
   - Distributed production upstream is mapped through `pushall`:
     - GitHub: `git@github.com:dcbyers13/greenbean_dotapp`
     - QNAP NAS: `ssh://iyou@qnap:/share/homes/iyou/repos/greenbean_dotapp.git`
     - VPS Edge Offsite: `vps-offsite-backup:/home/gitbackup/greenbean_dotapp.git`

---

## 3. Quality Gates (Mandatory Before Completion)

Every code modification must pass the following quality gates with **zero warnings and zero errors**:

```bash
# 1. Django system check
uv run python manage.py check

# 2. Automated test suite execution
uv run python manage.py test tests
```

---

## 4. Source Tree Boundaries

- Never commit virtual environments (`.venv/`), compiled Python artifacts (`__pycache__/`, `*.pyc`), SQLite databases (`db.sqlite3`), or collected static files (`staticfiles/`).
- Verify `.gitignore` covers all transient files before committing.
