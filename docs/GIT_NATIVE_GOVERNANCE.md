# 基于 Git 原生机制的企业级规范治理方案
## Git-Native Governance for Enterprise Spec-Kit

---

## 🎯 核心理念

**不构建独立的审批后台，而是利用 Git 原生的 PR/Review 机制实现企业治理。**

### 设计原则

1. **Git-Native**: 所有审批通过 Git PR/MR 完成
2. **Code-as-Config**: 配置即代码，纳入版本控制
3. **CI-Enforced**: 通过 CI/CD 自动检查策略合规性
4. **Commit-Driven**: 关键信息通过 commit message 传递
5. **Transparent**: 所有变更可追溯、可审计

---

## 📐 总体架构

```
┌─────────────────────────────────────────────────────┐
│            企业模板中心仓库                           │
│   git@company.com/templates/spec-templates.git      │
│                                                      │
│   ├── corporate/          # 企业强制模板             │
│   ├── department/         # 部门推荐模板             │
│   ├── policies/           # 策略配置                 │
│   ├── .github/workflows/  # CI 检查                  │
│   └── CODEOWNERS          # 审批人配置               │
└─────────────────────────────────────────────────────┘
                        ↓ PR/MR 审批
┌─────────────────────────────────────────────────────┐
│         项目仓库 (使用模板)                          │
│   git@company.com/team/payment-service.git          │
│                                                      │
│   ├── .specify/                                      │
│   │   ├── config.yaml        # 模板源配置            │
│   │   ├── template-lock.yaml # 版本锁定              │
│   │   └── overrides/         # 团队覆盖记录          │
│   ├── .claude/commands/      # AI 命令模板           │
│   ├── memory/constitution.md # 项目宪法              │
│   └── .github/workflows/                            │
│       └── spec-compliance.yml # 合规性检查           │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 工作流程设计

### 1. 模板更新流程（企业 → 项目）

#### 场景：合规团队更新安全检查清单

**步骤：**

```bash
# 1. 合规团队在模板中心仓库创建 PR
cd spec-templates
git checkout -b update/security-checklist-v2.1

# 修改模板
vim corporate/security-checklist.md

# 提交，使用规范化的 commit message
git commit -m "feat(corporate): Update security checklist v2.1

Type: mandatory
Scope: corporate
Reason: Add OWASP Top 10 2023 requirements
Affects: all projects with tag:finance,healthcare
Review-Required: security-lead,compliance-team
Effective-Date: 2025-12-15

BREAKING CHANGE: All finance/healthcare projects must update within 30 days

Refs: SEC-2024-001
Signed-off-by: Jane Smith <jane@company.com>"

git push origin update/security-checklist-v2.1

# 2. 创建 PR（通过 gh cli 或 Web）
gh pr create \
  --title "[Mandatory] Update corporate security checklist v2.1" \
  --body "$(cat <<EOF
## 变更摘要
更新企业安全检查清单，新增 OWASP Top 10 2023 要求

## 影响范围
- **影响级别**: 🔴 强制（Mandatory）
- **影响项目**: 所有带 \`finance\`, \`healthcare\` 标签的项目
- **生效日期**: 2025-12-15
- **过渡期**: 30 天（至 2026-01-14）

## 变更详情
- ✅ 新增 GraphQL 注入防护检查
- ✅ 新增 JWT 安全配置验证
- ✅ 更新密码强度要求

## 审批要求
- [x] Security Lead (@security-lead)
- [ ] Compliance Team (@compliance-team)
- [ ] Engineering VP (@vp-eng)

## 迁移指南
受影响的项目会收到自动 PR，包含以下操作：
1. 更新 .specify/template-lock.yaml 中的版本
2. 更新 .claude/commands/checklist.md
3. 生成迁移检查清单

## 参考文档
- OWASP Top 10 2023: https://owasp.org/Top10/
- 内部安全政策: https://intranet.company.com/security

/cc @finance-teams @healthcare-teams
EOF
)" \
  --reviewer security-lead,compliance-team,vp-eng \
  --label "type:mandatory,scope:corporate,security"

# 3. CODEOWNERS 自动要求必要的审批人
# .github/CODEOWNERS 文件定义：
# corporate/*  @security-lead @compliance-team @vp-eng
# department/* @engineering-leads
# policies/*   @compliance-team

# 4. CI 自动检查
# - 验证 commit message 格式
# - 验证版本号递增
# - 运行模板语法检查
# - 生成影响分析报告

# 5. 审批人 review（通过 GitHub PR）
gh pr review 123 --approve --body "✅ Approved by Security Lead. OWASP 2023 compliance verified."

# 6. PR 合并后，自动触发推送到项目
# GitHub Actions 自动创建 PR 到所有受影响的项目
```

