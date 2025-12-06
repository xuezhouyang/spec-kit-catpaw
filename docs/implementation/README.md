# 分支上下文管理实现方案
## Branch Context Management Implementation

本目录包含完整的实现代码，用于管理不同分支的 constitution 和 AI Agent Memory。

---

## 📁 文件说明

```
implementation/
├── README.md                              # 本文件
├── feature-worktree-commands.py          # Specify CLI: feature 子命令实现
├── git-hooks/
│   ├── post-checkout                     # Git Hook: 自动保存/恢复上下文
│   └── post-merge                        # Git Hook: 合并时处理 constitution
└── skills/
    └── feature_context_manager_skill.py  # Claude Code Skill: 自动化上下文管理
```

---

## 🚀 快速开始

### 方案选择

根据您的团队习惯选择：

| 方案 | 适合场景 | 优势 | 劣势 |
|------|---------|------|------|
| **Git Worktree** | 多 feature 并行开发 | 完全隔离，零风险 | 需要改变工作习惯 |
| **Post-Checkout Hook** | 传统 Git workflow | 透明自动，无感知 | 不支持真正并行 |
| **Skills Automation** | Claude Code 用户 | 一键操作，智能化 | 依赖 Claude Code |

**推荐：** Worktree + Skills（完整体验）

---

## 🏗️ 安装与配置

### 方案 1: Git Worktree + Specify CLI

#### 1. 集成到 Specify CLI

```bash
# 将 feature-worktree-commands.py 集成到 specify CLI

# 方式 1: 添加到现有 CLI
cd spec-kit-catpaw/src/specify_cli
cp ../../docs/implementation/feature-worktree-commands.py ./feature_commands.py

# 在 __init__.py 中导入
# from .feature_commands import feature
# cli.add_command(feature)

# 方式 2: 作为插件
mkdir -p ~/.specify/plugins
cp docs/implementation/feature-worktree-commands.py ~/.specify/plugins/
```

#### 2. 使用

```bash
# 创建新 feature（自动创建 worktree）
specify feature create payment-gateway --description "Stripe payment integration"

# 切换 feature
specify feature switch payment-gateway

# 列出所有 features
specify feature list

# 完成 feature（自动分析 constitution 变更）
specify feature complete payment-gateway

# 清理 worktree
specify feature cleanup payment-gateway
```

---

### 方案 2: Post-Checkout Hook（备用方案）

#### 1. 安装 Hook

```bash
# 方式 1: 复制到 .git/hooks/（单项目）
cp docs/implementation/git-hooks/post-checkout .git/hooks/
chmod +x .git/hooks/post-checkout

# 方式 2: 使用自定义 hooks 目录（可提交到仓库）
mkdir -p .githooks
cp docs/implementation/git-hooks/post-checkout .githooks/
chmod +x .githooks/post-checkout

# 配置 Git 使用自定义 hooks 目录
git config core.hooksPath .githooks

# 提交 hooks 到仓库（推荐）
git add .githooks/
git commit -m "chore: Add branch context management hooks"
```

#### 2. 配置

编辑 hook 文件，根据需要调整：

```bash
# 修改保存的文件列表
CONTEXT_FILES=(
    "memory/constitution.md"
    "CLAUDE.md"
    "GEMINI.md"
    "COPILOT.md"
    # 添加其他需要管理的文件
)
```

#### 3. 使用

```bash
# 正常使用 Git，hook 会自动运行
git checkout main
# 💾 自动保存当前分支上下文

git checkout 001-payment-gateway
# 📂 自动恢复 001 分支上下文

# 查看保存的上下文
ls .git/branch-contexts/
# main/
# 001-payment-gateway/
# 002-user-auth/
```

---

### 方案 3: Skills Automation（完整体验）

#### 1. 安装 Skill

```bash
# 复制 skill 到 Claude Code 项目
mkdir -p .claude/skills
cp docs/implementation/skills/feature_context_manager_skill.py .claude/skills/
```

#### 2. 配置 SessionStart Hook

创建 `.claude/hooks/session_start.py`:

```python
#!/usr/bin/env python3
"""
Claude Code SessionStart Hook
"""

import sys
from pathlib import Path

# 添加 skills 目录到 Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "skills"))

from feature_context_manager_skill import on_session_start

# 调用 skill
on_session_start()
```

