# 分支上下文管理方案：Git Worktree + Skills 自动化
## Branch Context Management: Git Worktree + Skills Automation

> **场景**: 同一项目的不同功能分支，有不同的 constitution 和 AI Agent Memory（CLAUDE.md, GEMINI.md）
>
> **目标**: 自动化上下文切换、保存、恢复、上报

---

## 🎯 核心设计

### 问题分析

```
项目: payment-service
├── main 分支
│   └── memory/constitution.md (项目基础规范)
├── 001-payment-gateway 分支
│   ├── memory/constitution.md (+ 支付相关规范)
│   └── CLAUDE.md (支付网关开发上下文)
└── 002-user-auth 分支
    ├── memory/constitution.md (+ 认证相关规范)
    └── CLAUDE.md (用户认证开发上下文)

❌ 传统 git checkout 问题：
- 切换分支时，constitution.md 被覆盖
- AI Agent Memory 丢失之前的上下文
- 无法同时开发多个 feature

✅ 期望效果：
- 每个 feature 独立的上下文
- 切换分支时自动恢复上下文
- Feature 完成后，上报 constitution 更新
- 无缝的开发体验
```

---

## 🏗️ 方案架构

### **三层架构**

```
┌─────────────────────────────────────────────────┐
│  Layer 1: Git Worktree (物理隔离)                │
│  每个 feature 独立目录，完全隔离                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 2: Post-Checkout Hook (自动保存/恢复)     │
│  传统 branch switching 的后备方案                │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  Layer 3: Skills Automation (开发者体验)         │
│  specify CLI 命令 + SessionStart Hook           │
└─────────────────────────────────────────────────┘
```

---

## 📐 方案 1: Git Worktree（主方案，推荐）

### 原理

Git Worktree 允许一个 Git 仓库有**多个工作目录**，每个目录对应不同分支。

```
主仓库（main 分支）:
/home/user/payment-service/
├── .git/                          # Git 元数据（共享）
├── src/
└── memory/constitution.md         # main 分支的 constitution

Worktree 1（feature 001）:
/home/user/payment-service-001/
├── .git -> /home/user/payment-service/.git  # 指向主仓库
├── src/
└── memory/constitution.md         # 001 分支独立的 constitution

Worktree 2（feature 002）:
/home/user/payment-service-002/
├── .git -> /home/user/payment-service/.git
├── src/
└── memory/constitution.md         # 002 分支独立的 constitution
```

### 实现：specify CLI 集成

#### 1. 创建新 Feature（自动创建 Worktree）

```bash
# 用户执行
$ specify feature create payment-gateway

# 系统自动执行：
📋 Creating feature branch: 001-payment-gateway

1️⃣ Creating Git worktree...
   git worktree add ../payment-service-001 001-payment-gateway
   ✅ Worktree created at: /home/user/payment-service-001

2️⃣ Initializing feature context...
   - Copying base constitution.md
   - Initializing CLAUDE.md with feature context
   - Creating feature-specific .specify/config.yaml

3️⃣ Generating templates...
   specify generate --from .specify/templates --to .claude/commands/

4️⃣ Setting up AI Agent context...
   cat > CLAUDE.md <<EOF
   # Feature: Payment Gateway (001)

   ## Context
   This feature implements a secure payment gateway integration.

   ## Constitution Diff from Main
   + Added payment security requirements
   + Added PCI-DSS compliance checklist

   ## Recent Changes
   - [Empty - Feature just started]

   ## Tech Stack
   - Python 3.11
   - FastAPI
   - Stripe SDK
   EOF

5️⃣ Opening in IDE...
   code /home/user/payment-service-001

✅ Feature workspace ready!
   Directory: /home/user/payment-service-001
   Branch: 001-payment-gateway

💡 To switch to this feature: specify feature switch payment-gateway
💡 To list all features: specify feature list
```

#### 2. 切换 Feature（切换到 Worktree）

