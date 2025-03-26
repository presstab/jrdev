# Prompt: Generate Codebase Conventions and Patterns Document

**Objective:** Analyze the provided codebase files and generate a comprehensive document. This document should meticulously detail the OBSERVED conventions, patterns, and practices employed within the code. The primary goal is to create a clear and actionable guide for current and future developers to ensure consistency and maintainability. DO NOT infer conventions that are not present in the provided files.

**Instructions:**

1.  **Analyze Thoroughly:** Examine all provided code files to identify recurring patterns and established conventions. Infer these conventions even if not explicitly stated in comments or existing documentation.
2.  **Structure the Output:** Use Markdown formatting effectively. Employ clear headers (`##`, `###`), bullet points (`*` or `-`), bold text (`**`), inline code (` `` `), and code blocks (``` ```) for specific examples extracted directly from the provided codebase.
3.  **Be Language-Agnostic:** While drawing specific examples from the code, describe the conventions in general terms where possible, avoiding excessive reliance on language-specific jargon unless essential to illustrate a point.
4.  **Provide Concrete Examples:** For each identified convention or pattern, include short, relevant code snippets *from the provided files* to illustrate the point clearly.
5.  **Focus on Actionable Guidance:** Frame the descriptions in a way that helps a developer understand *how* to write new code that fits the existing style.

**Output Structure:**

Please structure your response following this Markdown outline:

~~~~markdown
# Codebase Conventions and Patterns Guide

This document outlines the established conventions and patterns observed in the codebase. Adhering to these guidelines helps maintain consistency, readability, and maintainability.

## 1. Language & Environment

*   **Primary Language(s):** [Identify the main programming language(s) used]
*   **Key Frameworks/Runtimes:** [List major frameworks (e.g., React, Spring, .NET, Node.js) or runtimes]
*   **Package/Module System:**
    *   Describe the system used for organizing and sharing code (e.g., ES Modules, CommonJS, Java packages, Python modules, namespaces).
    *   Provide examples of import/export or include/using statements.


## 2. Naming Conventions

*   **File Naming:**
    *   Convention used (e.g., `kebab-case.js`, `PascalCase.cs`, `snake_case.py`).
    *   Patterns for specific file types (e.g., `*.component.ts`, `*_test.py`, `IInterfaceName.java`).
    *   Examples: `user-profile.component.jsx`, `AuthService.java`, `database_connection.py`
*   **Variables:** Convention used (e.g., `camelCase`, `snake_case`, `PascalCase` for constants). Examples.
*   **Functions/Methods:** Convention used (e.g., `camelCase`, `snake_case`, `PascalCase` for constructors). Examples.
*   **Classes/Interfaces/Types:** Convention used (e.g., `PascalCase`, prefix `I` for interfaces). Examples.
*   **Constants:** Convention used (e.g., `UPPER_SNAKE_CASE`). Examples.
*   **Other (if applicable):** Conventions for enums, modules, packages, etc.

## 3. Code Structure & Organization

*   **Intra-file Organization:**
    *   Standard order of elements (e.g., imports, constants, class definition, methods, private functions).
    *   Use of regions, markers, or comments for sectioning.
*   **Import/Include Ordering:**
    *   Grouping conventions (e.g., external libs, internal modules, relative paths).
    *   Sorting conventions (e.g., alphabetical).
    *   Example:
        ```[lang]
        // External dependencies
        import React from 'react';
        import _ from 'lodash';

        // Internal absolute paths
        import { AuthService } from 'src/services/auth';
        import { Button } from 'src/components';

        // Relative paths
        import { helperFunction } from './utils';
        ```

## 4. Programming Paradigms & Design Patterns

*   **Primary Paradigm(s):** Is the code predominantly Object-Oriented, Functional, Procedural, or a mix?
*   **Common Design Patterns:** Identify recurring patterns (e.g., Singleton, Factory, Repository, Middleware, MVC/MVVM). Where are they typically used?
*   **Immutability:** Is immutability preferred? Where and how is it enforced?
*   **Code Reusability:** How is code reuse achieved (e.g., inheritance, composition, utility functions, hooks)?

