# 完全基于 Git 生态系统的企业规范治理方案
## Pure Git-Ecosystem Governance Solution

> **核心原则**: 不重复造轮子，100% 利用 Git 和 GitHub/GitLab 现有能力

---

## 🎯 设计哲学

### 1. 充分利用现有 Git 生态能力

| 需求 | Git 生态现有能力 | 无需重新实现 |
|------|-----------------|--------------|
| **版本管理** | Git tags, branches, commits | ✅ |
| **权限控制** | CODEOWNERS, Protected branches, Required reviews | ✅ |
| **审批流程** | Pull Request + Required approvers + Status checks | ✅ |
| **审计追踪** | Git history + commit signatures + PR timeline | ✅ |
| **通知系统** | GitHub/GitLab notifications + Slack/Email integrations | ✅ |
| **自动化** | GitHub Actions / GitLab CI + Webhooks | ✅ |
| **发布管理** | GitHub Releases / GitLab Releases | ✅ |
| **依赖管理** | Git submodules / Git subtree | ✅ |
| **锁定机制** | Protected tags + Branch protection + Signed commits | ✅ |
| **变更追踪** | Git blame, log, diff, reflog | ✅ |

---

## 📐 架构设计（纯 Git 生态）

### 核心组件映射

```
企业需求                 →  Git 生态能力
──────────────────────────────────────────────────
模板中心仓库             →  Git Repository
模板版本                 →  Git Tags (v1.0.0, v2.0.0)
强制/推荐级别            →  Git Submodules (不同更新策略)
审批流程                 →  PR + Required Reviews + CODEOWNERS
策略执行                 →  Branch Protection + Status Checks
版本锁定                 →  Git Submodule 锁定 commit hash
级联更新                 →  Dependabot / Renovate Bot
审计日志                 →  Git log + Signed commits
通知机制                 →  GitHub Notifications + Actions
权限管理                 →  GitHub Teams + Repository permissions
```

---

## 🏗️ 具体实现方案

### 方案 A: Git Submodules（推荐）

**核心思想**: 将模板中心仓库作为项目的 Git submodule，利用 submodule 机制管理版本和更新。

#### 1. 仓库结构

```
# 企业模板中心仓库
git@company.com/templates/spec-templates.git
├── corporate/
│   ├── constitution.md
│   ├── security-checklist.md
│   └── compliance-plan.md
├── department/
│   ├── api-spec.md
│   └── microservice-plan.md
└── team/
    └── custom-workflows/

# 项目仓库
git@company.com/backend/payment-service.git
├── .gitmodules                    # Submodule 配置
├── .specify/
│   ├── templates/                 # → Submodule to spec-templates
│   │   ├── corporate/             # (locked to specific commit)
│   │   ├── department/
│   │   └── team/
│   └── overrides/                 # 本地覆盖（Git tracked）
│       └── custom-plan.md
├── .claude/commands/              # 生成的模板（.gitignore）
└── memory/constitution.md         # 生成的模板（.gitignore）
```

#### 2. 初始化项目

```bash
# 1. 创建项目
git init payment-service
cd payment-service

# 2. 添加模板中心作为 submodule
git submodule add \
  git@company.com/templates/spec-templates.git \
  .specify/templates

# 3. 锁定到特定版本（企业强制）
cd .specify/templates
git checkout tags/v2.1.0  # 锁定到 v2.1.0
cd ../..

# 4. 提交
git add .gitmodules .specify/templates
git commit -m "chore: Add spec templates v2.1.0 as submodule"

# 5. 从 submodule 生成实际模板
specify generate \
  --from .specify/templates/corporate \
  --to .claude/commands/

# 6. 添加到 .gitignore（生成的文件不提交）
echo ".claude/commands/" >> .gitignore
echo "memory/constitution.md" >> .gitignore
```

#### 3. 强制更新流程（企业级模板）

**场景**: 合规团队发布新的安全检查清单 v2.2.0