```bash
$ specify feature switch payment-gateway

# 系统执行：
📂 Switching to feature: payment-gateway

Worktree location: /home/user/payment-service-001
Current directory: /home/user/payment-service
IDE workspace: VSCode

Options:
  1. Change directory (cd)
  2. Open in new terminal window
  3. Update current IDE workspace

Choose (1/2/3): 2

✅ Opened feature workspace in new terminal
   Directory: /home/user/payment-service-001
   Branch: 001-payment-gateway

🤖 AI Agent context loaded:
   - Constitution: payment-gateway specific
   - CLAUDE.md: 2 days of development history
```

#### 3. Feature 完成（合并并上报 Constitution）

```bash
$ specify feature complete payment-gateway

# 系统执行：
🎉 Completing feature: payment-gateway

1️⃣ Analyzing constitution changes...

   📊 Constitution Diff Report:

   Base (main):          Feature (001):
   ─────────────────     ─────────────────────────────────────
   ## Security          ## Security
   - HTTPS only         - HTTPS only
   - Auth required      - Auth required
                        + Payment data encryption (PCI-DSS)
                        + Tokenization required
                        + 3D Secure for cards

   ## Code Review       ## Code Review
   - 2 approvers        - 2 approvers
                        + Security team review for payment code

2️⃣ Prompting for constitution update...

   ⚠️  Feature added new constitution rules.

   Do you want to:
   a) Merge changes back to main constitution ✅ (Recommended)
   b) Keep feature-specific (discard on merge)
   c) Review and edit before merging

   Choose (a/b/c): a

3️⃣ Creating PR with constitution update...

   gh pr create \
     --title "feat: Add payment gateway + Update constitution" \
     --body "$(cat <<EOF
   ## Feature Summary
   Implemented secure payment gateway with Stripe integration.

   ## Constitution Updates
   Added payment security requirements:
   - PCI-DSS compliance rules
   - Payment data encryption requirements
   - 3D Secure mandate
   - Security team review for payment code

   ## Files Changed
   - src/payment/ (new payment module)
   - memory/constitution.md (added payment rules)
   - CLAUDE.md (updated with payment context)

   ## Testing
   - ✅ Unit tests passing
   - ✅ Integration tests with Stripe sandbox
   - ✅ Security review completed
   EOF
   )"

4️⃣ Merging feature branch...
   git checkout main
   git merge 001-payment-gateway

5️⃣ Cleaning up worktree...
   git worktree remove ../payment-service-001

6️⃣ Updating main constitution...
   ✅ Constitution updated with payment security rules

7️⃣ Broadcasting to team...
   📧 Notification sent to #engineering:
      "Constitution updated: Payment security requirements added by @you"

✅ Feature completed successfully!

   Next steps:
   - Constitution changes are now in main
   - All future features will include payment security rules
   - Worktree cleaned up
```

#### 4. 列出所有 Features（Worktree 列表）

```bash
$ specify feature list

📋 Active Features (Worktrees):

┌────────┬─────────────────────┬──────────────────────────────────┬────────────┐
│ Branch │ Feature Name        │ Worktree Location                │ Status     │
├────────┼─────────────────────┼──────────────────────────────────┼────────────┤
│ 001    │ payment-gateway     │ /home/user/payment-service-001   │ ✅ Active  │
│ 002    │ user-auth           │ /home/user/payment-service-002   │ 🔒 Locked  │
│ 003    │ dashboard           │ /home/user/payment-service-003   │ ⚠️  Stale   │
└────────┴─────────────────────┴──────────────────────────────────┴────────────┘

💡 Commands:
   specify feature switch <name>    - Switch to feature worktree
   specify feature status <name>    - Show feature status
   specify feature complete <name>  - Complete and merge feature
   specify feature cleanup <name>   - Remove worktree without merging
```

---

## 📐 方案 2: Post-Checkout Hook（辅助方案）

### 适用场景

开发者**不想**使用 worktree，仍然喜欢传统的 `git checkout` 切换分支。

### 实现：自动保存/恢复上下文

#### Hook 安装

```bash
# specify CLI 自动安装
$ specify init my-project --ai claude

# 自动执行：
✅ Initialized Spec-Kit project
✅ Generated templates
✅ Configured Git hooks for branch context management

Git hooks installed:
  - .githooks/post-checkout    (auto-save/restore context)
  - .githooks/post-merge       (merge constitution changes)
  - .githooks/pre-commit       (validate constitution)

To activate: git config core.hooksPath .githooks
(Already configured for this project)
```