**自动化 CI 检查 (.github/workflows/template-update.yml):**

```yaml
name: Template Update Validation

on:
  pull_request:
    paths:
      - 'corporate/**'
      - 'department/**'
      - 'policies/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Validate Commit Message
        run: |
          # 检查 commit message 是否包含必要字段
          python scripts/validate-commit-message.py

      - name: Check Template Syntax
        run: |
          # 验证模板语法
          specify template validate --all

      - name: Analyze Impact
        run: |
          # 分析影响范围，生成报告
          python scripts/analyze-impact.py > impact-report.md

      - name: Post Impact Report
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('impact-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## 📊 影响分析报告\n\n' + report
            });

  auto-cascade:
    runs-on: ubuntu-latest
    if: github.event.pull_request.merged == true
    steps:
      - name: Create PRs to Affected Projects
        run: |
          # 读取 commit message 中的 Affects 字段
          # 自动创建 PR 到所有受影响的项目
          python scripts/cascade-update.py \
            --template corporate/security-checklist.md \
            --version v2.1.0 \
            --tags finance,healthcare
```

---

### 2. 团队覆盖模板流程（项目 → 审批）

#### 场景：支付团队想覆盖 plan-template 使用自己的微服务规划流程

**步骤：**

```bash
# 1. 开发者在项目仓库创建覆盖请求分支
cd payment-service
git checkout -b template-override/plan-template

# 2. 创建覆盖配置
mkdir -p .specify/overrides
cat > .specify/overrides/plan-template.yaml <<EOF
override:
  template: plan-template
  from_source: department
  to_source: team
  reason: |
    支付系统采用微服务架构，需要特定的服务拆分、
    API 网关设计、分布式事务处理等规划流程。
    部门通用模板不适用。

  custom_template_path: .specify/custom-templates/microservice-plan.md

  justification:
    - 微服务架构需要服务拆分设计
    - 需要 API Gateway 和服务发现规划
    - 需要分布式事务处理方案
    - 需要服务间通信协议定义

  approval_request:
    roles:
      - engineering-lead
      - architecture-team
    deadline: 2025-12-13

  compliance_check:
    - ✅ 不违反企业安全规范
    - ✅ 保留必要的审核流程
    - ✅ 与部门模板兼容
EOF

# 3. 添加自定义模板
cp team-templates/microservice-plan.md .specify/custom-templates/

# 4. 提交，commit message 包含关键信息
git add .specify/overrides/plan-template.yaml
git add .specify/custom-templates/microservice-plan.md

git commit -m "feat(override): Request override for plan-template

Type: override-request
Template: plan-template
From-Source: department
To-Source: team
Approval-Required: engineering-lead,architecture-team

## 覆盖原因
支付系统采用微服务架构，需要特定的规划流程包括：
- 服务拆分设计
- API Gateway 规划
- 分布式事务处理
- 服务间通信协议

## 合规性检查
- ✅ 保留企业安全要求
- ✅ 保留代码审核流程
- ✅ 兼容部门质量标准

## 审批人
@engineering-lead @architecture-team

Refs: ARCH-2024-015
Signed-off-by: John Doe <john@company.com>"

# 5. 创建 PR
gh pr create \
  --title "[Override Request] Use custom microservice plan template" \
  --body "$(cat <<EOF
## 📋 覆盖请求

**模板**: plan-template
**当前来源**: department (部门通用模板)
**请求来源**: team (团队定制模板)

## 🎯 覆盖原因

支付系统采用微服务架构，部门通用的单体应用规划模板不适用。需要包括：

1. **服务拆分设计**:
   - 按业务边界拆分服务
   - DDD 领域建模
   - 服务粒度评估

2. **API Gateway 规划**:
   - 路由规则设计
   - 认证授权集成
   - 限流熔断配置

3. **分布式事务处理**:
   - Saga 模式设计
   - 补偿机制
   - 最终一致性保证

4. **服务间通信**:
   - gRPC vs REST 选型
   - 消息队列集成
   - 服务发现机制

## ✅ 合规性检查

- ✅ **安全要求**: 保留企业安全检查流程
- ✅ **代码审核**: 保留 PR Review 机制
- ✅ **质量标准**: 保留测试覆盖率要求
- ✅ **文档要求**: 保留 API 文档规范

## 👥 审批要求

- [ ] Engineering Lead (@engineering-lead)
- [ ] Architecture Team (@architecture-team)

## 📎 参考文档

- [微服务规划模板](.specify/custom-templates/microservice-plan.md)
- [覆盖配置](.specify/overrides/plan-template.yaml)
- [架构设计文档](docs/architecture/microservices.md)

---

**⏰ 预计审批时间**: 2-3 个工作日
**📅 Deadline**: 2025-12-13

/cc @payment-team @backend-leads
EOF
)" \
  --reviewer engineering-lead,architecture-team \
  --label "type:override-request,template:plan,priority:normal"

# 6. CI 自动检查覆盖请求的合规性
# .github/workflows/override-validation.yml

# 7. 审批人通过 GitHub Review 审批
gh pr review 456 --approve --body "✅ Approved by Engineering Lead

微服务架构需求合理，自定义模板已审核：
- ✅ 包含必要的架构设计章节
- ✅ 保留安全和合规要求
- ✅ 符合公司微服务最佳实践

Condition: 需在下次季度架构评审中汇报实施效果。"

# 8. PR 合并后，自动更新配置
# - 更新 .specify/config.yaml 中的模板源优先级
# - 记录到审计日志
# - 触发模板重新生成
```

