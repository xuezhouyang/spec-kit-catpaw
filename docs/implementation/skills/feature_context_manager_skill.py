"""
Feature Context Manager Skill
分支上下文管理 Skill - 与 Claude Code SessionStart Hook 集成

功能:
1. 检测当前工作环境（Worktree vs 普通分支）
2. 加载分支特定的 constitution 和 AI memory
3. 显示上下文摘要
4. Feature 完成时分析 constitution 变更
5. 自动生成 constitution 更新 PR
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import difflib


class FeatureContextManagerSkill:
    """
    Feature Context Manager Skill

    与 Claude Code SessionStart Hook 集成，自动管理分支上下文
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.git_dir = self.project_root / ".git"

    # ========================================
    # SessionStart Hook Methods
    # ========================================

    def on_session_start(self):
        """
        当 Claude Code session 启动时调用

        这是主入口点，由 .claude/hooks/session_start.py 调用
        """
        print("\n" + "=" * 60)
        print("🚀 Feature Context Manager - Session Start")
        print("=" * 60 + "\n")

        # 1. 检测环境
        env_info = self.detect_environment()

        # 2. 加载上下文
        context = self.load_context(env_info)

        # 3. 显示摘要
        self.display_context_summary(context, env_info)

        # 4. 更新 AI Agent memory（如果需要）
        self.update_agent_memory(context)

        print("\n" + "=" * 60)
        print("✅ Context loaded - Ready for development!")
        print("=" * 60 + "\n")

    def detect_environment(self) -> Dict:
        """
        检测当前工作环境

        返回: {
            'type': 'worktree' | 'branch' | 'main',
            'current_branch': '001-payment-gateway',
            'worktree_path': '/path/to/worktree' (if worktree),
            'is_feature_branch': True/False
        }
        """
        # 获取当前分支
        current_branch = self._get_current_branch()

        # 检查是否在 worktree 中
        is_worktree, worktree_info = self._check_if_worktree()

        # 判断是否是 feature 分支（001-*, 002-*, etc.）
        is_feature = current_branch and current_branch[0].isdigit()

        env_type = 'main'
        if is_worktree:
            env_type = 'worktree'
        elif is_feature:
            env_type = 'branch'

        return {
            'type': env_type,
            'current_branch': current_branch,
            'worktree_path': worktree_info.get('path') if is_worktree else None,
            'is_feature_branch': is_feature,
            'worktree_info': worktree_info if is_worktree else None
        }

    def load_context(self, env_info: Dict) -> Dict:
        """
        加载当前分支的上下文

        返回: {
            'constitution': {...},
            'ai_memory': {...},
            'feature_metadata': {...}
        }
        """
        context = {
            'branch': env_info['current_branch'],
            'env_type': env_info['type'],
            'constitution': None,
            'ai_memory': None,
            'feature_metadata': None
        }

        # 加载 constitution
        constitution_path = self.project_root / "memory" / "constitution.md"
        if constitution_path.exists():
            context['constitution'] = self._parse_constitution(constitution_path)

        # 加载 AI memory
        claude_md_path = self.project_root / "CLAUDE.md"
        if claude_md_path.exists():
            with open(claude_md_path, 'r') as f:
                context['ai_memory'] = {
                    'path': str(claude_md_path),
                    'content': f.read(),
                    'last_modified': datetime.fromtimestamp(
                        claude_md_path.stat().st_mtime
                    ).isoformat()
                }

        # 加载 feature metadata（如果是 worktree）
        if env_info['type'] == 'worktree':
            metadata_path = self.project_root / ".specify" / "feature-metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    context['feature_metadata'] = json.load(f)

        return context

    def display_context_summary(self, context: Dict, env_info: Dict):
        """显示上下文摘要"""

        print("📋 Current Environment:")
        print(f"   Type: {env_info['type'].upper()}")
        print(f"   Branch: {context['branch']}")

        if env_info['worktree_path']:
            print(f"   Worktree: {env_info['worktree_path']}")

        print()

        # Constitution 摘要
        if context['constitution']:
            print("📝 Constitution:")
            const = context['constitution']

            print(f"   Version: {const.get('version', 'N/A')}")
            print(f"   Sections: {len(const.get('sections', []))}")

            # 显示 feature-specific rules（如果有）
            if const.get('feature_specific_rules'):
                print(f"   Feature-Specific Rules: {len(const['feature_specific_rules'])}")
                print()
                print("   🎯 Feature-Specific Highlights:")
                for rule in const['feature_specific_rules'][:3]:  # 只显示前3条
                    print(f"      • {rule}")

            print()

        # AI Memory 摘要
        if context['ai_memory']:
            print("🤖 AI Context:")
            memory = context['ai_memory']

            print(f"   Last updated: {memory['last_modified'][:10]}")

            # 提取最近的变更（简化版）
            lines = memory['content'].split('\n')
            recent_section = False
            recent_items = []

            for line in lines:
                if 'Recent' in line or 'Development History' in line:
                    recent_section = True
                elif recent_section and line.strip().startswith('-'):
                    recent_items.append(line.strip())

            if recent_items:
                print(f"   Recent changes:")
                for item in recent_items[:3]:  # 只显示前3条
                    print(f"      {item}")

            print()

        # Feature Metadata
        if context.get('feature_metadata'):
            metadata = context['feature_metadata']
            print("🏷️  Feature Info:")
            print(f"   Name: {metadata.get('feature_name')}")
            print(f"   Number: {metadata.get('feature_number')}")
            print(f"   Created: {metadata.get('created_at', '')[:10]}")
            print(f"   Status: {metadata.get('status', 'active')}")
            print()

    def update_agent_memory(self, context: Dict):
        """
        更新 AI Agent memory（如果需要）

        在 session 开始时，可以在 CLAUDE.md 中添加一条记录
        """
        claude_md_path = self.project_root / "CLAUDE.md"

        if not claude_md_path.exists():
            return

        # 简单追加一条 session start 记录
        # 实际实现可以更智能（避免重复记录）

        session_entry = f"\n### {datetime.now().strftime('%Y-%m-%d %H:%M')}\n- Session started\n"

        # 注意：这里简化处理，实际应该检查是否已有今天的记录
        # with open(claude_md_path, 'a') as f:
        #     f.write(session_entry)

    # ========================================
    # Feature Completion Methods
    # ========================================

    def on_feature_complete(self, feature_name: str):
        """
        Feature 完成时调用

        分析 constitution 变更并生成上报 PR
        """
        print("\n" + "=" * 60)
        print(f"🎉 Completing Feature: {feature_name}")
        print("=" * 60 + "\n")

        # 1. 比较 constitution
        diff = self.compare_constitution_with_main()

        if not diff['has_changes']:
            print("✅ No constitution changes detected")
            print("   Feature-specific rules will not be merged to main")
            return

        # 2. 显示 diff
        print("📊 Constitution Changes Detected:\n")
        self.display_constitution_diff(diff)

        # 3. 询问用户
        print("\nOptions:")
        print("  a) Merge all changes to main constitution")
        print("  b) Merge selected sections")
        print("  c) Review and edit before merging")
        print("  d) Keep feature-specific (don't merge)")
        print()

        choice = input("Choose (a/b/c/d): ").strip().lower()

        if choice == 'a':
            self.merge_constitution_changes(diff, mode='all')

        elif choice == 'b':
            self.merge_constitution_changes(diff, mode='selective')

        elif choice == 'c':
            self.open_interactive_merge_editor(diff)

        elif choice == 'd':
            print("\n✅ Constitution changes will remain feature-specific")

    def compare_constitution_with_main(self) -> Dict:
        """
        比较当前分支的 constitution 和 main 分支

        返回: {
            'has_changes': True/False,
            'added_sections': [...],
            'modified_sections': [...],
            'removed_sections': [...]
        }
        """
        current_const_path = self.project_root / "memory" / "constitution.md"

        # 获取 main 分支的 constitution
        try:
            main_const_content = subprocess.run(
                ["git", "show", "main:memory/constitution.md"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            ).stdout

        except subprocess.CalledProcessError:
            print("⚠️  Could not read main branch constitution")
            return {'has_changes': False}

        # 读取当前 constitution
        if not current_const_path.exists():
            return {'has_changes': False}

        with open(current_const_path, 'r') as f:
            current_const_content = f.read()

        # 比较
        if current_const_content == main_const_content:
            return {'has_changes': False}

        # 解析 sections
        main_sections = self._parse_markdown_sections(main_const_content)
        current_sections = self._parse_markdown_sections(current_const_content)

        added_sections = []
        modified_sections = []
        removed_sections = []

        # 查找新增和修改的 sections
        for title, content in current_sections.items():
            if title not in main_sections:
                added_sections.append({'title': title, 'content': content})
            elif content != main_sections[title]:
                modified_sections.append({
                    'title': title,
                    'before': main_sections[title],
                    'after': content,
                    'diff': self._generate_diff(main_sections[title], content)
                })

        # 查找删除的 sections
        for title in main_sections:
            if title not in current_sections:
                removed_sections.append({'title': title, 'content': main_sections[title]})

        return {
            'has_changes': True,
            'added_sections': added_sections,
            'modified_sections': modified_sections,
            'removed_sections': removed_sections
        }

    def display_constitution_diff(self, diff: Dict):
        """显示 constitution diff（美化输出）"""

        if diff['added_sections']:
            print("━" * 60)
            print("📝 Added Sections:")
            print("━" * 60)

            for section in diff['added_sections']:
                print(f"\n## {section['title']}")
                print()
                # 只显示前几行
                lines = section['content'].strip().split('\n')
                for line in lines[:5]:
                    print(f"  {line}")

                if len(lines) > 5:
                    print(f"  ... ({len(lines) - 5} more lines)")

                print()

        if diff['modified_sections']:
            print("━" * 60)
            print("📝 Modified Sections:")
            print("━" * 60)

            for section in diff['modified_sections']:
                print(f"\n## {section['title']}")
                print()
                print("Changes:")
                # 显示 unified diff
                for line in section['diff'].split('\n')[:10]:
                    if line.startswith('+'):
                        print(f"  \033[0;32m{line}\033[0m")  # Green
                    elif line.startswith('-'):
                        print(f"  \033[0;31m{line}\033[0m")  # Red
                    else:
                        print(f"  {line}")

                print()

        if diff['removed_sections']:
            print("━" * 60)
            print("📝 Removed Sections:")
            print("━" * 60)

            for section in diff['removed_sections']:
                print(f"\n## {section['title']}")
                print("  (This section was removed)")
                print()

    def merge_constitution_changes(self, diff: Dict, mode: str = 'all'):
        """
        合并 constitution 变更到 main

        mode: 'all' | 'selective'
        """
        if mode == 'selective':
            # 让用户选择要合并的 sections
            selected_sections = self._select_sections_to_merge(diff)
        else:
            # 合并所有变更
            selected_sections = {
                'added': diff['added_sections'],
                'modified': diff['modified_sections']
            }

        # 生成 PR body
        pr_body = self._generate_constitution_pr_body(selected_sections)

        print("\n" + "=" * 60)
        print("Creating PR for constitution update...")
        print("=" * 60 + "\n")

        print(pr_body)

        # 创建 PR（简化版，实际应该调用 gh CLI）
        print("\n💡 To create PR manually:")
        print(f"   1. Commit constitution changes")
        print(f"   2. Run: gh pr create --title 'docs: Update constitution' --body '<body>'")

    def _select_sections_to_merge(self, diff: Dict) -> Dict:
        """交互式选择要合并的 sections"""

        print("\n📋 Select sections to merge:\n")

        selected_added = []
        selected_modified = []

        # 选择新增的 sections
        if diff['added_sections']:
            print("Added Sections:")
            for i, section in enumerate(diff['added_sections'], 1):
                choice = input(f"  [{i}] {section['title']} - Merge? (y/n): ")
                if choice.lower() == 'y':
                    selected_added.append(section)

        # 选择修改的 sections
        if diff['modified_sections']:
            print("\nModified Sections:")
            for i, section in enumerate(diff['modified_sections'], 1):
                choice = input(f"  [{i}] {section['title']} - Merge? (y/n): ")
                if choice.lower() == 'y':
                    selected_modified.append(section)

        return {
            'added': selected_added,
            'modified': selected_modified
        }

    def _generate_constitution_pr_body(self, selected_sections: Dict) -> str:
        """生成 constitution 更新 PR 的 body"""

        current_branch = self._get_current_branch()

        body = f"""## Constitution Update from Feature: {current_branch}

### Summary
This PR updates the project constitution with rules developed during the feature implementation.

"""

        # 新增的 sections
        if selected_sections['added']:
            body += "### Sections Added\n\n"
            for section in selected_sections['added']:
                body += f"#### {section['title']}\n\n"
                body += "```\n"
                body += section['content'].strip()[:200]  # 限制长度
                body += "\n```\n\n"

        # 修改的 sections
        if selected_sections['modified']:
            body += "### Sections Modified\n\n"
            for section in selected_sections['modified']:
                body += f"#### {section['title']}\n\n"
                body += "Changes:\n```diff\n"
                body += section['diff'][:200]
                body += "\n```\n\n"

        body += """### Review Checklist
- [ ] Reviewed by Engineering Lead
- [ ] No conflicts with existing rules
- [ ] Rules are broadly applicable

---
*This PR was generated by Feature Context Manager Skill*
"""

        return body

    # ========================================
    # Utility Methods
    # ========================================

    def _get_current_branch(self) -> Optional[str]:
        """获取当前分支名"""
        try:
            result = subprocess.run(
                ["git", "symbolic-ref", "--short", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None

    def _check_if_worktree(self) -> tuple[bool, Dict]:
        """检查是否在 worktree 中"""

        # 检查 .git 是否是文件（worktree 中 .git 是指向主仓库的文件）
        git_path = self.project_root / ".git"

        if git_path.is_file():
            # 读取 .git 文件内容
            with open(git_path, 'r') as f:
                content = f.read().strip()

            # 内容格式: gitdir: /path/to/main/repo/.git/worktrees/name
            if content.startswith('gitdir:'):
                worktree_git_dir = content.split(':', 1)[1].strip()

                return True, {
                    'path': str(self.project_root),
                    'git_dir': worktree_git_dir
                }

        return False, {}

    def _parse_constitution(self, path: Path) -> Dict:
        """解析 constitution.md"""

        with open(path, 'r') as f:
            content = f.read()

        sections = self._parse_markdown_sections(content)

        # 提取 feature-specific rules（如果有特殊标记的 section）
        feature_specific = []
        if 'Feature-Specific Rules' in sections:
            rules_text = sections['Feature-Specific Rules']
            # 简单解析（实际可以更智能）
            for line in rules_text.split('\n'):
                if line.strip().startswith('-'):
                    feature_specific.append(line.strip()[2:])

        return {
            'path': str(path),
            'version': 'unknown',  # 可以从文件头提取
            'sections': sections,
            'feature_specific_rules': feature_specific
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

    def _generate_diff(self, text1: str, text2: str) -> str:
        """生成 unified diff"""
        diff = difflib.unified_diff(
            text1.splitlines(keepends=True),
            text2.splitlines(keepends=True),
            lineterm=''
        )
        return ''.join(diff)


# ========================================
# SessionStart Hook 集成
# ========================================

def on_session_start():
    """
    Claude Code SessionStart Hook 入口

    在 .claude/hooks/session_start.py 中调用此函数
    """
    skill = FeatureContextManagerSkill()
    skill.on_session_start()


# ========================================
# CLI Interface (可选)
# ========================================

if __name__ == '__main__':
    import sys

    skill = FeatureContextManagerSkill()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'session-start':
            skill.on_session_start()

        elif command == 'feature-complete':
            feature_name = sys.argv[2] if len(sys.argv) > 2 else 'current'
            skill.on_feature_complete(feature_name)

        elif command == 'diff':
            diff = skill.compare_constitution_with_main()
            skill.display_constitution_diff(diff)

    else:
        print("Usage:")
        print("  python feature_context_manager_skill.py session-start")
        print("  python feature_context_manager_skill.py feature-complete <name>")
        print("  python feature_context_manager_skill.py diff")