#### Hook 实现

```bash
#!/bin/bash
# .githooks/post-checkout
# Auto-save and restore branch-specific context files

# Arguments
PREV_HEAD="$1"
NEW_HEAD="$2"
BRANCH_CHECKOUT="$3"

# Only run on branch checkout (not file checkout)
if [ "$BRANCH_CHECKOUT" != "1" ]; then
    exit 0
fi

# Get branch names
PREV_BRANCH=$(git name-rev --name-only "$PREV_HEAD" 2>/dev/null | sed 's/remotes\/origin\///')
NEW_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)

CONTEXT_STORE=".git/branch-contexts"

echo "🔄 Branch context manager: $PREV_BRANCH → $NEW_BRANCH"

# === SAVE: Previous branch context ===
if [ -n "$PREV_BRANCH" ] && [ "$PREV_BRANCH" != "HEAD" ]; then
    echo "💾 Saving context for: $PREV_BRANCH"

    mkdir -p "$CONTEXT_STORE/$PREV_BRANCH"

    # Save constitution
    if [ -f "memory/constitution.md" ]; then
        cp memory/constitution.md "$CONTEXT_STORE/$PREV_BRANCH/constitution.md"
        echo "   ✅ Saved constitution.md"
    fi

    # Save AI Agent memory files
    for agent_file in CLAUDE.md GEMINI.md COPILOT.md CURSOR.md; do
        if [ -f "$agent_file" ]; then
            cp "$agent_file" "$CONTEXT_STORE/$PREV_BRANCH/$agent_file"
            echo "   ✅ Saved $agent_file"
        fi
    done

    # Save metadata
    cat > "$CONTEXT_STORE/$PREV_BRANCH/metadata.json" <<EOF
{
  "branch": "$PREV_BRANCH",
  "saved_at": "$(date -Iseconds)",
  "commit": "$PREV_HEAD",
  "saved_by": "$(git config user.name)"
}
EOF
fi

# === RESTORE: New branch context ===
if [ -d "$CONTEXT_STORE/$NEW_BRANCH" ]; then
    echo "📂 Restoring context for: $NEW_BRANCH"

    # Restore constitution
    if [ -f "$CONTEXT_STORE/$NEW_BRANCH/constitution.md" ]; then
        cp "$CONTEXT_STORE/$NEW_BRANCH/constitution.md" memory/constitution.md
        echo "   ✅ Restored constitution.md"
    fi

    # Restore AI Agent memory files
    for agent_file in CLAUDE.md GEMINI.md COPILOT.md CURSOR.md; do
        if [ -f "$CONTEXT_STORE/$NEW_BRANCH/$agent_file" ]; then
            cp "$CONTEXT_STORE/$NEW_BRANCH/$agent_file" "$agent_file"
            echo "   ✅ Restored $agent_file"
        fi
    done

    # Show metadata
    if [ -f "$CONTEXT_STORE/$NEW_BRANCH/metadata.json" ]; then
        SAVED_AT=$(jq -r '.saved_at' "$CONTEXT_STORE/$NEW_BRANCH/metadata.json" 2>/dev/null)
        echo "   📅 Context saved at: $SAVED_AT"
    fi

else
    echo "⚠️  No saved context for: $NEW_BRANCH"
    echo "   Using base constitution from Git"
fi

echo ""
echo "✅ Branch context switched successfully"
echo "   Previous: $PREV_BRANCH (saved)"
echo "   Current: $NEW_BRANCH (restored)"
```

#### 使用示例

```bash
# 开发者正常使用 Git
$ git checkout main
# constitution.md = main 版本

$ git checkout 001-payment-gateway
🔄 Branch context manager: main → 001-payment-gateway
💾 Saving context for: main
   ✅ Saved constitution.md
   ✅ Saved CLAUDE.md
📂 Restoring context for: 001-payment-gateway
   ✅ Restored constitution.md (with payment rules)
   ✅ Restored CLAUDE.md (payment context)
   📅 Context saved at: 2025-12-05T10:30:00+00:00

✅ Branch context switched successfully
   Previous: main (saved)
   Current: 001-payment-gateway (restored)

# constitution.md 现在是 001 分支的版本（包含支付规则）
```