**覆盖请求验证 CI (.github/workflows/override-validation.yml):**

```yaml
name: Template Override Validation

on:
  pull_request:
    paths:
      - '.specify/overrides/**'

jobs:
  validate-override:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Parse Override Request
        id: parse
        run: |
          # 从 commit message 和 YAML 文件解析覆盖请求
          python scripts/parse-override-request.py > override-info.json

      - name: Check Policy Compliance
        run: |
          # 检查是否违反策略
          specify policy check-override \
            --config .specify/config.yaml \
            --override override-info.json

      - name: Validate Custom Template
        run: |
          # 验证自定义模板格式
          specify template validate .specify/custom-templates/

      - name: Check Approver Permissions
        uses: actions/github-script@v6
        with:
          script: |
            // 检查请求的审批人是否有权限
            const yaml = require('js-yaml');
            const fs = require('fs');
            const override = yaml.load(fs.readFileSync('.specify/overrides/plan-template.yaml'));

            // 从 CODEOWNERS 或团队配置获取有效审批人
            // 验证请求的审批人在列表中

      - name: Generate Compliance Report
        run: |
          # 生成合规性报告
          specify audit generate-override-report \
            --override override-info.json \
            --output compliance-report.md

      - name: Post Compliance Report
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('compliance-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '## 🔍 合规性检查报告\n\n' + report
            });

  require-approvals:
    runs-on: ubuntu-latest
    steps:
      - name: Check Required Approvals
        uses: actions/github-script@v6
        with:
          script: |
            // 确保所有必要的审批人都已批准
            const reviews = await github.rest.pulls.listReviews({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number
            });

            const requiredApprovers = ['engineering-lead', 'architecture-team'];
            const approvals = reviews.data
              .filter(r => r.state === 'APPROVED')
              .map(r => r.user.login);

            const missing = requiredApprovers.filter(a => !approvals.includes(a));

            if (missing.length > 0) {
              core.setFailed(`Missing approvals from: ${missing.join(', ')}`);
            }
```

---

### 3. 版本锁定与解锁流程