```bash
# === 模板中心仓库 ===
cd spec-templates

# 1. 更新模板
vim corporate/security-checklist.md

# 2. 提交并打 tag
git add corporate/security-checklist.md
git commit -s -m "feat(corporate): Update security checklist v2.2.0

Add OWASP Top 10 2023 requirements

BREAKING CHANGE: All finance/healthcare projects must update

Signed-off-by: Jane Smith <jane@company.com>"

# 3. 创建 tag（语义化版本）
git tag -a v2.2.0 -m "Release v2.2.0: OWASP 2023 compliance"

# 4. 推送（protected tag，需要权限）
git push origin v2.2.0

# 5. 创建 GitHub Release
gh release create v2.2.0 \
  --title "v2.2.0: OWASP 2023 Compliance" \
  --notes "## Breaking Changes
  - All finance/healthcare projects must update within 30 days

  ## What's Changed
  - Add OWASP Top 10 2023 requirements
  - Update password policy

  ## Migration Guide
  Run: \`specify update --force v2.2.0\`"

# 6. 自动触发更新 PR 到所有项目（GitHub Actions）
# .github/workflows/cascade-release.yml
```

**自动级联更新 Action:**

```yaml
# spec-templates/.github/workflows/cascade-release.yml
name: Cascade Release to Projects

on:
  release:
    types: [published]

jobs:
  update-projects:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # 1. 解析 release notes，确定影响范围
      - name: Parse Release Info
        id: release
        run: |
          echo "version=${{ github.event.release.tag_name }}" >> $GITHUB_OUTPUT
          echo "breaking=${{ contains(github.event.release.body, 'BREAKING CHANGE') }}" >> $GITHUB_OUTPUT

      # 2. 查询受影响的项目（通过 GitHub API）
      - name: Find Affected Projects
        id: projects
        uses: actions/github-script@v6
        with:
          script: |
            // 查询所有使用此 submodule 的项目
            // 通过 GitHub Code Search API
            const query = 'org:company-name path:.gitmodules spec-templates';
            const result = await github.rest.search.code({ q: query });

            const projects = result.data.items.map(item => ({
              repo: item.repository.full_name,
              path: item.path
            }));

            core.setOutput('projects', JSON.stringify(projects));

      # 3. 为每个项目创建更新 PR
      - name: Create Update PRs
        uses: actions/github-script@v6
        with:
          script: |
            const projects = JSON.parse('${{ steps.projects.outputs.projects }}');
            const version = '${{ steps.release.outputs.version }}';
            const isBreaking = '${{ steps.release.outputs.breaking }}' === 'true';

            for (const project of projects) {
              const [owner, repo] = project.repo.split('/');

              // 创建分支
              const branchName = `template-update/${version}`;

              // 通过 API 创建 PR
              await github.rest.pulls.create({
                owner,
                repo,
                title: `${isBreaking ? '🔴 [Mandatory]' : '⭐ [Recommended]'} Update spec templates to ${version}`,
                head: branchName,
                base: 'main',
                body: `## 模板更新通知

                企业模板中心发布了新版本: **${version}**

                ${isBreaking ? '⚠️ **这是一个强制更新，必须在 30 天内完成**' : '💡 推荐更新以获得最新最佳实践'}

                ### 更新内容
                ${github.event.release.body}

                ### 操作步骤
                1. Review 本 PR 的变更
                2. 运行测试确保兼容性
                3. 批准并合并

                ### 自动操作
                合并后将自动：
                - 更新 submodule 到 ${version}
                - 重新生成模板文件
                - 运行合规性检查

                ---
                *This PR was automatically created by spec-templates release workflow*
                `
              });
            }
```

#### 4. 推荐更新流程（部门级模板）

**利用 Dependabot / Renovate Bot 自动检测并创建 PR**

```yaml
# payment-service/.github/dependabot.yml
version: 2
updates:
  # 监控 Git submodules 更新
  - package-ecosystem: "gitsubmodule"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "template-update"
    commit-message:
      prefix: "chore"
      prefix-development: "chore"
      include: "scope"

  # 自定义配置
    open-pull-requests-limit: 5
    reviewers:
      - "engineering-lead"
    assignees:
      - "team-lead"
```

**Dependabot 会自动**:
- 检测 submodule 有新版本
- 创建 PR 更新 submodule
- 请求指定的 reviewers
- 运行 CI 检查

#### 5. 覆盖审批流程（团队定制）

**场景**: 团队想使用自己的 plan 模板