---

## 📐 方案 3: Skills 自动化（终极用户体验）

### Skill: Feature Context Manager

创建一个 Skill，通过 SessionStart Hook 自动管理上下文。

#### Skill 定义

```yaml
# .claude/skills/feature-context-manager.yaml

name: feature-context-manager
description: Automatically manage branch-specific constitution and AI memory
type: session-start
triggers:
  - on_session_start
  - on_branch_change
  - on_feature_complete

actions:
  on_session_start:
    - check_current_branch
    - load_branch_context
    - display_context_summary

  on_branch_change:
    - save_previous_context
    - load_new_context
    - notify_context_diff

  on_feature_complete:
    - analyze_constitution_diff
    - prompt_constitution_merge
    - create_update_pr

config:
  storage_backend: worktree  # or: git-hook, git-stash
  auto_restore: true
  notify_on_change: true
```

#### Skill 实现

```python
# .claude/skills/feature_context_manager.py

class FeatureContextManager:
    """
    Manages branch-specific constitution and AI memory files.
    """

    def on_session_start(self):
        """
        当 Claude Code session 启动时调用
        """
        current_branch = self.get_current_branch()

        # 检查是否在 worktree 中
        if self.is_worktree():
            print(f"📂 Worktree detected: {self.get_worktree_path()}")
            print(f"   Branch: {current_branch}")
            context = self.load_worktree_context()
        else:
            # 使用 post-checkout hook 恢复的上下文
            context = self.load_git_context(current_branch)

        # 显示上下文摘要
        self.display_context_summary(context)

        # 更新 AI Agent memory
        self.update_claude_md(context)

    def display_context_summary(self, context):
        """
        显示当前分支的上下文信息
        """
        print("\n📋 Current Feature Context:")
        print(f"   Branch: {context['branch']}")
        print(f"   Feature: {context['feature_name']}")
        print(f"   Constitution: {context['constitution_version']}")
        print(f"   Last updated: {context['last_updated']}")
        print(f"\n📝 Constitution Highlights:")

        for rule in context['constitution_highlights']:
            print(f"   • {rule}")

        print(f"\n🤖 AI Context:")
        print(f"   Recent changes: {context['recent_changes']}")
        print(f"   Active spec: {context['active_spec']}")

    def on_feature_complete(self):
        """
        Feature 完成时，分析并上报 constitution 变更
        """
        current_branch = self.get_current_branch()

        # 比较当前 constitution 和 main
        diff = self.compare_constitution(current_branch, 'main')

        if not diff:
            print("✅ No constitution changes in this feature")
            return

        # 显示 diff
        print("\n📊 Constitution Changes Detected:\n")
        print(diff.formatted)

        # 询问用户
        choice = input("\nMerge these changes back to main constitution? (y/n): ")

        if choice.lower() == 'y':
            self.merge_constitution_to_main(diff)
            print("✅ Constitution updated in main branch")
        else:
            print("⚠️  Constitution changes will be feature-specific")

    def compare_constitution(self, branch_a, branch_b):
        """
        比较两个分支的 constitution 差异
        """
        const_a = self.get_constitution(branch_a)
        const_b = self.get_constitution(branch_b)

        # 结构化 diff（按章节）
        diff = {
            'added_sections': [],
            'modified_sections': [],
            'removed_sections': []
        }

        # 解析 Markdown 章节
        sections_a = self.parse_markdown_sections(const_a)
        sections_b = self.parse_markdown_sections(const_b)

        for section in sections_a:
            if section not in sections_b:
                diff['added_sections'].append(section)
            elif sections_a[section] != sections_b.get(section):
                diff['modified_sections'].append(section)

        for section in sections_b:
            if section not in sections_a:
                diff['removed_sections'].append(section)

        return diff
```

#### SessionStart Hook 集成

```python
# .claude/hooks/session_start.py

from skills.feature_context_manager import FeatureContextManager

def on_session_start():
    """
    Claude Code session 启动时自动调用
    """
    manager = FeatureContextManager()
    manager.on_session_start()
```