#### 场景：合规团队锁定 constitution 模板

**步骤：**

```bash
# 1. 合规团队在模板中心仓库创建锁定 PR
cd spec-templates
git checkout -b lock/constitution-v2.1

# 2. 更新锁定配置
cat >> policies/template-locks.yaml <<EOF
locks:
  constitution:
    version: v2.1.0
    sha256: abc123def456...
    locked_at: 2025-12-06T10:00:00Z
    locked_by: compliance-team
    reason: SOC2 审计要求，未经审批不得修改
    expires_at: 2026-06-01T00:00:00Z
    unlock_requires:
      approvers:
        - compliance-lead
        - security-vp
        - legal-counsel
      reason_required: true
      audit_trail: true
EOF

# 3. 提交
git commit -m "chore(lock): Lock constitution template v2.1.0

Type: template-lock
Template: constitution
Version: v2.1.0
Reason: SOC2 audit compliance requirement
Expires: 2026-06-01
Unlock-Requires: compliance-lead,security-vp,legal-counsel

This lock prevents any modifications to the constitution template
without explicit approval from compliance, security, and legal teams.

All projects must use exactly version v2.1.0 for SOC2 compliance.

Refs: AUDIT-2025-SOC2
Signed-off-by: Jane Smith <jane@company.com>"

# 4. 创建 PR（需要高权限审批）
gh pr create \
  --title "[Critical] Lock constitution template for SOC2 compliance" \
  --reviewer compliance-lead,security-vp,legal-counsel \
  --label "type:lock,critical,security"

# 5. 合并后，CI 自动推送锁定到所有项目
# 每个项目的 .specify/template-lock.yaml 会自动更新
```

**解锁流程（6个月后需要更新）：**

```bash
# 1. 创建解锁请求 PR
git checkout -b unlock/constitution-v2.2-review

# 2. 修改锁定配置，添加解锁申请
cat > policies/unlock-requests/constitution-v2.2.yaml <<EOF
unlock_request:
  template: constitution
  current_version: v2.1.0
  locked_since: 2025-12-06
  requesting_unlock_for:
    reason: |
      SOC2 审计周期结束，需要更新模板以包含新的合规要求：
      - 增加 AI/ML 模型治理章节
      - 更新数据隐私条款（GDPR 2025）
      - 增加供应链安全要求

    proposed_new_version: v2.2.0
    changes_summary:
      - feat: Add AI/ML governance section
      - feat: Update GDPR 2025 privacy requirements
      - feat: Add supply chain security requirements

  approvals_required:
    - role: compliance-lead
      status: pending
    - role: security-vp
      status: pending
    - role: legal-counsel
      status: pending

  timeline:
    review_deadline: 2026-06-15
    implementation_deadline: 2026-07-01
EOF

# 3. 提交并创建 PR
git commit -m "feat(unlock): Request unlock constitution for v2.2.0 update

Type: unlock-request
Template: constitution
Current-Version: v2.1.0
Proposed-Version: v2.2.0
Reason: SOC2 cycle completed, GDPR 2025 update needed

## 解锁原因
当前锁定的 v2.1.0 已使用 6 个月，需要解锁以进行以下更新：
- AI/ML 模型治理（新业务需求）
- GDPR 2025 合规（法规要求）
- 供应链安全（行业最佳实践）

## 风险评估
- ✅ 低风险：仅新增章节，不修改现有要求
- ✅ 向后兼容：v2.1.0 内容完整保留
- ✅ 过渡期：30天试用期

## 审批要求
@compliance-lead @security-vp @legal-counsel

Refs: AUDIT-2026-Q2
Signed-off-by: Jane Smith <jane@company.com>"

gh pr create \
  --title "[Unlock Request] Update constitution to v2.2.0" \
  --reviewer compliance-lead,security-vp,legal-counsel \
  --label "type:unlock-request,critical,compliance"
```

---

## 🔐 Commit Message 规范（承载关键信息）

### 标准格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 扩展字段（用于治理）

