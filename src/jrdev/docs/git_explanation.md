# 🧠 AI-Powered Git Tools

> ⚠️ **Note:** This tool uses Git command-line tools under the hood. Make sure Git is installed and available in your terminal before using it.

This tool integrates AI into your daily Git workflow, helping you write better commit messages and create cleaner pull requests. It uses Git command-line tools to analyze your changes and interact with an AI model.

---

## ✨ What It Can Do

### 🔍 1. Interactive Staging & Committing
The Git Overview tab provides a UI to manage your local changes:
- **View Status:** See your current branch, unstaged files, and staged files in separate lists.
- **View Diffs:** Select any file to see a color-coded diff of its changes.
- **Stage & Unstage:** Easily move files between the working directory and the staging area.
- **Reset Changes:** Discard local modifications for an unstaged file.
- **Commit:** Once files are staged, you can write or generate a commit message and create the commit.

### 📝 2. AI-Generated Commit Messages
From the commit view, you can ask the AI to generate a commit message for you.
- It analyzes your **staged files** (`git diff --staged`).
- It creates a concise message following the **Conventional Commits** specification.

### 📄 3. AI-Powered Pull Request Tools
These tools help you prepare your branch for a pull request by comparing it against a **base branch** (e.g., `origin/main`).
- **PR Summary:** Generates a clean, helpful description of what changed in your branch.
- **PR Review:** Asks the AI to act as a reviewer, giving feedback and pointing out potential issues in your code.

---

## 📌 What Is the Base Branch?

> **Note:** The base branch is used for the **Pull Request Summary** and **Code Review** features.

The **base branch** is what your changes are being compared to — usually the main branch where you’ll be merging your work. The tool runs `git diff <base_branch>` to get the changes.

### Common Choices:
- `origin/main` — when your work is based on the main production branch
- `origin/develop` — if your team uses a develop branch
- `origin/feature-x` — to compare against a specific feature or staging branch

💡 **Tip:** Use the branch you plan to merge into. Make sure it's up-to-date by running `git fetch origin` first.

---

## 🌐 What Does `origin` Mean?

`origin` is Git’s default name for the remote version of your repository — the one hosted on GitHub, GitLab, etc.

When you see something like `origin/main`, it means:

- `origin` = the remote repository
- `main` = the branch on that remote

You can check your remotes with:

```bash
git remote -v
```

Other common remotes include:
- `upstream` — usually the original repo you forked from
- Custom names — like `team` or `myfork`

---

## ✅ Quick Setup Checklist

- [ ] Git is installed and working from the command line.
- [ ] You have a Git repository open.
- [ ] For PR tools, you know which base branch you want to compare against.
- [ ] The base branch is up to date (run `git fetch` to be sure).

---