```bash
# 1. 创建覆盖分支
git checkout -b override/custom-plan

# 2. 在 overrides 目录添加自定义模板
mkdir -p .specify/overrides
cp team-templates/microservice-plan.md .specify/overrides/plan.md

# 3. 更新配置，指定覆盖
cat > .specify/override-config.yaml <<EOF
overrides:
  plan-template:
    source: .specify/overrides/plan.md
    reason: |
      支付系统微服务架构需要特定的规划流程。
      已保留企业安全和合规要求。
    approved_by: []  # PR merge 即为审批
EOF

# 4. 提交
git add .specify/overrides/ .specify/override-config.yaml
git commit -m "feat: Add custom microservice plan template

Request override for plan-template with microservice-specific workflow.

Reason: Payment microservices architecture requires specific planning.

Compliance: All corporate security requirements are preserved.

Approval-Required: engineering-lead,architecture-team"

# 5. 创建 PR（自动通过 CODEOWNERS 要求审批）
gh pr create \
  --title "[Override Request] Custom microservice plan template" \
  --reviewer engineering-lead,architecture-team

# 6. CI 自动检查
# - 验证覆盖不违反策略
# - 检查自定义模板格式
# - 生成合规报告

# 7. 审批人 review 并批准
gh pr review --approve

# 8. 合并后生效
```

#### 6. 版本锁定机制（利用 Git Protected Tags）

**场景**: 锁定 constitution 模板到 v2.1.0

```bash
# === GitHub Repository Settings ===
# Settings → Tags → Protected tags

# 1. 创建 protected tag rule
Pattern: v*
Protection rules:
  ✅ Prevent tag deletion
  ✅ Prevent tag updates (force push)
  ✅ Require signed commits
  ✅ Restrict who can create matching tags
     → Only: @compliance-team, @security-vp

# === 在项目中锁定 ===
cd payment-service/.specify/templates

# 2. 锁定到特定 commit (tag)
git checkout v2.1.0

# 3. 提交锁定
cd ../..
git add .specify/templates
git commit -m "chore: Lock templates to v2.1.0 for SOC2 compliance

Locked-By: compliance-team
Reason: SOC2 audit requirement
Unlock-Requires: compliance-lead,security-vp,legal
Expires: 2026-06-01

Refs: AUDIT-2025-SOC2
Signed-off-by: Jane Smith <jane@company.com>"

# 4. 配置 Branch Protection 防止未经审批的解锁
# Settings → Branches → Branch protection rules
# Rule: main
# ✅ Require pull request before merging
# ✅ Require approvals: 2
# ✅ Require review from Code Owners
# ✅ Require status checks to pass
#    → spec-compliance-check
# ✅ Require signed commits
# ✅ Include administrators

# 5. CODEOWNERS 限制谁能修改 submodule
cat >> .github/CODEOWNERS <<EOF
# Spec templates submodule: 需要合规团队审批
.specify/templates  @compliance-team @security-vp
.gitmodules         @compliance-team @security-vp
EOF
```

**解锁流程**（6个月后）:

```bash
# 1. 创建解锁 PR
git checkout -b unlock/templates-v2.2

# 2. 更新 submodule
cd .specify/templates
git checkout v2.2.0
cd ../..

# 3. 提交
git add .specify/templates
git commit -s -m "chore: Unlock and update templates to v2.2.0

Unlock-Reason: SOC2 cycle completed, GDPR 2025 update required
Previous-Version: v2.1.0
New-Version: v2.2.0
Approved-By: compliance-lead,security-vp,legal

Changes:
- AI/ML governance section added
- GDPR 2025 privacy requirements updated
- Supply chain security requirements added

Risk-Assessment: Low (backward compatible, additive only)
Migration-Period: 30 days

Refs: AUDIT-2026-Q2
Signed-off-by: Jane Smith <jane@company.com>"

# 4. 创建 PR
gh pr create \
  --title "🔓 [Unlock] Update templates to v2.2.0" \
  --reviewer compliance-lead,security-vp,legal-counsel \
  --label critical,compliance

# 5. 需要所有 CODEOWNERS 批准才能合并（自动强制）
# 6. Signed commit 确保可追溯
# 7. Status checks 确保合规性
```

---

### 方案 B: Git Subtree（适合深度定制）

**适用场景**: 团队需要频繁修改模板，submodule 太重。

