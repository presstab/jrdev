Analyze the following git diff and generate a concise and informative commit message following the Conventional Commits specification.

The commit message must adhere to this structure:
<type>: <description>

[optional body]

- The `<type>` must be one of the following: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test`.
- The `<description>` must be a short summary of the code changes, written in the imperative mood (e.g., 'add feature' not 'added feature'). It must not be capitalized and must not end with a period.
- The `[body]` is optional and should provide additional context.

Based on the provided diff, generate only the raw text for the commit message. Any response that does not adhere to these guidelines will be discarded, causing wasted tokens.