#### 实际体验

```bash
# 开发者打开 Claude Code
$ code .

# Claude Code 启动，自动调用 SessionStart Hook

📂 Worktree detected: /home/user/payment-service-001
   Branch: 001-payment-gateway

📋 Current Feature Context:
   Branch: 001-payment-gateway
   Feature: Payment Gateway Integration
   Constitution: v1.2.3-payment
   Last updated: 2025-12-05 15:30:00

📝 Constitution Highlights:
   • Payment data must be encrypted (PCI-DSS)
   • 3D Secure required for all card transactions
   • Security team review required for payment code
   • Rate limiting: 100 requests/min per user

🤖 AI Context:
   Recent changes: Implemented Stripe webhook handler
   Active spec: specs/001-payment-gateway.md

✅ Context loaded successfully

---

# 开发者继续开发...
# Claude Code 知道当前是 payment-gateway feature
# constitution 包含支付相关规则
# AI 记住了之前的开发进度
```

---

## 📐 方案 4: Constitution 上报机制

### 场景

Feature 开发完成后，需要将**有价值的 constitution 变更**合并回 main，供其他 feature 复用。

### 实现：智能 Constitution Diff + PR

#### 1. 分析 Constitution 变更

```bash
$ specify constitution diff main

📊 Constitution Diff: 001-payment-gateway vs main

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Added Sections (3):

  ## 5. Payment Security Requirements

  - All payment data MUST be encrypted in transit and at rest
  - PCI-DSS Level 1 compliance required
  - Use Stripe SDK (approved payment processor)
  - Tokenization required for storing card data
  - 3D Secure (SCA) mandatory for EU transactions

  Rationale: Payment features must meet regulatory requirements
  Added by: @john-doe on 2025-12-05

  ────────────────────────────────────────────────────────

  ## 6. Rate Limiting for Payment Endpoints

  - Payment endpoints: 10 requests/min per user
  - Webhook endpoints: 100 requests/min per IP
  - Implement exponential backoff for retries

  Rationale: Prevent abuse and ensure system stability
  Added by: @john-doe on 2025-12-06

  ────────────────────────────────────────────────────────

📝 Modified Sections (1):

  ## 2. Code Review Requirements

  Before (main):
    - All PRs require 2 approvals
    - At least 1 approval from senior engineer

  After (001-payment-gateway):
    - All PRs require 2 approvals
    - At least 1 approval from senior engineer
  + - Payment-related PRs require security team review  ← NEW

  Rationale: Payment code needs extra security oversight
  Modified by: @john-doe on 2025-12-05

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Recommendations:

  ✅ MERGE: Payment Security Requirements (Section 5)
     → High value for future payment features

  ✅ MERGE: Code Review modification
     → Important security practice

  ⚠️  REVIEW: Rate Limiting (Section 6)
     → Consider if this should be global or payment-specific
     → Suggest: Move to API documentation instead

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actions:
  a) Merge all changes to main
  b) Merge selected sections
  c) Review and edit before merging
  d) Keep feature-specific (don't merge)

Choose (a/b/c/d): b
```

#### 2. 选择性合并

```bash
# 用户选择 b（selective merge）

📝 Select sections to merge:

  [✓] 5. Payment Security Requirements
  [✓] 2. Code Review Requirements (modification)
  [ ] 6. Rate Limiting for Payment Endpoints

  Use ↑↓ to navigate, Space to toggle, Enter to confirm

---

# 用户确认后

✅ Selected sections to merge:
   - Payment Security Requirements
   - Code Review Requirements

Creating PR to update main constitution...

gh pr create \
  --title "docs: Update constitution with payment security rules" \
  --body "## Constitution Update from Feature: payment-gateway

### Sections Added

#### 5. Payment Security Requirements
- PCI-DSS Level 1 compliance
- Encryption requirements
- 3D Secure mandate

Rationale: All future payment features need these rules.

#### 2. Code Review Requirements (Modified)
- Added security team review for payment code

Rationale: Payment code has higher security risk.

### Review Checklist
- [ ] Reviewed by Engineering Lead
- [ ] Reviewed by Security Team
- [ ] No conflicts with existing rules

---
This PR was generated by \`specify constitution merge\`
Feature: 001-payment-gateway
Author: @john-doe
" \
  --reviewer engineering-lead,security-team \
  --label constitution,documentation

✅ PR created: #123

Constitution will be updated after PR approval and merge.
```