```bash
# 1. 初始添加（类似 submodule，但直接合并到主仓库）
git subtree add \
  --prefix .specify/templates \
  git@company.com/templates/spec-templates.git \
  v2.1.0 \
  --squash

# 2. 更新（拉取上游变更）
git subtree pull \
  --prefix .specify/templates \
  git@company.com/templates/spec-templates.git \
  v2.2.0 \
  --squash

# 3. 推送本地修改回上游（如果允许）
git subtree push \
  --prefix .specify/templates \
  git@company.com/templates/spec-templates.git \
  team-custom-branch

# 优势：
# - 历史更清晰（直接在主仓库）
# - 不需要额外的 submodule 步骤
# - 更容易本地修改

# 劣势：
# - 历史体积更大
# - 更新冲突处理复杂
```

---

### 方案 C: GitHub Packages / NPM（模板即依赖）

**适用场景**: 模板作为包发布，利用包管理器的依赖锁定机制。

```bash
# === 模板中心发布为 NPM 包 ===
cd spec-templates

# 1. package.json
cat > package.json <<EOF
{
  "name": "@company/spec-templates",
  "version": "2.1.0",
  "description": "Enterprise Spec-Kit Templates",
  "files": ["corporate", "department", "team"],
  "repository": "git@company.com/templates/spec-templates.git"
}
EOF

# 2. 发布到 GitHub Packages / 私有 NPM
npm publish

# === 项目中使用 ===
cd payment-service

# 3. 安装模板包
npm install --save-dev @company/spec-templates@2.1.0

# 4. package-lock.json 自动锁定版本
# {
#   "@company/spec-templates": {
#     "version": "2.1.0",
#     "resolved": "https://npm.pkg.github.com/...",
#     "integrity": "sha512-..."
#   }
# }

# 5. Renovate Bot 自动检测新版本并创建 PR
# renovate.json
{
  "extends": ["config:base"],
  "packageRules": [
    {
      "matchPackagePatterns": ["@company/spec-templates"],
      "matchUpdateTypes": ["major"],
      "labels": ["breaking", "mandatory"],
      "automerge": false,
      "assignees": ["@compliance-team"]
    }
  ]
}

# 优势：
# - 利用成熟的包管理生态（npm, yarn, pnpm）
# - 自动版本锁定（lock file）
# - Renovate/Dependabot 原生支持
# - 语义化版本（semver）

# 劣势：
# - 需要额外的包管理基础设施
# - 不太符合"纯配置"的直觉
```

---

## 🔒 策略执行（Branch Protection + Status Checks）

### 1. Branch Protection Rules（GitHub Settings）

```yaml
# Settings → Branches → Add rule

Branch name pattern: main

Protection rules:
  ✅ Require a pull request before merging
     - Require approvals: 2
     - Dismiss stale pull request approvals when new commits are pushed
     - Require review from Code Owners
     - Require approval of the most recent reviewable push

  ✅ Require status checks to pass before merging
     - Require branches to be up to date before merging
     - Status checks required:
       ✅ spec-compliance-check
       ✅ template-version-check
       ✅ policy-validation
       ✅ override-approval-check

  ✅ Require conversation resolution before merging

  ✅ Require signed commits

  ✅ Require linear history

  ✅ Include administrators (无人可绕过)

  ✅ Restrict who can push to matching branches
     - Only: @engineering-leads, @compliance-team

  ✅ Allow force pushes: Never

  ✅ Allow deletions: Never
```

### 2. Required Status Checks（CI）

