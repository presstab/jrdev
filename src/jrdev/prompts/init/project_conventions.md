# Prompt: Generate Codebase Conventions and Patterns Document

__Objective:__ Analyze the provided codebase files and generate a comprehensive document. This document should meticulously detail the OBSERVED conventions, patterns, and practices employed within the code. The primary goal is to create a clear and actionable guide for current and future developers to ensure consistency and maintainability. DO NOT infer conventions that are not present in the provided files.

__Instructions:__

1.  __Analyze Thoroughly:__ Examine all provided code files to identify recurring patterns and established conventions. Do not infer these conventions, they must be observed in the provided files.
2.  __Structure the Output:__ Use Markdown formatting effectively. Employ clear headers (`##`, `###`), bullet points (* or -), bold text (__), inline code (` `), and code blocks (``` ```) for specific examples extracted directly from the provided codebase.
3.  __Be Language-Agnostic:__ While drawing specific examples from the code, describe the conventions in general terms where possible, avoiding excessive reliance on language-specific jargon unless essential to illustrate a point.
4.  __Provide Concrete Examples:__ For each identified convention or pattern, include short, relevant code snippets *from the provided files* to illustrate the point clearly.
5.  __Focus on Actionable Guidance:__ Frame the descriptions in a way that helps a developer understand *how* to write new code that fits the existing style.

__Output Structure:__

Please structure your response following this Markdown outline. 

```markdown
# Codebase Conventions and Patterns Guide

This document outlines the established conventions and patterns observed in the codebase. Adhering to these guidelines helps maintain consistency, readability, and maintainability.

## 1. Language & Environment

-   __Primary Language(s):__ [Identify the main programming language(s) used]
-   __Key Frameworks/Runtimes:__ [List major frameworks (e.g., React, Spring, .NET, Node.js) or runtimes]
-   __Package/Module System:__
    - Describe the system used for organizing and sharing code (e.g., ES Modules, CommonJS, Java packages Python modules, namespaces).
    - Provide examples of import/export or include/using statements.


## 2. Naming Conventions

-   __File Naming:__
    - Convention used (e.g., `kebab-case.js`, `PascalCase.cs`, `snake_case.py`).
    - Patterns for specific file types (e.g., `*.component.ts`, `*_test.py`, `IInterfaceName.java`).
    - Examples: `user-profile.component.jsx`, `AuthService.java`, `database_connection.py`
-   __Variables:__ Convention used (e.g., `camelCase`, `snake_case`, `PascalCase` for constants). Examples.
-   __Functions/Methods:__ Convention used (e.g., `camelCase`, `snake_case`, `PascalCase` for constructors). Examples.
-   __Classes/Interfaces/Types:__ Convention used (e.g., `PascalCase`, prefix `I` for interfaces). Examples.
-   __Constants:__ Convention used (e.g., `UPPER_SNAKE_CASE`). Examples.
-   __Other (if applicable):__ Conventions for enums, modules, packages, etc.

## 3. Code Structure & Organization

-   __Intra-file Organization:__
    - Standard order of elements (e.g., imports, constants, class definition, methods, private functions).
    - Use of regions, markers, or comments for sectioning.
-   __Import/Include Ordering:__
    - Grouping conventions (e.g., external libs, internal modules, relative paths).
    - Sorting conventions (e.g., alphabetical).
    - Example:
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

-   __Primary Paradigm(s):__ Is the code predominantly Object-Oriented, Functional, Procedural, or a mix?
-   __Common Design Patterns:__ Identify recurring patterns (e.g., Singleton, Factory, Repository, Middleware, MVC/MVVM). Where are they typically used?
-   __Immutability:__ Is immutability preferred? Where and how is it enforced?
-   __Code Reusability:__ How is code reuse achieved (e.g., inheritance, composition, utility functions, hooks)?

## 5. Type System (If Applicable)

-   __Static vs. Dynamic:__ Is a static type system used (e.g., TypeScript, Java, C#, Flow, MyPy)? Or is it primarily dynamic?
-   __Type Declaration:__ How are types specified? (e.g., type hints, interfaces, annotations, JSDoc). Provide examples.
-   __Type Usage:__ Where are types most rigorously applied (e.g., function signatures, data structures, API boundaries)?

## 6. Error Handling

-   __Mechanism:__ How are errors typically handled? (e.g., exceptions/try-catch, error codes, specific return types like `Result`/`Option`, dedicated error objects).
-   __Error Types:__ Are custom error classes/types used? How are they structured?
-   __Propagation:__ How are errors propagated up the call stack?
-   __Logging/Reporting:__ How and where are errors logged or reported? Examples.

## 7. Asynchronous Programming

-   __Patterns Used:__ Identify the primary methods for handling async operations (e.g., `async/await`, Promises, Futures, Callbacks, Threads, Goroutines, Event Loops).
-   __Concurrency/Parallelism:__ Are there specific patterns for managing concurrent or parallel execution?
-   __Common Use Cases:__ Where are async patterns most prevalent (e.g., I/O, API calls, background tasks)?

## 8. State Management (If Applicable)

-   __Approach:__ How is application state managed (e.g., global state stores like Redux/Vuex/Context API, service-based state, local component state, database as source of truth)?
-   __Scope:__ Conventions for deciding between global vs. local state.
-   __State Mutation:__ How is state updated (e.g., reducers, setters, direct mutation)?

## 9. API/Interface Design (If Applicable)

-   __Style:__ Conventions for designing internal or external APIs (e.g., RESTful principles, GraphQL schema design, gRPC service definitions, function signatures).
-   __Data Formats:__ Standard request/response formats (e.g., JSON structure, status codes, error formats).
-   __Versioning:__ How are APIs versioned, if at all?

## 10. Documentation & Comments

-   __Code Comments:__
    - Style used (`//`, `#`, `/* */`, docblocks).
    - When are comments typically used (e.g., explaining complex logic, documenting public APIs, TODOs)?
    - Format for docblocks (e.g., JSDoc, TSDoc, XML-Doc). Examples.