---

## 🔒 方案 5: 安全网 - Custom Merge Driver

### 防止意外覆盖

配置 Git，使得合并分支时，constitution 等上下文文件**不会自动合并**，而是保留当前分支版本。

#### 配置

```bash
# .gitattributes
memory/constitution.md merge=ours
CLAUDE.md merge=ours
GEMINI.md merge=ours
*.context.md merge=ours

# Git config (自动设置)
git config merge.ours.driver true
git config merge.ours.name "Keep our version during merge"
```

#### 效果

```bash
# Feature branch: 001-payment-gateway
# constitution.md 包含支付规则

$ git checkout main
$ git merge 001-payment-gateway

# 普通文件正常合并
# constitution.md 保持 main 版本（不自动覆盖）

⚠️  Constitution not auto-merged.
    Feature branch has constitution changes.

    To review: specify constitution diff 001-payment-gateway
    To merge: specify constitution merge 001-payment-gateway
```

这样可以避免**意外的 constitution 覆盖**，必须通过 `specify constitution merge` 显式操作。

---

## 🚀 完整工作流演示

### 场景：开发支付网关功能

```bash
# ========================================
# Step 1: 创建新 Feature
# ========================================

$ specify feature create payment-gateway

📋 Creating feature: payment-gateway

1️⃣ Creating Git worktree...
   ✅ Worktree: /home/user/payment-service-001
   ✅ Branch: 001-payment-gateway

2️⃣ Initializing constitution...
   📄 Copied base constitution from main
   📝 Added feature metadata:
      - Feature: Payment Gateway
      - Created: 2025-12-06
      - Owner: @john-doe

3️⃣ Initializing AI context...
   ✅ CLAUDE.md created

4️⃣ Opening workspace...
   ✅ Opened in VS Code

✅ Feature workspace ready!

---

# ========================================
# Step 2: 开发过程中修改 Constitution
# ========================================

$ cd /home/user/payment-service-001

# 编辑 constitution.md，添加支付规则
$ vim memory/constitution.md

# 添加：
## 5. Payment Security Requirements
- PCI-DSS compliance required
- Encrypt all payment data
- 3D Secure for EU transactions

# AI Agent 自动记录到 CLAUDE.md
# (通过 file watcher 或手动更新)

---

# ========================================
# Step 3: 开发完成，查看 Constitution 变更
# ========================================

$ specify constitution diff main

📊 Constitution Diff: 001-payment-gateway vs main

📝 Added Sections (1):
  ## 5. Payment Security Requirements
  - PCI-DSS compliance required
  - ...

💡 Recommendation: MERGE (high value for future features)

---

# ========================================
# Step 4: 完成 Feature（自动上报 Constitution）
# ========================================

$ specify feature complete payment-gateway

🎉 Completing feature: payment-gateway

1️⃣ Analyzing constitution changes...
   ✅ Found 1 new section

2️⃣ Prompting for merge...
   Merge to main constitution? (y/n): y

3️⃣ Creating PR...
   ✅ PR #123 created:
      - Feature code
      - Constitution update
      - CLAUDE.md context (archived)

4️⃣ Merging...
   ✅ Merged to main

5️⃣ Cleaning up worktree...
   ✅ Removed /home/user/payment-service-001

6️⃣ Broadcasting update...
   📧 Slack: "Constitution updated with payment security rules"

✅ Feature completed!

---

# ========================================
# Step 5: 其他开发者受益
# ========================================

# 另一个开发者创建新的支付相关 feature
$ specify feature create payment-refunds

📋 Creating feature: payment-refunds

✅ Constitution loaded with payment security rules
   (从 main 继承了之前的 payment security 章节)

💡 This feature inherits payment security requirements:
   - PCI-DSS compliance
   - Encryption requirements
   - 3D Secure

# 新 feature 自动继承之前总结的最佳实践！
```