```yaml
# .github/workflows/spec-compliance.yml
name: Spec Compliance Checks

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  # 检查 1: 模板版本合规性
  template-version-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: true  # 拉取 submodule

      - name: Check Template Version
        run: |
          cd .specify/templates
          CURRENT_COMMIT=$(git rev-parse HEAD)
          CURRENT_TAG=$(git describe --tags --exact-match 2>/dev/null || echo "untagged")

          echo "Current template commit: $CURRENT_COMMIT"
          echo "Current template tag: $CURRENT_TAG"

          # 读取锁定配置（如果有）
          if [ -f ../.template-lock ]; then
            REQUIRED_VERSION=$(cat ../.template-lock)
            echo "Required version: $REQUIRED_VERSION"

            if [ "$CURRENT_TAG" != "$REQUIRED_VERSION" ]; then
              echo "❌ Template version mismatch!"
              echo "Required: $REQUIRED_VERSION, Current: $CURRENT_TAG"
              exit 1
            fi
          fi

          echo "✅ Template version check passed"

  # 检查 2: 策略合规性
  policy-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: true

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install specify CLI
        run: pip install specify-cli

      - name: Validate Policy Compliance
        run: |
          # 读取项目标签和技术栈
          PROJECT_TAGS=$(cat .specify/project-tags.txt | tr '\n' ',')
          TECH_STACK=$(cat .specify/tech-stack.txt | tr '\n' ',')

          # 检查策略
          specify policy check \
            --tags "$PROJECT_TAGS" \
            --tech-stack "$TECH_STACK" \
            --templates-dir .specify/templates

  # 检查 3: 覆盖审批验证
  override-approval-check:
    runs-on: ubuntu-latest
    if: contains(github.event.pull_request.title, 'Override')
    steps:
      - uses: actions/checkout@v3

      - name: Check Override Approval
        uses: actions/github-script@v6
        with:
          script: |
            // 检查是否有覆盖配置
            const fs = require('fs');
            if (!fs.existsSync('.specify/override-config.yaml')) {
              console.log('No overrides, skipping');
              return;
            }

            // 读取覆盖配置
            const yaml = require('js-yaml');
            const config = yaml.load(fs.readFileSync('.specify/override-config.yaml', 'utf8'));

            // 检查 PR 是否有必要的审批
            const reviews = await github.rest.pulls.listReviews({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number
            });

            // 从 CODEOWNERS 获取必要的审批人
            // 或者从覆盖配置中读取
            const requiredApprovers = ['engineering-lead', 'architecture-team'];

            const approvals = reviews.data
              .filter(r => r.state === 'APPROVED')
              .map(r => r.user.login);

            const missing = requiredApprovers.filter(a => !approvals.some(approved => approved.includes(a)));

            if (missing.length > 0) {
              core.setFailed(`❌ Missing approvals from: ${missing.join(', ')}`);
            } else {
              console.log('✅ All required approvals received');
            }

  # 检查 4: 签名验证
  signature-verification:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Verify Commit Signatures
        run: |
          # 检查所有 commits 是否签名
          for commit in $(git rev-list origin/main..HEAD); do
            if ! git verify-commit $commit 2>/dev/null; then
              echo "❌ Commit $commit is not signed"
              exit 1
            fi
          done
          echo "✅ All commits are signed"
```

### 3. CODEOWNERS（自动要求审批）

```
# .github/CODEOWNERS

# === 模板相关（高权限） ===
# Submodule 指向（需要合规审批）
.specify/templates/          @compliance-team @security-vp
.gitmodules                  @compliance-team @security-vp

# 覆盖配置（需要工程审批）
.specify/override-config.yaml  @engineering-lead @architecture-team
.specify/overrides/            @engineering-lead @architecture-team

# 项目配置（需要 Tech Lead 审批）
.specify/config.yaml         @tech-lead @engineering-lead

# === 生成的模板文件（无需审批，自动生成） ===
# .claude/commands/  # 不在 CODEOWNERS 中，因为自动生成

# === 代码（正常审批） ===
*.py                         @backend-team
*.ts                         @frontend-team
```

---

## 📊 审计与追踪（纯 Git）

### 1. Git 原生审计

```bash
# === 查看所有模板变更历史 ===
git log --all -- .specify/templates

# === 查看谁修改了 submodule ===
git log --all -p -- .gitmodules

# === 查看特定模板版本的使用历史 ===
git log --all --grep="v2.1.0" --oneline

# === 查看签名验证 ===
git log --show-signature

# === 查看覆盖请求的历史 ===
git log --all --grep="Override" -- .specify/overrides/

# === 使用 git blame 追踪责任人 ===
git blame .specify/templates  # 谁锁定的版本

# === 使用 git reflog 查看所有操作 ===
git reflog --all
```

### 2. GitHub/GitLab 审计

```bash
# === 通过 GitHub API 查询 PR 审批历史 ===
gh api /repos/{owner}/{repo}/pulls/{pr}/reviews

# === 查询所有覆盖请求 PR ===
gh pr list --label "override-request" --state all --json number,title,mergedAt,reviews

# === 查询 Protected Branch 事件 ===
gh api /repos/{owner}/{repo}/events \
  | jq '.[] | select(.type == "PushEvent" or .type == "PullRequestEvent")'

# === 导出完整审计日志（JSON） ===
gh api /repos/{owner}/{repo}/events --paginate > audit-log.json

# === 查询 Signed Commits ===
gh api /repos/{owner}/{repo}/commits \
  | jq '.[] | select(.commit.verification.verified == true)'
```

