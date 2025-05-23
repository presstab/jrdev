# Prompt: Generate High‑Level Project Conventions (≤ 500 tokens)

**Objective**  
Produce a concise overview (max 500 tokens) of repository‑wide conventions that would NOT be obvious from reading just a few individual source files.

**Instructions**

1. Examine all supplied project artifacts (code, configs, docs).
2. Capture only high‑level, cross‑cutting practices, such as:
   - **Architecture** (e.g., Hexagonal, MVC, Micro‑services, Layered).
   - **Directory / Module Layout** and agreed‑upon boundaries.
   - **Build & Dependency Management** tools and version‑locking approach.
   - **Configuration & Environment** handling (env files, secrets, feature flags).
   - **Testing Strategy** tiers and **CI/CD** workflow highlights.
   - **Error Handling & Logging** philosophies (central logger, structured logs).
   - **Release / Versioning** schemes and branch strategy.
3. Omit fine‑grained code‑style rules (indentation, variable casing, small helper patterns) that are easily inferred from individual files.
4. Summarize findings in Markdown using terse headings and bullet points; include examples only when essential.
5. Ensure the entire response is 500 tokens or fewer.

**Output Template**

```markdown
# High‑Level Project Conventions

## Architecture
- …

## Directory / Module Layout
- …

## Build & Dependency Management
- …

## Configuration & Environment
- …

## Testing & CI/CD
- …

## Error Handling & Logging
- …

## Release / Versioning
- …
