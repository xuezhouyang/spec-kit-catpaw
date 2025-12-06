"""
Specify CLI: Feature Worktree Management Commands
实现基于 Git Worktree 的 Feature 管理

用法:
  specify feature create <name>      - 创建新 feature（worktree）
  specify feature switch <name>      - 切换到 feature
  specify feature list              - 列出所有 features
  specify feature complete <name>    - 完成 feature 并上报 constitution
  specify feature cleanup <name>     - 清理 feature worktree
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import click


class FeatureWorktreeManager:
    """管理基于 Git Worktree 的 Feature 开发"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.git_dir = self.project_root / ".git"
        self.worktree_base = self.project_root.parent

    def create_feature(self, feature_name: str, description: str = "") -> Dict:
        """
        创建新 feature（使用 Git Worktree）

        返回: {
            'branch': '001-payment-gateway',
            'worktree_path': '/home/user/payment-service-001',
            'feature_number': '001'
        }
        """
        print(f"📋 Creating feature: {feature_name}")
        print()

        # 1. 获取下一个 feature 编号
        feature_number = self._get_next_feature_number()
        branch_name = f"{feature_number}-{feature_name}"

        print(f"1️⃣  Creating Git worktree...")

        # 2. 创建 worktree 目录
        worktree_name = f"{self.project_root.name}-{feature_number}"
        worktree_path = self.worktree_base / worktree_name

        # 3. 创建分支和 worktree
        try:
            # 创建新分支
            subprocess.run(
                ["git", "branch", branch_name],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )

            # 添加 worktree
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=self.project_root,
                check=True,
                capture_output=True
            )

            print(f"   ✅ Worktree created at: {worktree_path}")
            print(f"   ✅ Branch: {branch_name}")
            print()

        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to create worktree: {e.stderr.decode()}")
            return None

        # 4. 初始化 feature 上下文
        print(f"2️⃣  Initializing feature context...")
        self._initialize_feature_context(
            worktree_path,
            feature_name,
            feature_number,
            description
        )

        # 5. 生成模板
        print(f"3️⃣  Generating templates...")
        self._generate_templates(worktree_path)

        # 6. 设置 AI Agent 上下文
        print(f"4️⃣  Setting up AI Agent context...")
        self._setup_agent_context(
            worktree_path,
            feature_name,
            feature_number
        )

        # 7. 保存 feature 元数据
        self._save_feature_metadata(
            worktree_path,
            feature_name,
            feature_number,
            branch_name,
            description
        )

        print()
        print(f"✅ Feature workspace ready!")
        print(f"   Directory: {worktree_path}")
        print(f"   Branch: {branch_name}")
        print()
        print(f"💡 To switch to this feature: specify feature switch {feature_name}")
        print(f"💡 To list all features: specify feature list")
        print()

        return {
            'branch': branch_name,
            'worktree_path': str(worktree_path),
            'feature_number': feature_number,
            'feature_name': feature_name
        }

    def _get_next_feature_number(self) -> str:
        """获取下一个 feature 编号（001, 002, ...）"""
        # 获取所有 worktrees
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

        # 解析已有的 feature 编号
        max_number = 0
        for line in result.stdout.split('\n'):
            if line.startswith('branch refs/heads/'):
                branch = line.split('/')[-1]
                # 提取编号（如 001-payment-gateway -> 001）
                if branch and branch[0].isdigit():
                    try:
                        number = int(branch.split('-')[0])
                        max_number = max(max_number, number)
                    except ValueError:
                        pass

        # 返回下一个编号
        return f"{max_number + 1:03d}"

    def _initialize_feature_context(
        self,
        worktree_path: Path,
        feature_name: str,
        feature_number: str,
        description: str
    ):
        """初始化 feature 的上下文文件"""

        # 复制 base constitution
        main_constitution = self.project_root / "memory" / "constitution.md"
        feature_constitution = worktree_path / "memory" / "constitution.md"

        if main_constitution.exists():
            feature_constitution.parent.mkdir(parents=True, exist_ok=True)

            # 读取 base constitution
            with open(main_constitution, 'r') as f:
                base_content = f.read()

            # 添加 feature metadata
            feature_content = f"""# Project Constitution (Feature: {feature_name})

> **Feature**: {feature_name} (#{feature_number})
> **Created**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> **Description**: {description or 'No description provided'}
> **Base Version**: main

---

{base_content}

---

## Feature-Specific Rules

<!-- Add feature-specific constitution rules below -->
<!-- These will be reviewed for merging back to main when feature is completed -->

"""
            with open(feature_constitution, 'w') as f:
                f.write(feature_content)

            print(f"   ✅ Constitution initialized")

    def _generate_templates(self, worktree_path: Path):
        """生成 feature 的模板文件"""
        # 这里调用现有的 specify generate 逻辑
        # 简化示例：直接创建必要目录
        (worktree_path / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Templates generated")

    def _setup_agent_context(
        self,
        worktree_path: Path,
        feature_name: str,
        feature_number: str
    ):
        """设置 AI Agent 上下文文件（CLAUDE.md 等）"""

        claude_md = worktree_path / "CLAUDE.md"

        content = f"""# Feature: {feature_name} (#{feature_number})

## Context

This feature is being developed in an isolated Git worktree.

**Worktree Location**: {worktree_path}
**Branch**: {feature_number}-{feature_name}
**Created**: {datetime.now().strftime('%Y-%m-%d')}

## Constitution

This feature has its own `memory/constitution.md` which starts from the main branch
and can be extended with feature-specific rules.

When the feature is completed, constitution changes will be reviewed for merging
back to the main branch.

## Development History

<!-- AI Agent will append development progress here -->

### {datetime.now().strftime('%Y-%m-%d')}
- Feature created
- Worktree initialized
- Ready for development

---

*This file is automatically managed by Specify CLI*
"""

        with open(claude_md, 'w') as f:
            f.write(content)

        print(f"   ✅ CLAUDE.md initialized")

    def _save_feature_metadata(
        self,
        worktree_path: Path,
        feature_name: str,
        feature_number: str,
        branch_name: str,
        description: str
    ):
        """保存 feature 元数据"""

        metadata_dir = worktree_path / ".specify"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            'feature_name': feature_name,
            'feature_number': feature_number,
            'branch_name': branch_name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'worktree_path': str(worktree_path),
            'status': 'active'
        }

        with open(metadata_dir / "feature-metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

    def list_features(self) -> List[Dict]:
        """列出所有 feature worktrees"""

        # 获取所有 worktrees
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            check=True
        )

        worktrees = []
        current_worktree = {}

        for line in result.stdout.split('\n'):
            if line.startswith('worktree '):
                if current_worktree:
                    worktrees.append(current_worktree)
                current_worktree = {'path': line.split(' ', 1)[1]}

            elif line.startswith('branch refs/heads/'):
                current_worktree['branch'] = line.split('/')[-1]

            elif line.startswith('HEAD '):
                current_worktree['commit'] = line.split(' ')[1]

        if current_worktree:
            worktrees.append(current_worktree)

        # 过滤出 feature worktrees（排除 main/master）
        features = []
        for wt in worktrees:
            branch = wt.get('branch', '')
            if branch and branch not in ['main', 'master']:
                # 读取 metadata
                metadata_file = Path(wt['path']) / ".specify" / "feature-metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    wt.update(metadata)

                features.append(wt)

        return features

    def switch_feature(self, feature_name: str):
        """切换到指定 feature"""

        features = self.list_features()

        # 查找 feature
        target_feature = None
        for feature in features:
            if feature.get('feature_name') == feature_name:
                target_feature = feature
                break

        if not target_feature:
            print(f"❌ Feature '{feature_name}' not found")
            print(f"\nAvailable features:")
            for f in features:
                print(f"  - {f.get('feature_name')}")
            return

        worktree_path = target_feature['path']

        print(f"📂 Switching to feature: {feature_name}")
        print(f"   Worktree: {worktree_path}")
        print(f"   Branch: {target_feature['branch']}")
        print()

        # 选项
        print("Options:")
        print("  1. Change directory (cd)")
        print("  2. Open in new terminal")
        print("  3. Open in VS Code")
        print()

        choice = input("Choose (1/2/3): ").strip()

        if choice == '1':
            print(f"\n💡 Run: cd {worktree_path}")

        elif choice == '2':
            # 打开新终端（Linux/Mac）
            terminal_cmd = f"gnome-terminal --working-directory={worktree_path}"
            try:
                subprocess.Popen(terminal_cmd, shell=True)
                print(f"✅ Opened in new terminal")
            except:
                print(f"💡 Manually open terminal at: {worktree_path}")

        elif choice == '3':
            # 打开 VS Code
            try:
                subprocess.run(["code", str(worktree_path)], check=True)
                print(f"✅ Opened in VS Code")
            except:
                print(f"💡 Run: code {worktree_path}")

    def complete_feature(self, feature_name: str, auto_pr: bool = True):
        """
        完成 feature 并上报 constitution 变更

        步骤：
        1. 分析 constitution 变更
        2. 询问是否合并到 main
        3. 创建 PR
        4. 合并 feature
        5. 清理 worktree
        """

        print(f"🎉 Completing feature: {feature_name}")
        print()

        # 查找 feature
        features = self.list_features()
        target_feature = None
        for feature in features:
            if feature.get('feature_name') == feature_name:
                target_feature = feature
                break

        if not target_feature:
            print(f"❌ Feature '{feature_name}' not found")
            return

        worktree_path = Path(target_feature['path'])
        branch_name = target_feature['branch']

        # 1. 分析 constitution 变更
        print(f"1️⃣  Analyzing constitution changes...")
        diff = self._compare_constitution(worktree_path, branch_name)

        if not diff['has_changes']:
            print(f"   ✅ No constitution changes")
        else:
            print(f"   📊 Found constitution changes:")
            print(f"      - Added sections: {len(diff['added_sections'])}")
            print(f"      - Modified sections: {len(diff['modified_sections'])}")
            print()

            # 显示详细 diff
            self._display_constitution_diff(diff)

            # 询问是否合并
            print()
            merge_choice = input("Merge these changes to main constitution? (y/n): ")

            if merge_choice.lower() == 'y':
                self._prepare_constitution_merge(diff, branch_name)

        # 2. 创建 PR（如果需要）
        if auto_pr:
            print()
            print(f"2️⃣  Creating Pull Request...")
            self._create_feature_pr(branch_name, feature_name, diff)

        # 3. 清理 worktree（在 PR 合并后）
        print()
        cleanup_choice = input("Remove worktree now? (y/n): ")

        if cleanup_choice.lower() == 'y':
            print()
            print(f"3️⃣  Cleaning up worktree...")
            self.cleanup_feature(feature_name)

        print()
        print(f"✅ Feature completion initiated!")

    def _compare_constitution(
        self,
        worktree_path: Path,
        branch_name: str
    ) -> Dict:
        """比较 feature constitution 和 main 的差异"""

        feature_const = worktree_path / "memory" / "constitution.md"
        main_const = self.project_root / "memory" / "constitution.md"

        if not feature_const.exists() or not main_const.exists():
            return {'has_changes': False}

        # 读取内容
        with open(feature_const, 'r') as f:
            feature_content = f.read()

        with open(main_const, 'r') as f:
            main_content = f.read()

        # 简单比较（实际应该做结构化 diff）
        if feature_content == main_content:
            return {'has_changes': False}

        # 解析 sections（简化版）
        feature_sections = self._parse_markdown_sections(feature_content)
        main_sections = self._parse_markdown_sections(main_content)

        added_sections = []
        modified_sections = []

        for title, content in feature_sections.items():
            if title not in main_sections:
                added_sections.append({'title': title, 'content': content})
            elif content != main_sections[title]:
                modified_sections.append({
                    'title': title,
                    'before': main_sections[title],
                    'after': content
                })

        return {
            'has_changes': True,
            'added_sections': added_sections,
            'modified_sections': modified_sections
        }

    def _parse_markdown_sections(self, content: str) -> Dict[str, str]:
        """解析 Markdown 为 section 字典"""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            if line.startswith('## '):
                # 保存前一个 section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)

                # 开始新 section
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个 section
        if current_section:
            sections[current_section] = '\n'.join(current_content)

        return sections

    def _display_constitution_diff(self, diff: Dict):
        """显示 constitution diff"""

        if diff['added_sections']:
            print()
            print("   📝 Added Sections:")
            for section in diff['added_sections']:
                print(f"      • {section['title']}")

        if diff['modified_sections']:
            print()
            print("   📝 Modified Sections:")
            for section in diff['modified_sections']:
                print(f"      • {section['title']}")

    def _prepare_constitution_merge(self, diff: Dict, branch_name: str):
        """准备 constitution 合并（生成 PR body）"""
        print(f"   ✅ Constitution changes will be included in PR")

    def _create_feature_pr(self, branch_name: str, feature_name: str, constitution_diff: Dict):
        """创建 feature PR"""

        pr_body = f"""## Feature: {feature_name}

### Summary
[Describe what this feature does]

### Constitution Updates
"""

        if constitution_diff.get('has_changes'):
            pr_body += "\nThis feature includes constitution updates:\n\n"

            for section in constitution_diff.get('added_sections', []):
                pr_body += f"- **Added**: {section['title']}\n"

            for section in constitution_diff.get('modified_sections', []):
                pr_body += f"- **Modified**: {section['title']}\n"

        else:
            pr_body += "\nNo constitution changes.\n"

        pr_body += "\n### Checklist\n- [ ] Tests passing\n- [ ] Documentation updated\n"

        # 创建 PR（使用 gh CLI）
        try:
            subprocess.run(
                [
                    "gh", "pr", "create",
                    "--title", f"feat: {feature_name}",
                    "--body", pr_body,
                    "--head", branch_name,
                    "--base", "main"
                ],
                cwd=self.project_root,
                check=True
            )
            print(f"   ✅ PR created")

        except subprocess.CalledProcessError:
            print(f"   ⚠️  Failed to create PR automatically")
            print(f"      Please create manually for branch: {branch_name}")

    def cleanup_feature(self, feature_name: str):
        """清理 feature worktree"""

        features = self.list_features()
        target_feature = None

        for feature in features:
            if feature.get('feature_name') == feature_name:
                target_feature = feature
                break

        if not target_feature:
            print(f"❌ Feature '{feature_name}' not found")
            return

        worktree_path = target_feature['path']

        # 移除 worktree
        try:
            subprocess.run(
                ["git", "worktree", "remove", worktree_path],
                cwd=self.project_root,
                check=True
            )
            print(f"✅ Worktree removed: {worktree_path}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to remove worktree: {e}")