## 5. Type System (If Applicable)

*   **Static vs. Dynamic:** Is a static type system used (e.g., TypeScript, Java, C#, Flow, MyPy)? Or is it primarily dynamic?
*   **Type Declaration:** How are types specified? (e.g., type hints, interfaces, annotations, JSDoc). Provide examples.
*   **Type Usage:** Where are types most rigorously applied (e.g., function signatures, data structures, API boundaries)?

## 6. Error Handling

*   **Mechanism:** How are errors typically handled? (e.g., exceptions/try-catch, error codes, specific return types like `Result`/`Option`, dedicated error objects).
*   **Error Types:** Are custom error classes/types used? How are they structured?
*   **Propagation:** How are errors propagated up the call stack?
*   **Logging/Reporting:** How and where are errors logged or reported? Examples.

## 7. Asynchronous Programming

*   **Patterns Used:** Identify the primary methods for handling async operations (e.g., `async/await`, Promises, Futures, Callbacks, Threads, Goroutines, Event Loops).
*   **Concurrency/Parallelism:** Are there specific patterns for managing concurrent or parallel execution?
*   **Common Use Cases:** Where are async patterns most prevalent (e.g., I/O, API calls, background tasks)?

## 8. State Management (If Applicable)

*   **Approach:** How is application state managed (e.g., global state stores like Redux/Vuex/Context API, service-based state, local component state, database as source of truth)?
*   **Scope:** Conventions for deciding between global vs. local state.
*   **State Mutation:** How is state updated (e.g., reducers, setters, direct mutation)?

## 9. API/Interface Design (If Applicable)

*   **Style:** Conventions for designing internal or external APIs (e.g., RESTful principles, GraphQL schema design, gRPC service definitions, function signatures).
*   **Data Formats:** Standard request/response formats (e.g., JSON structure, status codes, error formats).
*   **Versioning:** How are APIs versioned, if at all?

## 10. Documentation & Comments

*   **Code Comments:**
    *   Style used (`//`, `#`, `/* */`, docblocks).
    *   When are comments typically used (e.g., explaining complex logic, documenting public APIs, TODOs)?
    *   Format for docblocks (e.g., JSDoc, TSDoc, XML-Doc). Examples.
*   **External Documentation:** Is there a system for generating documentation from code comments (e.g., Sphinx, Javadoc, TypeDoc)?

## 11. Testing

*   **Frameworks/Libraries:** Identify testing tools used (e.g., Jest, PyTest, JUnit, NUnit, Go testing).
*   **Test Types:** What kinds of tests are prevalent (e.g., unit, integration, end-to-end)?
*   **File Organization:** Where are test files located relative to source files?
*   **Test Naming:** Conventions for naming test files and test cases.
*   **Common Patterns:** Use of mocks, stubs, fixtures, setup/teardown methods.

## 12. Styling & Formatting

*   **Tools:** Are linters (e.g., ESLint, Pylint, Checkstyle) or formatters (e.g., Prettier, Black, gofmt) used? Are configuration files present (`.eslintrc`, `pyproject.toml`, `.prettierrc`)?
*   **Key Style Rules:** Mention significant rules regarding indentation (spaces vs. tabs, count), line length, quotes (single vs. double), brace style, spacing, etc. *Infer these if no config file is provided.*

## 13. Dependency Management

*   **Tooling:** How are dependencies managed (e.g., npm/yarn, pip, Maven/Gradle, Go modules, NuGet)?
*   **Version Locking:** Are dependency versions locked (e.g., `package-lock.json`, `requirements.txt`, `go.sum`)?
*   **Common Libraries:** List any core or frequently used third-party libraries/SDKs.

## 14. Build & Deployment (If Observable)

*   **Build Tools:** Tools used for compiling, bundling, or packaging (e.g., Webpack, Rollup, Maven, Gradle, Docker).
*   **Scripts:** Common scripts for building, testing, running (`package.json` scripts, `Makefile`, etc.).
*   **CI/CD:** Any observable configuration for Continuous Integration or Deployment (e.g., `.github/workflows`, `gitlab-ci.yml`, `Jenkinsfile`).

~~~~