```bash
git commit -m "feat(corporate): Update security checklist v2.1

Type: mandatory | recommended | optional
Scope: corporate | department | team
Template: <template-name>
Version: <version>
Reason: <reason>
Affects: <project-tags>
Review-Required: <roles>
Effective-Date: <date>
Unlock-Requires: <roles>  # 用于锁定
From-Source: <source>      # 用于覆盖
To-Source: <source>        # 用于覆盖
Approval-Required: <roles> # 用于覆盖

<详细描述>

BREAKING CHANGE: <breaking-change-description>

Refs: <issue-id>
Signed-off-by: <name> <email>"
```

### 解析工具

```python
# scripts/parse-commit-message.py
import re
from typing import Dict, Any

def parse_commit_message(message: str) -> Dict[str, Any]:
    """
    解析 commit message，提取治理相关字段
    """
    lines = message.split('\n')

    metadata = {}

    # 解析扩展字段
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip().lower().replace('-', '_')
            value = value.strip()

            if key in ['type', 'scope', 'template', 'version', 'reason',
                       'affects', 'review_required', 'effective_date',
                       'unlock_requires', 'from_source', 'to_source',
                       'approval_required']:
                metadata[key] = value

    # 解析 BREAKING CHANGE
    breaking_match = re.search(r'BREAKING CHANGE:(.*?)(?=\n\n|\nRefs:|\Z)', message, re.DOTALL)
    if breaking_match:
        metadata['breaking_change'] = breaking_match.group(1).strip()

    # 解析 Refs
    refs_match = re.search(r'Refs:\s*(.+)', message)
    if refs_match:
        metadata['refs'] = refs_match.group(1).strip()

    # 解析 Signed-off-by
    sign_match = re.search(r'Signed-off-by:\s*(.+)', message)
    if sign_match:
        metadata['signed_by'] = sign_match.group(1).strip()

    return metadata

# 使用示例
message = """feat(corporate): Update security checklist v2.1

Type: mandatory
Scope: corporate
Template: security-checklist
Version: v2.1.0
Reason: Add OWASP Top 10 2023 requirements
Affects: finance,healthcare
Review-Required: security-lead,compliance-team
Effective-Date: 2025-12-15

BREAKING CHANGE: All finance/healthcare projects must update within 30 days

Refs: SEC-2024-001
Signed-off-by: Jane Smith <jane@company.com>
"""

metadata = parse_commit_message(message)
print(metadata)
# {
#   'type': 'mandatory',
#   'scope': 'corporate',
#   'template': 'security-checklist',
#   'version': 'v2.1.0',
#   'affects': 'finance,healthcare',
#   ...
# }
```

---

## 🤖 自动化流程（CI/CD）

### 1. 模板中心仓库 CI

```yaml
# .github/workflows/template-governance.yml
name: Template Governance

on:
  pull_request:
    branches: [main]

jobs:
  validate-change:
    runs-on: ubuntu-latest
    steps:
      # 1. 解析 commit message
      - name: Parse Commit Metadata
        id: metadata
        run: |
          python scripts/parse-commit-message.py \
            --commit "${{ github.event.pull_request.head.sha }}" \
            --output metadata.json

      # 2. 验证必要字段
      - name: Validate Required Fields
        run: |
          python scripts/validate-metadata.py metadata.json

      # 3. 检查版本号
      - name: Check Version Increment
        run: |
          python scripts/check-version.py \
            --template $(jq -r .template metadata.json) \
            --new-version $(jq -r .version metadata.json)

      # 4. 分析影响范围
      - name: Analyze Impact
        run: |
          python scripts/analyze-impact.py \
            --affects $(jq -r .affects metadata.json) \
            --output impact-report.md

      # 5. 检查审批人权限
      - name: Verify Reviewers
        run: |
          python scripts/verify-reviewers.py \
            --required $(jq -r .review_required metadata.json) \
            --pr-number ${{ github.event.pull_request.number }}

      # 6. 发布影响报告
      - name: Post Impact Report
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('impact-report.md', 'utf8');
            await github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });

  cascade-update:
    runs-on: ubuntu-latest
    if: github.event.pull_request.merged == true
    needs: validate-change
    steps:
      # PR 合并后，自动推送到受影响的项目
      - name: Cascade Template Update
        run: |
          # 读取元数据
          TEMPLATE=$(jq -r .template metadata.json)
          VERSION=$(jq -r .version metadata.json)
          AFFECTS=$(jq -r .affects metadata.json)

          # 查询受影响的项目（从内部 API 或配置）
          python scripts/find-affected-projects.py \
            --tags "$AFFECTS" \
            --output projects.json

          # 为每个项目创建更新 PR
          cat projects.json | jq -r '.[]' | while read PROJECT_REPO; do
            python scripts/create-update-pr.py \
              --target-repo "$PROJECT_REPO" \
              --template "$TEMPLATE" \
              --version "$VERSION" \
              --metadata metadata.json
          done
```

