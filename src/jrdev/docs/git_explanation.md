# 🧠 AI-Powered Git Pull Request Summary and Reviews

> ⚠️ **Note:** This tool uses Git command-line tools under the hood. Make sure Git is installed and available in your terminal before using it.

This feature helps you make better pull requests by using AI to summarize or review your code changes. It compares your current branch to a **base branch** using:

```bash
git diff <base_branch>
```

The output is sent to an AI model along with a prompt — either to generate a **pull request summary** or to provide a **code review**.

---

## ✨ What It Can Do

### 📝 1. Pull Request Summary  
Generates a clean, helpful description of what changed in your branch. Great for writing the description section of your pull request.

### 🔍 2. Code Review  
Asks the AI to act as a reviewer — giving feedback, pointing out issues, and offering suggestions based on the changes detected in your diff.

---

## 📌 What Is the Base Branch?

The **base branch** is what your changes are being compared to — usually the branch where you’ll be merging your work.

### Common Choices:
- `origin/main` — when your work is based on the main production branch
- `origin/develop` — if your team uses a develop branch
- `origin/feature-x` — to compare against a specific feature or staging branch

💡 **Tip:** Use the branch you plan to merge into.

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

- [ ] Git is installed and working from the command line
- [ ] You’ve committed changes to your branch
- [ ] You know which branch you want to compare against (base branch)
- [ ] The base branch is up to date (ie `git fetch origin`)

---