# ========================================
# CLI Commands (Click)
# ========================================

@click.group()
def feature():
    """Feature management using Git Worktrees"""
    pass


@feature.command()
@click.argument('name')
@click.option('--description', '-d', default='', help='Feature description')
def create(name, description):
    """Create a new feature worktree"""
    manager = FeatureWorktreeManager()
    manager.create_feature(name, description)


@feature.command()
@click.argument('name')
def switch(name):
    """Switch to a feature worktree"""
    manager = FeatureWorktreeManager()
    manager.switch_feature(name)


@feature.command()
def list():
    """List all feature worktrees"""
    manager = FeatureWorktreeManager()
    features = manager.list_features()

    if not features:
        print("No active features")
        return

    print()
    print("📋 Active Features:")
    print()

    for feature in features:
        print(f"┌─ {feature.get('feature_name', 'Unknown')}")
        print(f"│  Branch: {feature.get('branch', 'N/A')}")
        print(f"│  Path: {feature.get('path', 'N/A')}")
        print(f"│  Created: {feature.get('created_at', 'N/A')[:10]}")
        print(f"└─ Status: {feature.get('status', 'active')}")
        print()


@feature.command()
@click.argument('name')
@click.option('--auto-pr/--no-auto-pr', default=True, help='Automatically create PR')
def complete(name, auto_pr):
    """Complete a feature and merge constitution changes"""
    manager = FeatureWorktreeManager()
    manager.complete_feature(name, auto_pr=auto_pr)


@feature.command()
@click.argument('name')
def cleanup(name):
    """Remove a feature worktree"""
    manager = FeatureWorktreeManager()
    manager.cleanup_feature(name)


if __name__ == '__main__':
    feature()