### 2. 项目仓库 CI

```yaml
# .github/workflows/spec-compliance.yml
name: Spec Compliance Check

on:
  pull_request:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # 每周检查一次

jobs:
  check-compliance:
    runs-on: ubuntu-latest
    steps:
      # 1. 检查模板版本是否符合锁定要求
      - name: Check Template Versions
        run: |
          specify template check-compliance \
            --config .specify/config.yaml \
            --lock .specify/template-lock.yaml

      # 2. 检查策略合规性
      - name: Check Policy Compliance
        run: |
          specify policy check \
            --project-tags $(cat .specify/project-tags.txt) \
            --tech-stack $(cat .specify/tech-stack.txt)

      # 3. 验证覆盖是否已审批
      - name: Verify Overrides
        run: |
          specify override verify \
            --overrides-dir .specify/overrides

      # 4. 生成合规报告
      - name: Generate Compliance Report
        run: |
          specify audit compliance-report \
            --output compliance-report.md

      # 5. 如果不合规，阻止合并
      - name: Fail on Non-Compliance
        if: failure()
        run: |
          echo "❌ 项目不符合企业规范要求，请查看合规报告"
          exit 1

  check-lock-expiry:
    runs-on: ubuntu-latest
    steps:
      # 检查锁定是否即将过期
      - name: Check Lock Expiry
        run: |
          python scripts/check-lock-expiry.py \
            --lock-file .specify/template-lock.yaml \
            --warn-days 30

      # 如果即将过期，创建提醒 issue
      - name: Create Reminder Issue
        if: env.LOCKS_EXPIRING == 'true'
        uses: actions/github-script@v6
        with:
          script: |
            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: '⚠️ 模板锁定即将过期',
              body: process.env.EXPIRY_REPORT,
              labels: ['compliance', 'reminder']
            });
```

---

## 📊 审计与追踪（基于 Git 历史）

### 完整的审计链

```bash
# 1. 查看模板变更历史
cd spec-templates
git log --all --grep="Type: mandatory" --oneline

# 2. 查看特定模板的所有变更
git log --all -- corporate/constitution.md

# 3. 查看谁批准了某个变更
gh pr view 123 --json reviews

# 4. 追踪模板在项目中的应用
cd payment-service
git log --all --grep="Template: security-checklist"

# 5. 查看覆盖请求的审批历史
gh pr list --label "type:override-request" --state merged --json number,title,mergedAt,reviews

# 6. 生成合规报告（基于 Git 历史）
specify audit report \
  --from 2025-11-01 \
  --to 2025-12-01 \
  --format pdf \
  --output audit-report-2025-11.pdf
```

### 审计报告生成器

