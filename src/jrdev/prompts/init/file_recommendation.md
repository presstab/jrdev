Respond only with a list of files in the format get_files ['path/to/file.cpp', 'path/to/file2.json', ...] etc. 
Do not include any other text or communication.

# File Structure Analysis Guide

This document outlines the methodology for identifying critical files in a codebase based on observed patterns and standard development practices.

__Objective:__ Identify a maximum of 20 critical files that reveal core functionality, architectural patterns, and entry points. Prioritize files that provide maximum insight into how the system works.

## 1. Priority Guidelines

### High Priority Targets
- __Entry Points:__ 
    - Language-specific main files (`main.py`, `index.js`, `App.tsx`)
    - Framework initialization files (`AppConfig.java`, `startup.cs`)
    - Examples: `src/main.tsx`, `app/Application.java`
- __Core Implementation:__
    - Files containing primary business logic
    - Pattern-matching names: `*service.*`, `*core.*`, `*manager.*`
- __Architectural Foundations:__
    - Dependency injection configurations
    - Routing definitions (`routes.ts`, `web.php`)
    - State management setups (`store.js`, `redux/`)
- __Documentation:__
    - Active `README.md` files with structural explanations
    - Architectural decision records (`adr/` directory)

### Medium Priority Targets
- __Configuration:__
    - Build process files (`webpack.config.js`, `CMakeLists.txt`)
    - Environment setups (`.env.*`, `config/`)
- __Testing:__
    - Comprehensive test suites (`*spec.js`, `*test.py`)
    - Integration test directories (`tests/e2e/`)
- __Utilities:__
    - Widely-reused helper modules (`utils/`, `helpers/`)
    - Shared constants files (`constants.js`, `Settings.cs`)

### Low Priority/Ignore
- __Boilerplate:__
    - Framework-generated files (`angular.json`, `package-lock.json`)
    - IDE configurations (`.vscode/`, `.idea/`)
- __Assets:__
    - Media files (`images/`, `fonts/`)
    - Compiled resources (`dist/`, `build/`)
- __Third-party:__
    - Vendor dependencies (`node_modules/`, `venv/`)
    - License files (`LICENSE`, `NOTICE`)

## 2. Analysis Process

1. __Language Identification__
    - Examine file extensions (`*.tsx`, `*.java`, `*.go`)
    - Check for manifest files (`package.json`, `requirements.txt`)
    - Identify framework-specific patterns (`@Component` decorators, `SpringApplication`)

2. __Entry Point Discovery__
    - Follow language conventions:
        - Python: `__main__.py`, files with `if __name__ == "__main__"`
        - JavaScript: `index.js`, Webpack entry points
        - Java: `main()` method declarations
    - Search for common patterns:
        ```javascript
        // React entry pattern
        ReactDOM.render(
          ,
          document.getElementById('root')
        );
        ```

3. __Architectural Analysis__
    - Identify infrastructure patterns:
        - Dependency injection: `container.ts`, `ApplicationContext.java`
        - API routing: `routes/`, `app/Http/Controllers/`
    - Detect layered architecture:
        ```plaintext
        src/
        ├── presentation/
        ├── application/
        └── domain/
        ```