-   __External Documentation:__ Is there a system for generating documentation from code comments (e.g., Sphinx, Javadoc, TypeDoc)?

## 11. Testing

-   __Frameworks/Libraries:__ Identify testing tools used (e.g., Jest, PyTest, JUnit, NUnit, Go testing).
-   __Test Types:__ What kinds of tests are prevalent (e.g., unit, integration, end-to-end)?
-   __File Organization:__ Where are test files located relative to source files?
-   __Test Naming:__ Conventions for naming test files and test cases.
-   __Common Patterns:__ Use of mocks, stubs, fixtures, setup/teardown methods.

## 12. Styling & Formatting

-   __Tools:__ Are linters (e.g., ESLint, Pylint, Checkstyle) or formatters (e.g., Prettier, Black, gofmt) used? Are configuration files present (`.eslintrc`, `pyproject.toml`, `.prettierrc`)?
-   __Key Style Rules:__ Mention significant rules regarding indentation (spaces vs. tabs, count), line length, quotes (single vs. double), brace style, spacing, etc. *Infer these if no config file is provided.*

## 13. Dependency Management

-   __Tooling:__ How are dependencies managed (e.g., npm/yarn, pip, Maven/Gradle, Go modules, NuGet)?
-   __Version Locking:__ Are dependency versions locked (e.g., `package-lock.json`, `requirements.txt`, `go.sum`)?
-   __Common Libraries:__ List any core or frequently used third-party libraries/SDKs.

## 14. Build & Deployment (If Observable)

-   __Build Tools:__ Tools used for compiling, bundling, or packaging (e.g., Webpack, Rollup, Maven, Gradle, Docker).
-   __Scripts:__ Common scripts for building, testing, running (`package.json` scripts, `Makefile`, etc.).
-   __CI/CD:__ Any observable configuration for Continuous Integration or Deployment (e.g., `.github/workflows`, `gitlab-ci.yml`, `Jenkinsfile`).
```