```python
# scripts/generate-audit-report.py
import subprocess
import json
from datetime import datetime, timedelta

def generate_audit_report(from_date: str, to_date: str) -> dict:
    """
    基于 Git 历史生成审计报告
    """
    report = {
        'period': {'from': from_date, 'to': to_date},
        'template_updates': [],
        'override_requests': [],
        'policy_violations': [],
        'lock_changes': []
    }

    # 1. 查询模板更新
    cmd = f"""
    git log --all \
      --since="{from_date}" --until="{to_date}" \
      --grep="Type: mandatory\\|Type: recommended" \
      --format="%H|%an|%ae|%ai|%s"
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        commit_hash, author, email, date, subject = line.split('|')

        # 获取完整 commit message
        msg = subprocess.run(
            f"git show -s --format=%B {commit_hash}",
            shell=True, capture_output=True, text=True
        ).stdout

        # 解析元数据
        metadata = parse_commit_message(msg)

        report['template_updates'].append({
            'commit': commit_hash,
            'author': f"{author} <{email}>",
            'date': date,
            'subject': subject,
            'metadata': metadata
        })

    # 2. 查询覆盖请求（通过 GitHub API）
    # gh api /repos/{owner}/{repo}/pulls?state=closed&labels=override-request

    # 3. 查询策略违规（通过 CI 失败记录）
    # 分析 GitHub Actions 运行记录

    # 4. 查询锁定变更
    # git log --all -- policies/template-locks.yaml

    return report
```

---

## 🎨 最佳实践示例

### 1. CODEOWNERS 配置

```
# .github/CODEOWNERS

# 企业级强制模板：需要最高权限审批
/corporate/*                    @compliance-team @security-vp @cto

# 部门级推荐模板：需要工程主管审批
/department/*                   @engineering-leads @tech-leads

# 团队级模板：团队自己维护
/team/*                         @team-leads

# 策略配置：需要合规和工程双重审批
/policies/*                     @compliance-team @engineering-vp

# 锁定配置：需要最高权限
/policies/template-locks.yaml   @compliance-lead @security-vp @legal-counsel

# 覆盖请求：项目中的覆盖需要对应审批人
# 在项目仓库的 CODEOWNERS
/.specify/overrides/*           @engineering-lead @architecture-team
```

### 2. PR 模板

```markdown
<!-- .github/PULL_REQUEST_TEMPLATE/template_update.md -->

## 模板更新 PR

### 📋 基本信息

- **模板名称**: <!-- 如: security-checklist -->
- **当前版本**: <!-- 如: v2.0.0 -->
- **新版本**: <!-- 如: v2.1.0 -->
- **变更类型**: <!-- mandatory / recommended / optional -->
- **变更范围**: <!-- corporate / department / team -->

### 🎯 变更原因

<!-- 为什么需要这次更新？关联的需求或合规要求是什么？ -->

### 📊 影响范围

- **影响的项目标签**: <!-- 如: finance, healthcare -->
- **预计影响项目数**: <!-- 自动填充 or 估算 -->
- **生效日期**: <!-- YYYY-MM-DD -->
- **过渡期**: <!-- 如: 30天 -->

### 📝 变更详情

<!-- 列出主要变更点 -->

- [ ] 变更 1
- [ ] 变更 2
- [ ] 变更 3

### ✅ 合规性检查

- [ ] 已通过模板语法验证
- [ ] 已通过策略合规检查
- [ ] 已生成影响分析报告
- [ ] 已通知受影响团队

### 👥 审批要求

<!-- 根据 CODEOWNERS 自动填充 -->

- [ ] @security-lead
- [ ] @compliance-team

### 🔗 参考文档

<!-- 相关文档链接 -->

- Issue: #
- 规范文档:
- 迁移指南:

---

**⚠️ 重要提示**: 合并此 PR 将自动向受影响的项目创建更新 PR。
```

### 3. 项目配置示例

```yaml
# .specify/config.yaml (项目仓库)

# 项目元数据
project:
  name: payment-gateway
  tags:
    - finance
    - payment
    - pci-dss
  tech_stack:
    - python
    - fastapi
    - postgresql
    - redis
  team: backend-payments
  owner: john.doe@company.com

# 模板源（优先级由高到低）
template_sources:
  # 企业级（强制）
  corporate:
    type: git
    url: git@company.com/templates/spec-templates.git
    path: corporate
    branch: main
    priority: 1
    enforce: true

  # 部门级（推荐）
  department:
    type: git
    url: git@company.com/templates/spec-templates.git
    path: department
    branch: main
    priority: 2
    enforce: false

  # 团队级（可选）
  team:
    type: git
    url: git@company.com/backend/team-templates.git
    path: templates
    branch: main
    priority: 3
    enforce: false

# 覆盖记录（自动生成，PR 合并后更新）
overrides:
  plan-template:
    from_source: department
    to_source: team
    reason: 微服务架构特殊需求
    approved_by: engineering-lead,architecture-team
    approved_at: 2025-12-06T15:30:00Z
    pr_number: 456
    expires_at: 2026-12-06  # 一年后重新评估

# 合规性配置
compliance:
  auto_update: true  # 自动接受强制模板更新
  ci_enforcement: true  # CI 强制检查合规性
  weekly_audit: true  # 每周自动审计
```