```bash
chmod +x .claude/hooks/session_start.py
```

#### 3. 使用

```bash
# 打开 Claude Code
code .

# SessionStart Hook 自动运行，显示：
# ============================================================
# 🚀 Feature Context Manager - Session Start
# ============================================================
#
# 📋 Current Environment:
#    Type: WORKTREE
#    Branch: 001-payment-gateway
#    Worktree: /home/user/payment-service-001
#
# 📝 Constitution:
#    Version: v1.2.3-payment
#    Sections: 8
#    Feature-Specific Rules: 3
#
#    🎯 Feature-Specific Highlights:
#       • Payment data must be encrypted (PCI-DSS)
#       • 3D Secure required for all card transactions
#       • Security team review required for payment code
#
# 🤖 AI Context:
#    Last updated: 2025-12-05
#    Recent changes:
#       - Implemented Stripe webhook handler
#       - Added payment validation logic
#       - Updated error handling
#
# ============================================================
# ✅ Context loaded - Ready for development!
# ============================================================
```

---

## 📚 使用示例

### 完整工作流：支付网关功能开发

#### Step 1: 创建 Feature

```bash
$ specify feature create payment-gateway

📋 Creating feature: payment-gateway

1️⃣  Creating Git worktree...
   ✅ Worktree created at: /home/user/payment-service-001
   ✅ Branch: 001-payment-gateway

2️⃣  Initializing feature context...
   ✅ Constitution initialized

3️⃣  Generating templates...
   ✅ Templates generated

4️⃣  Setting up AI Agent context...
   ✅ CLAUDE.md initialized

✅ Feature workspace ready!
   Directory: /home/user/payment-service-001
   Branch: 001-payment-gateway
```

#### Step 2: 开发过程中修改 Constitution

```bash
$ cd /home/user/payment-service-001

# 编辑 constitution，添加支付相关规则
$ vim memory/constitution.md

# 在 "Feature-Specific Rules" section 添加：
## Feature-Specific Rules

### Payment Security Requirements
- All payment data MUST be encrypted in transit and at rest
- PCI-DSS Level 1 compliance required
- Use Stripe SDK (approved payment processor)
- 3D Secure mandatory for EU transactions

### Code Review for Payment Code
- Payment-related PRs require security team review
- Minimum 2 reviewers, including 1 senior engineer
```

#### Step 3: 开发完成，查看 Constitution 变更

```bash
$ python .claude/skills/feature_context_manager_skill.py diff

📊 Constitution Changes Detected:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Added Sections:

## Payment Security Requirements

  - All payment data MUST be encrypted in transit and at rest
  - PCI-DSS Level 1 compliance required
  - Use Stripe SDK (approved payment processor)
  - 3D Secure mandatory for EU transactions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Modified Sections:

## Code Review Requirements

Changes:
  - All PRs require 2 approvals
  - At least 1 approval from senior engineer
+ - Payment-related PRs require security team review  ← NEW
```

#### Step 4: 完成 Feature（自动上报）

```bash
$ specify feature complete payment-gateway

🎉 Completing feature: payment-gateway

1️⃣  Analyzing constitution changes...
   📊 Found 1 new section, 1 modified section

2️⃣  Prompting for constitution update...

   Options:
     a) Merge all changes to main constitution
     b) Merge selected sections
     c) Review and edit before merging
     d) Keep feature-specific (don't merge)

   Choose (a/b/c/d): a

3️⃣  Creating PR...
   ✅ PR #123 created:
      Title: feat: Add payment gateway + Update constitution
      Reviewers: @engineering-lead, @security-team

4️⃣  Merging feature branch...
   ✅ Merged to main

5️⃣  Cleaning up worktree...
   ✅ Removed /home/user/payment-service-001

6️⃣  Broadcasting update...
   📧 Slack notification sent to #engineering

✅ Feature completed!
```

#### Step 5: 新 Feature 自动继承

```bash
# 另一个开发者创建新的支付相关 feature
$ specify feature create payment-refunds

📋 Creating feature: payment-refunds

✅ Constitution loaded with payment security rules
   (从 main 继承了之前 feature 的 payment security 章节)

💡 Inherited rules:
   • Payment Security Requirements (from feat 001)
   • Security code review process (from feat 001)

# 新 feature 自动包含之前总结的最佳实践！
```