---

## 📊 方案对比

| 特性 | Worktree | Post-Checkout Hook | Skills Automation |
|------|----------|-------------------|------------------|
| **隔离性** | ⭐⭐⭐⭐⭐ 完全隔离 | ⭐⭐⭐ 自动保存恢复 | ⭐⭐⭐⭐ 基于 Worktree |
| **易用性** | ⭐⭐⭐ 需要学习 | ⭐⭐⭐⭐⭐ 透明自动 | ⭐⭐⭐⭐⭐ 一键操作 |
| **安全性** | ⭐⭐⭐⭐⭐ 无覆盖风险 | ⭐⭐⭐ 依赖 hook 可靠性 | ⭐⭐⭐⭐⭐ 多层保护 |
| **IDE 支持** | ⭐⭐⭐⭐ 独立窗口 | ⭐⭐⭐⭐⭐ 无感知 | ⭐⭐⭐⭐⭐ 集成体验 |
| **多 Feature 并行** | ⭐⭐⭐⭐⭐ 完美支持 | ⭐⭐ 需手动管理 | ⭐⭐⭐⭐⭐ 自动管理 |
| **Constitution 上报** | ⭐⭐⭐ 手动 | ⭐⭐⭐ 手动 | ⭐⭐⭐⭐⭐ 自动分析 |

---

## 🎯 推荐方案

### **主方案：Worktree + Skills Automation**

```
为什么？

1. ✅ 完全隔离 - 每个 feature 独立目录，零风险
2. ✅ 并行开发 - 可同时开发多个 feature
3. ✅ IDE 友好 - 每个 feature 独立 VS Code 窗口
4. ✅ 自动化 - 通过 Skills 实现一键操作
5. ✅ Constitution 治理 - 自动分析、上报、合并
```

### **备用方案：Post-Checkout Hook**

```
适合：

- 不想改变传统 git workflow 的团队
- 单人开发、较少并行 features
- 快速原型项目

限制：

- 不支持真正的并行开发
- 依赖 hook 可靠性
- Constitution 上报需手动
```

---

## 📋 实施步骤

### Phase 1: 基础设施（1 周）

```bash
# 1. 添加 .gitattributes（安全网）
cat > .gitattributes <<EOF
memory/constitution.md merge=ours
CLAUDE.md merge=ours
GEMINI.md merge=ours
EOF

git config merge.ours.driver true

# 2. 实现 specify feature 命令
specify feature create <name>    # 创建 worktree
specify feature switch <name>    # 切换 worktree
specify feature list            # 列出 worktrees
specify feature complete <name>  # 完成并上报

# 3. 实现 specify constitution 命令
specify constitution diff <branch>      # 比较差异
specify constitution merge <branch>     # 合并变更
specify constitution report            # 生成报告
```

### Phase 2: Hooks 集成（1 周）

```bash
# 4. 实现 post-checkout hook（备用方案）
.githooks/post-checkout
.githooks/post-merge

# 5. 配置自动安装
specify init --enable-context-hooks

# 6. 文档和培训
docs/workflows/branch-context-management.md
```

### Phase 3: Skills 自动化（2 周）

```bash
# 7. 实现 SessionStart Hook
.claude/hooks/session_start.py

# 8. 实现 Feature Context Manager Skill
.claude/skills/feature_context_manager.py

# 9. 集成 AI Agent 上下文更新
自动更新 CLAUDE.md, GEMINI.md
```

### Phase 4: Constitution 治理（1 周）

```bash
# 10. 实现智能 diff 分析
specify constitution diff --smart

# 11. 实现选择性合并
specify constitution merge --interactive

# 12. 实现自动 PR 创建
specify feature complete --auto-pr
```

---

## 📚 相关文档

- `GIT_ECOSYSTEM_NATIVE_SOLUTION.md` - Git 生态方案总览
- `GIT_NATIVE_GOVERNANCE.md` - Git 治理机制
- `ENTERPRISE_SOLUTION.md` - 企业级完整方案

---

**文档版本**: v1.0
**最后更新**: 2025-12-06
**状态**: 完整实施方案
**核心**: Git Worktree + Skills Automation + Constitution 治理