---

## 📈 优势总结

### 相比独立审批系统的优势

| 维度 | Git-Native 方案 | 独立审批系统 | 优势 |
|------|----------------|--------------|------|
| **学习成本** | ✅ 开发者熟悉 Git/PR 流程 | ❌ 需要学习新系统 | **无额外学习成本** |
| **开发成本** | ✅ 利用现有 Git 基础设施 | ❌ 需要构建完整后台 | **节省 80% 开发成本** |
| **审批透明** | ✅ PR Review 公开可见 | ⚠️ 取决于系统设计 | **完全透明** |
| **审计追踪** | ✅ Git 历史天然审计链 | ❌ 需要单独实现 | **自动审计** |
| **权限管理** | ✅ CODEOWNERS + GitHub Teams | ❌ 需要单独 RBAC | **复用现有权限** |
| **通知集成** | ✅ GitHub 通知 + Slack 集成 | ❌ 需要单独实现 | **开箱即用** |
| **离线工作** | ✅ Git 支持离线操作 | ❌ 需要在线系统 | **更灵活** |
| **工具集成** | ✅ gh CLI, IDE 插件 | ⚠️ 需要定制开发 | **生态丰富** |
| **版本控制** | ✅ Git 原生版本管理 | ❌ 需要单独实现 | **内置版本控制** |
| **回滚能力** | ✅ Git revert 即可 | ⚠️ 需要单独实现 | **简单可靠** |

### 核心价值

1. **零学习成本**: 开发者已经熟悉 PR/Review 流程
2. **零基础设施成本**: 完全基于 Git + GitHub/GitLab
3. **完全透明**: 所有变更、审批、审计都在 Git 历史中
4. **自动审计**: Git 历史即审计日志，无需单独记录
5. **强制执行**: CI/CD 自动检查，无法绕过
6. **灵活扩展**: 可以逐步添加更多 CI 检查

---

## 🚀 实施建议

### Phase 1: 基础设施（2周）

1. **建立模板中心仓库**
   - 创建 spec-templates 仓库
   - 组织 corporate/department/team 目录结构
   - 配置 CODEOWNERS

2. **定义 Commit Message 规范**
   - 创建 commit message 模板
   - 编写解析脚本
   - 配置 commit-msg hook

3. **实现基础 CI**
   - commit message 验证
   - 模板语法检查
   - 基础影响分析

### Phase 2: 治理机制（3周）

4. **实现策略引擎**
   - 策略配置格式
   - 策略检查脚本
   - CI 集成

5. **实现级联更新**
   - 受影响项目识别
   - 自动 PR 创建
   - 更新通知

6. **实现覆盖审批**
   - 覆盖请求 PR 模板
   - 覆盖验证 CI
   - 审批流程 CI

### Phase 3: 自动化与优化（2周）

7. **完善审计**
   - 审计报告生成
   - 合规性仪表板
   - 定期检查

8. **开发者工具**
   - CLI 命令优化
   - PR 模板完善
   - 文档和培训

### Phase 4: 推广与迭代（持续）

9. **试点推广**
   - 选择 2-3 个团队试点
   - 收集反馈
   - 迭代优化

10. **全面推广**
    - 内部培训
    - 文档完善
    - 持续支持

---

## 📚 附录

### A. 相关工具

- **Git**: 版本控制
- **GitHub/GitLab**: 代码托管 + PR/MR
- **GitHub Actions / GitLab CI**: 自动化
- **gh CLI**: GitHub 命令行工具
- **specify CLI**: 模板管理（扩展）

### B. 参考资源

- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)

---

**文档版本**: v1.0
**最后更新**: 2025-12-06
**状态**: 完整方案