---

## 🔧 高级配置

### 自定义 Context 文件

在 `post-checkout` hook 中添加更多文件：

```bash
CONTEXT_FILES=(
    "memory/constitution.md"
    "CLAUDE.md"
    "GEMINI.md"
    "COPILOT.md"
    "CURSOR.md"
    ".vscode/settings.json"      # VS Code 设置
    ".specify/feature-config.yaml"  # Feature 特定配置
    "docs/feature-notes.md"       # Feature 笔记
)
```

### 配置 .gitattributes（安全网）

防止合并时意外覆盖上下文文件：

```bash
# .gitattributes
memory/constitution.md merge=ours
CLAUDE.md merge=ours
GEMINI.md merge=ours
*.context.md merge=ours

# 配置 merge driver
git config merge.ours.driver true
git config merge.ours.name "Keep our version during merge"
```

### 集成到 specify init

在项目初始化时自动配置：

```python
# 在 specify_cli/__init__.py 的 init() 函数中添加

def init_project(...):
    # ... 现有代码 ...

    # 配置分支上下文管理
    setup_branch_context_management()

def setup_branch_context_management():
    """配置分支上下文管理"""

    # 1. 安装 Git hooks
    hooks_dir = Path(".githooks")
    hooks_dir.mkdir(exist_ok=True)

    # 复制 hooks
    shutil.copy(
        TEMPLATES_DIR / "git-hooks" / "post-checkout",
        hooks_dir / "post-checkout"
    )

    # 设置可执行权限
    (hooks_dir / "post-checkout").chmod(0o755)

    # 配置 Git
    subprocess.run(["git", "config", "core.hooksPath", ".githooks"])

    # 2. 配置 .gitattributes
    with open(".gitattributes", "a") as f:
        f.write("\n# Branch context files - use 'ours' merge strategy\n")
        f.write("memory/constitution.md merge=ours\n")
        f.write("CLAUDE.md merge=ours\n")

    # 3. 安装 Skills（如果使用 Claude Code）
    if AI_AGENT == "claude":
        claude_skills_dir = Path(".claude/skills")
        claude_skills_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy(
            TEMPLATES_DIR / "skills" / "feature_context_manager_skill.py",
            claude_skills_dir / "feature_context_manager_skill.py"
        )

    print("✅ Branch context management configured")
```

---

## 🔍 故障排查

### Hook 不运行

```bash
# 检查 hook 是否可执行
ls -la .githooks/post-checkout
# -rwxr-xr-x  ... post-checkout  ← 需要有 x 权限

# 如果没有，添加权限
chmod +x .githooks/post-checkout

# 检查 Git 配置
git config core.hooksPath
# 应该输出: .githooks

# 如果没有，设置配置
git config core.hooksPath .githooks
```

### Worktree 创建失败

```bash
# 检查分支是否已存在
git branch
# 如果已存在，删除或使用不同名称

# 检查 worktree 目录是否已存在
ls -la ../payment-service-001
# 如果存在，删除或使用不同路径

# 手动清理 stale worktrees
git worktree prune
```

### Context 恢复不正确

```bash
# 检查 context 存储
ls -la .git/branch-contexts/

# 查看特定分支的保存内容
ls -la .git/branch-contexts/001-payment-gateway/

# 手动恢复
cp .git/branch-contexts/001-payment-gateway/constitution.md memory/

# 清理 context 缓存（重新开始）
rm -rf .git/branch-contexts/
```

---

## 📖 参考文档

- [分支上下文管理完整方案](../BRANCH_CONTEXT_MANAGEMENT.md)
- [Git Worktree 官方文档](https://git-scm.com/docs/git-worktree)
- [Git Hooks 文档](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [Git 生态原生方案](../GIT_ECOSYSTEM_NATIVE_SOLUTION.md)

---

## 🎯 下一步

1. ✅ 选择适合您团队的方案
2. ✅ 安装并测试
3. ✅ 培训团队成员
4. ✅ 收集反馈并优化
5. ✅ 扩展到更多项目

---

**维护者**: Spec-Kit Team
**最后更新**: 2025-12-06
**状态**: Production Ready