### 3. 自动合规报告（基于 Git）

```yaml
# .github/workflows/compliance-report.yml
name: Weekly Compliance Report

on:
  schedule:
    - cron: '0 9 * * 1'  # 每周一早上 9 点
  workflow_dispatch:

jobs:
  generate-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # 拉取完整历史
          submodules: true

      - name: Generate Compliance Report
        run: |
          cat > compliance-report.md <<EOF
          # 合规性报告
          **生成时间**: $(date)
          **报告周期**: $(date -d '7 days ago' +%Y-%m-%d) ~ $(date +%Y-%m-%d)

          ## 1. 模板版本状态
          EOF

          # 检查当前模板版本
          cd .specify/templates
          CURRENT_TAG=$(git describe --tags)
          LATEST_TAG=$(git ls-remote --tags origin | tail -1 | awk -F/ '{print $3}')

          cat >> ../../compliance-report.md <<EOF
          - **当前版本**: $CURRENT_TAG
          - **最新版本**: $LATEST_TAG
          - **状态**: $([ "$CURRENT_TAG" == "$LATEST_TAG" ] && echo "✅ Up to date" || echo "⚠️ Update available")

          ## 2. 本周变更记录
          EOF

          # 查询本周的模板相关变更
          cd ../..
          git log --since='7 days ago' --oneline -- .specify/ >> compliance-report.md

          cat >> compliance-report.md <<EOF

          ## 3. 覆盖请求记录
          EOF

          # 查询本周的覆盖请求
          gh pr list \
            --label "override-request" \
            --state all \
            --search "created:>=$(date -d '7 days ago' +%Y-%m-%d)" \
            --json number,title,state,createdAt \
            --jq '.[] | "- #\(.number) \(.title) [\(.state)]"' \
            >> compliance-report.md

          cat >> compliance-report.md <<EOF

          ## 4. 签名验证状态
          EOF

          # 检查本周 commits 的签名状态
          for commit in $(git rev-list --since='7 days ago' HEAD); do
            if git verify-commit $commit 2>/dev/null; then
              echo "- ✅ $commit (signed)" >> compliance-report.md
            else
              echo "- ❌ $commit (unsigned)" >> compliance-report.md
            fi
          done

      - name: Send Report
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('compliance-report.md', 'utf8');

            // 创建 Issue
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: `📊 Weekly Compliance Report - ${new Date().toISOString().split('T')[0]}`,
              body: report,
              labels: ['compliance', 'report'],
              assignees: ['compliance-lead']
            });

            // 发送到 Slack（如果配置了 webhook）
            // ...
```

---

## 🚀 完整工作流示例

### 示例 1: 企业强制更新

```
1. 合规团队在 spec-templates 仓库修改模板
   ↓
2. 创建 PR → CODEOWNERS 要求 @compliance-lead 审批
   ↓
3. CI 检查通过（语法、版本号）
   ↓
4. 审批并合并
   ↓
5. 创建 Git Tag (v2.2.0)
   ↓
6. GitHub Release 自动发布
   ↓
7. Release Action 触发，查询所有使用 submodule 的项目
   ↓
8. 为每个项目自动创建 PR:
   - 更新 submodule 到 v2.2.0
   - 标记为 [Mandatory]
   - 请求 @team-lead review
   ↓
9. 团队收到通知，review PR
   ↓
10. 团队批准并合并
    ↓
11. 合并后 CI 自动:
    - 重新生成模板文件
    - 运行合规性检查
    - 更新审计日志
    ↓
12. Signed commit 记录到 Git 历史，完整可追溯
```

### 示例 2: 团队覆盖请求

