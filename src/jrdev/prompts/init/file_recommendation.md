Respond only with a list of files in the format get_files ['path/to/file.cpp', 'path/to/file2.json', ...] etc. 
Do not include any other text or communication.

File Structure Analysis Guide

This document guides the selection of critical files based *only* on the file tree structure.
No file content is available at this stage, so analysis relies on naming conventions and directory layout.

__Objective:__ Identify a maximum of 20 critical files based on their names and locations in the file tree.
Prioritize files likely to contain entry points, core logic, configuration, or architectural elements based on common practices.

## 1. Priority Guidelines

These files/directories often indicate key parts of an application, even without seeing the content.
### High Priority Targets
- __Entry Points:__ 
    Look for standard main files or framework-specific startup files, often at the root or in `src`/`app`.
    - Common names are: `main.py`, `__main__.py`, `index.js`, `index.ts`, `server.js`, `server.ts`, `app.js`, `app.ts`, `App.tsx`, `App.jsx`, `Program.cs`, `Startup.cs`, `Application.java`, `manage.py`, `wsgi.py`, `asgi.py`, ...
    - Framework initialization files: `AppConfig.java`, `startup.cs`, `nuxt.config.js`, ...
    - Examples: `src/main.tsx`, `app/Application.java`, `cmd/server/main.go`, ...
- __Core Implementation:__
    Look for files/directories suggesting core business logic through naming conventions.
    - Pattern-matching names: `*service.*`, `*core.*`, `*manager.*`, `*controller.*`, `*handler.*`, `*model.*`, `*domain.*`, `*repository.*`, `*provider.*`, ...
    - Common directories: `src/core/`, `app/services/`, `lib/`, `pkg/`, ...
- __Architectural Foundations:__
    Identify potential configuration or setup files based on common names/directories.
    - Routing definitions: `routes.ts`, `web.php`, `urls.py`, `api.py`, `routes/`, `controllers/`, `routers/`, ...
    - State management setups: `store.js`, `store.ts`, `rootReducer.js`, `store/`, `redux/`, `vuex/`, ...
    - Dependency injection/config: `container.*`, `services.*`, `config.*`, `settings.*`, `application.*`, `bootstrap.*`, `config/`, `app/config/`, ...
- __Key Documentation:__
    READMEs in important locations can give context. ADRs document architectural choices.
    - `README.md` (especially root, `/src`, `/app`)
    - Architectural decision records: `adr/`, `docs/adr/`

### Medium Priority Targets
These files are important but often secondary to the core logic or entry points.
- __Configuration & Build:__
    Build process files and environment settings are crucial for understanding setup.
    - Build process files: `webpack.config.js`, `vite.config.js`, `CMakeLists.txt`, `Makefile`, `pom.xml`, `build.gradle`, `*.csproj`, `*.sln`, `package.json`, `composer.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, ...
    - Environment setups (by name/dir): `.env*`, `config/`, `settings/`, `docker-compose.yml`, `Dockerfile`, ...
- __Utilities:__
    Reusable code is important, often found in dedicated directories.
    - Common directories: `utils/`, `helpers/`, `shared/`, `common/`, `lib/`, ... (if not core)
    - Shared constants: `constants.*`, `config.*`, `settings.*`, ... (if not high priority config)
- __Testing:__
    Test files indicate quality practices but are less critical for understanding *what* the app does initially.
    - Common test directories: `test/`, `tests/`, `spec/`, `__tests__/`, `e2e/`, ...
    - Pattern-matching names: `*test.*`, `*spec.*`, ...

### Low Priority/Ignore
These files usually don't contain core logic or are environment-specific/generated.
- __Boilerplate & Generated:__
    Framework config/lock files, IDE settings - less important for core understanding.
    - Framework/tooling files: `angular.json`, `package-lock.json`, `yarn.lock`, `composer.lock`, `.gitignore`, `.dockerignore`, ...
    - IDE configurations: `.vscode/`, `.idea/`, `.project`, `.settings/`, ....
- __Assets & Resources:__
    Non-code files.
    - Media files: `images/`, `fonts/`, `assets/`, `public/`, ...
    - Compiled/built output: `dist/`, `build/`, `out/`, `target/`, `bin/`, ...
- __Third-party Dependencies:__
    Code not part of the project itself.
    - Vendor dependencies: `node_modules/`, `venv/`, `vendor/`, `Pods/`, ...
    - License/Notice files: `LICENSE`, `NOTICE`, `COPYING`, ...
    
---

## 2. Analysis Process

1. __Language/Framework Identification__
    Infer primary languages/frameworks from file extensions and manifest files.
    - Examine common file extensions: `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.py`, `*.java`, `*.go`, `*.cs`, `*.php`, `*.rb`, ...
    - Check for manifest/build files: `package.json`, `requirements.txt`, `pom.xml`, `build.gradle`, `*.csproj`, `composer.json`, `go.mod`, `Gemfile`, ...
    Note: Cannot reliably identify frameworks just from tree, but file names might give clues (e.g., `next.config.js`, `nuxt.config.js`, ...).

2. __Entry Point Discovery__
    Look for standard entry point filenames in likely locations.
    - Check root directory, `src/`, `app/`, `cmd/*/` for files listed in "High Priority Targets > Entry Points".

3. __Architectural Analysis__
    - Identify infrastructure patterns:
        - Dependency injection: `container.ts`, `ApplicationContext.java`
        - API routing: `routes/`, `app/Http/Controllers/`
    - Detect layered architecture:
        ```plaintext
        Example structure hint
        src/
        ├── api/ or presentation/ or controllers/
        ├── application/ or services/ or use_cases/
        └── domain/ or core/ or models/
        └── infrastructure/ or db/ or data/
        ```
    Identify files matching patterns in "High Priority Targets > Core Implementation" and "Architectural Foundations".

## Summary: Choose up to 20 files balancing coverage across entry points, potential core logic, configuration, and structure. Prioritize based on the High/Medium lists, using naming and location as the primary guides.