```
1. 开发者创建覆盖分支，添加自定义模板到 .specify/overrides/
   ↓
2. 提交并创建 PR
   ↓
3. CODEOWNERS 自动要求 @engineering-lead 审批
   ↓
4. CI 自动检查:
   - 覆盖是否违反策略（Status Check）
   - 自定义模板格式是否正确
   - 生成合规报告（作为 PR comment）
   ↓
5. Engineering Lead review:
   - 查看 CI 报告
   - 检查自定义模板
   - 批准或请求修改
   ↓
6. 批准后合并（Branch Protection 确保必须有审批）
   ↓
7. 合并触发 post-merge hook:
   - 重新生成模板
   - 记录审计日志
   ↓
8. Git history 完整记录覆盖请求和审批过程
```

### 示例 3: 版本锁定到期

```
1. 每周 CI 自动检查锁定过期时间
   ↓
2. 发现 constitution 锁定将在 30 天后过期
   ↓
3. 自动创建提醒 Issue:
   - @compliance-team
   - 包含锁定信息和过期时间
   ↓
4. 合规团队决定更新:
   - 创建解锁 PR
   - 更新 submodule 到新版本
   ↓
5. PR 需要 3 个高权限审批（CODEOWNERS）:
   - @compliance-lead
   - @security-vp
   - @legal-counsel
   ↓
6. Branch Protection + Required Status Checks:
   - 必须所有 3 人批准
   - 必须 CI 检查通过
   - 必须 Signed commit
   ↓
7. 合并后，Protected Tag 防止回滚
   ↓
8. Git history 永久记录解锁决策
```

---

## 📦 开箱即用的工具

### 利用现有工具，无需重新开发

| 功能 | 工具 | 说明 |
|------|------|------|
| 依赖更新 | **Dependabot / Renovate** | 自动检测 submodule/subtree 更新 |
| CI/CD | **GitHub Actions / GitLab CI** | 策略检查、合规验证 |
| PR 管理 | **GitHub PR / GitLab MR** | 审批流程 |
| 权限管理 | **GitHub Teams / CODEOWNERS** | 自动审批人分配 |
| 通知 | **GitHub Notifications + Slack App** | 开箱即用 |
| 审计 | **Git log + GitHub API** | 原生支持 |
| 签名 | **GPG Signed Commits** | Git 原生 |
| 版本管理 | **Git Tags + Releases** | Git 原生 |
| 搜索 | **GitHub Code Search** | 查找使用模板的项目 |
| 分析 | **GitHub Insights** | 贡献、活跃度 |

---

## 📝 总结

### 完全复用 Git 生态的优势

| 需求 | 传统方案 | Git 生态方案 | 优势 |
|------|----------|-------------|------|
| **版本管理** | 自建版本系统 | Git tags | ✅ 成熟、可靠 |
| **审批流程** | 自建审批系统 | PR + CODEOWNERS | ✅ 零开发成本 |
| **权限控制** | 自建 RBAC | GitHub Teams + Protected branches | ✅ 开箱即用 |
| **自动化** | 自建 CI/CD | GitHub Actions | ✅ 云原生 |
| **通知** | 自建通知服务 | GitHub Notifications | ✅ 集成 Slack/Email |
| **审计** | 自建审计日志 | Git history + Signed commits | ✅ 不可篡改 |
| **依赖更新** | 自建推送机制 | Dependabot | ✅ 智能、自动 |
| **策略执行** | 自建策略引擎 | Branch Protection + Status Checks | ✅ 强制执行 |

### 核心价值

1. **零开发成本**: 100% 利用现有能力
2. **零学习成本**: 开发者已熟悉 Git/PR
3. **零运维成本**: 云服务，无需自建
4. **完全可审计**: Git history 天然审计链
5. **强制执行**: 无法绕过（Branch Protection）
6. **高可用**: GitHub/GitLab 的 SLA
7. **生态丰富**: 海量工具和集成

---

## 🎯 实施建议

1. **选择 Submodule 方案**（最符合 Git 原生）
2. **配置 Protected Branches**（策略强制执行）
3. **启用 Dependabot**（自动更新检测）
4. **配置 CODEOWNERS**（自动审批路由）
5. **编写 CI Workflows**（合规性检查）
6. **强制 Signed Commits**（审计追踪）
7. **利用 GitHub Releases**（版本发布）
8. **使用 GitHub API**（自动化集成）

**结果**: 一个完全基于 Git 生态、零额外开发、企业级的规范治理平台。

---

**文档版本**: v2.0 (Pure Git-Ecosystem)
**最后更新**: 2025-12-06
**核心理念**: 不重复造轮子，充分利用 Git 生态现有能力
