"""
企业级 Spec-Kit 核心功能实现示例
Enterprise-Level Spec-Kit Core Implementation Examples

这个文件展示关键组件的实现逻辑，作为开发参考。
实际实现时需要集成到 src/specify_cli/__init__.py
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import yaml
import hashlib
import json
from datetime import datetime
from pathlib import Path


# ============================================
# 1. 数据模型
# ============================================

class SourceType(Enum):
    """模板源类型"""
    GIT = "git"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class AuthType(Enum):
    """认证类型"""
    SSH = "ssh"
    TOKEN = "token"
    BASIC = "basic"


@dataclass
class TemplateSource:
    """模板源配置"""
    name: str                          # 源名称 (corporate, department, team)
    type: SourceType
    url: str
    branch: str = "main"
    priority: int = 10                 # 数字越小优先级越高
    enforce: bool = False              # 是否强制使用
    cache_ttl: int = 3600             # 缓存时间（秒）
    templates: List[Dict[str, Any]] = field(default_factory=list)
    auth: Optional[Dict[str, str]] = None


@dataclass
class Template:
    """模板对象"""
    name: str                          # 模板名称
    content: str                       # 模板内容
    source: str                        # 来源（corporate/department/team）
    version: Optional[str] = None      # 版本
    sha256: Optional[str] = None       # 内容哈希
    path: Optional[str] = None         # 文件路径
    enforce: bool = False              # 是否强制

    def __post_init__(self):
        if not self.sha256:
            self.sha256 = hashlib.sha256(self.content.encode()).hexdigest()


@dataclass
class Policy:
    """策略配置"""
    name: str
    description: str
    enabled: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: Dict[str, Any] = field(default_factory=dict)
    notifications: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """审计事件"""
    timestamp: datetime
    event_type: str                    # template_override, template_download, etc.
    user: str
    team: Optional[str] = None
    action: Dict[str, Any] = field(default_factory=dict)
    policy_check: Dict[str, Any] = field(default_factory=dict)
    approval: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        """转换为 JSON"""
        data = {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "user": self.user,
            "team": self.team,
            "action": self.action,
            "policy_check": self.policy_check,
            "approval": self.approval
        }
        return json.dumps(data, indent=2)


# ============================================
# 2. 配置管理器
# ============================================

class ConfigManager:
    """
    配置管理器
    负责读取和解析 .specify/config.yaml
    """

    def __init__(self, config_path: str = ".specify/config.yaml"):
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.sources: List[TemplateSource] = []
        self.policies: List[Policy] = []

        if self.config_path.exists():
            self.load()

    def load(self):
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 解析模板源
        if 'template_sources' in self.config:
            for name, source_config in self.config['template_sources'].items():
                source = TemplateSource(
                    name=name,
                    type=SourceType(source_config.get('type', 'git')),
                    url=source_config['url'],
                    branch=source_config.get('branch', 'main'),
                    priority=source_config.get('priority', 10),
                    enforce=source_config.get('enforce', False),
                    cache_ttl=source_config.get('cache_ttl', 3600),
                    templates=source_config.get('templates', []),
                    auth=source_config.get('auth')
                )
                self.sources.append(source)

        # 解析策略
        if 'policies' in self.config:
            for policy_config in self.config['policies']:
                policy = Policy(
                    name=policy_config['name'],
                    description=policy_config.get('description', ''),
                    enabled=policy_config.get('enabled', True),
                    conditions=policy_config.get('conditions', {}),
                    actions=policy_config.get('actions', {}),
                    notifications=policy_config.get('notifications', {})
                )
                self.policies.append(policy)

    def get_sources_for_template(self, template_name: str) -> List[TemplateSource]:
        """
        获取提供指定模板的所有源
        """
        matching_sources = []

        for source in self.sources:
            for template_def in source.templates:
                # 支持通配符
                if template_def.get('name') == '*' or template_def.get('name') == template_name:
                    matching_sources.append(source)
                    break

        # 按优先级排序（数字越小越优先）
        matching_sources.sort(key=lambda s: s.priority)
        return matching_sources


# ============================================
# 3. 模板解析器
# ============================================

class TemplateResolver:
    """
    模板解析器
    从多个源下载并合并模板
    """

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.cache: Dict[str, Template] = {}

    def resolve(self, template_name: str) -> Template:
        """
        解析模板
        1. 检查是否有强制模板
        2. 如果没有，按优先级合并多个源
        """
        sources = self.config.get_sources_for_template(template_name)

        if not sources:
            raise ValueError(f"No source found for template: {template_name}")

        # 1. 检查强制模板
        enforced_sources = [s for s in sources if s.enforce]
        if enforced_sources:
            # 只使用优先级最高的强制模板
            return self._download_template(enforced_sources[0], template_name)

        # 2. 合并多个源的模板
        templates = []
        for source in sources:
            try:
                template = self._download_template(source, template_name)
                templates.append(template)
            except Exception as e:
                print(f"Warning: Failed to download from {source.name}: {e}")

        if not templates:
            raise ValueError(f"Failed to download template {template_name} from any source")

        # 如果只有一个模板，直接返回
        if len(templates) == 1:
            return templates[0]

        # 合并多个模板
        return self._merge_templates(templates, template_name)

    def _download_template(self, source: TemplateSource, template_name: str) -> Template:
        """
        从指定源下载模板
        实际实现需要调用 Git 操作
        """
        # 这里简化实现，实际需要调用 Git clone/pull
        # 可以复用现有的 download_template_from_github() 函数并扩展

        # 查找模板定义
        template_def = None
        for t in source.templates:
            if t.get('name') == template_name or t.get('name') == '*':
                template_def = t
                break

        if not template_def:
            raise ValueError(f"Template {template_name} not found in source {source.name}")

        # 模拟下载（实际应该从 Git 仓库拉取）
        content = f"# Template: {template_name}\n# Source: {source.name}\n# Priority: {source.priority}\n\n[Template content from {source.name}]"

        template = Template(
            name=template_name,
            content=content,
            source=source.name,
            version=template_def.get('version'),
            path=template_def.get('path'),
            enforce=template_def.get('enforce', source.enforce)
        )

        return template

    def _merge_templates(self, templates: List[Template], template_name: str) -> Template:
        """
        合并多个模板
        策略：按优先级从高到低，后面的扩展前面的
        """
        if not templates:
            raise ValueError("No templates to merge")

        # 按来源优先级排序（假设 corporate < department < team）
        priority_map = {'corporate': 1, 'department': 2, 'team': 3, 'public': 10}
        templates.sort(key=lambda t: priority_map.get(t.source, 99))

        # 简单合并：连接内容（实际应该按文件类型智能合并）
        merged_content = []
        sources_used = []

        for template in templates:
            merged_content.append(f"\n# === From: {template.source} (Priority: {priority_map.get(template.source, 99)}) ===\n")
            merged_content.append(template.content)
            sources_used.append(template.source)

        merged_content.append(f"\n# === Template Sources ===")
        merged_content.append(f"# This template was merged from: {', '.join(sources_used)}")

        return Template(
            name=template_name,
            content='\n'.join(merged_content),
            source='merged',
            enforce=any(t.enforce for t in templates)
        )


# ============================================
# 4. 策略引擎
# ============================================

class PolicyEngine:
    """
    策略引擎
    根据项目上下文自动应用模板策略
    """

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager

    def apply_policies(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用策略到项目上下文
        返回: {
            'enforced_templates': [...],
            'recommended_templates': [...],
            'policies_applied': [...],
            'violations': [...]
        }
        """
        result = {
            'enforced_templates': [],
            'recommended_templates': [],
            'policies_applied': [],
            'violations': []
        }

        for policy in self.config.policies:
            if not policy.enabled:
                continue

            # 检查策略条件是否满足
            if self._check_conditions(policy.conditions, project_context):
                result['policies_applied'].append(policy.name)

                # 应用策略动作
                actions = policy.actions

                # 强制模板
                if 'enforce_templates' in actions:
                    result['enforced_templates'].extend(actions['enforce_templates'])

                # 推荐模板
                if 'recommend_templates' in actions:
                    result['recommended_templates'].extend(actions['recommend_templates'])

        return result

    def _check_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        检查策略条件是否满足
        支持 'any' 和 'all' 逻辑
        """
        if not conditions:
            return True

        # 处理 'any' 条件（满足任一即可）
        if 'any' in conditions:
            for condition in conditions['any']:
                if self._check_single_condition(condition, context):
                    return True
            return False

        # 处理 'all' 条件（必须全部满足）
        if 'all' in conditions:
            for condition in conditions['all']:
                if not self._check_single_condition(condition, context):
                    return False
            return True

        # 默认按 'all' 处理
        for key, value in conditions.items():
            if not self._check_single_condition({key: value}, context):
                return False

        return True

    def _check_single_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        检查单个条件
        """
        for key, expected in condition.items():
            actual = context.get(key)

            if isinstance(expected, dict):
                # 处理复杂条件，如 contains, equals, etc.
                if 'contains' in expected:
                    if not actual:
                        return False
                    # 检查是否包含任一项
                    return any(item in actual for item in expected['contains'])

            elif isinstance(expected, list):
                # 检查是否匹配列表中的任一项
                if actual not in expected:
                    return False

            else:
                # 简单相等比较
                if actual != expected:
                    return False

        return True

    def check_override_approval(self, template_name: str, from_source: str,
                                 to_source: str, project_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        检查覆盖模板是否需要审批
        返回: None (不需要审批) 或 审批要求字典
        """
        # 检查所有适用的策略
        for policy in self.config.policies:
            if not policy.enabled:
                continue

            if not self._check_conditions(policy.conditions, project_context):
                continue

            actions = policy.actions

            # 检查是否禁止覆盖
            if actions.get('block_override'):
                return {
                    'allowed': False,
                    'reason': f"Policy '{policy.name}' blocks override",
                    'policy': policy.name
                }

            # 检查是否需要审批
            if actions.get('require_approval'):
                return {
                    'allowed': True,
                    'requires_approval': True,
                    'approver_roles': actions.get('approver_roles', []),
                    'policy': policy.name
                }

        # 默认允许，无需审批
        return None


# ============================================
# 5. 审计引擎
# ============================================

class AuditEngine:
    """
    审计引擎
    记录所有模板操作
    """

    def __init__(self, log_file: str = ".specify/audit.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: AuditEvent):
        """
        记录审计事件
        """
        # 1. 写入日志文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(event.to_json() + '\n')

        # 2. 如果需要，发送到远程服务
        # self._send_to_remote(event)

        # 3. 如果是重要事件，发送通知
        # self._send_notification(event)

    def log_template_download(self, template_name: str, source: str, user: str):
        """记录模板下载"""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="template_download",
            user=user,
            action={
                "template": template_name,
                "source": source
            }
        )
        self.log_event(event)

    def log_template_override(self, template_name: str, from_source: str,
                              to_source: str, user: str, reason: str,
                              approval: Optional[Dict[str, Any]] = None):
        """记录模板覆盖"""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="template_override",
            user=user,
            action={
                "template": template_name,
                "from_source": from_source,
                "to_source": to_source,
                "reason": reason
            },
            approval=approval
        )
        self.log_event(event)

    def log_policy_violation(self, policy_name: str, user: str, details: Dict[str, Any]):
        """记录策略违规"""
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type="policy_violation",
            user=user,
            action=details,
            policy_check={
                "violated": True,
                "policy": policy_name
            }
        )
        self.log_event(event)

    def get_events(self, event_type: Optional[str] = None,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None) -> List[AuditEvent]:
        """
        查询审计事件
        """
        events = []

        if not self.log_file.exists():
            return events

        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)

                    # 过滤事件类型
                    if event_type and data.get('event_type') != event_type:
                        continue

                    # 过滤日期范围
                    event_time = datetime.fromisoformat(data['timestamp'])
                    if start_date and event_time < start_date:
                        continue
                    if end_date and event_time > end_date:
                        continue

                    # 重建事件对象
                    event = AuditEvent(
                        timestamp=event_time,
                        event_type=data['event_type'],
                        user=data['user'],
                        team=data.get('team'),
                        action=data.get('action', {}),
                        policy_check=data.get('policy_check', {}),
                        approval=data.get('approval')
                    )
                    events.append(event)

                except Exception as e:
                    print(f"Warning: Failed to parse audit log line: {e}")

        return events


# ============================================
# 6. 版本管理器
# ============================================

class VersionManager:
    """
    版本管理器
    处理模板版本锁定
    """

    def __init__(self, lock_file: str = ".specify/template-lock.yaml"):
        self.lock_file = Path(lock_file)
        self.locks: Dict[str, Dict[str, Any]] = {}

        if self.lock_file.exists():
            self.load()

    def load(self):
        """加载锁文件"""
        with open(self.lock_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            self.locks = data.get('locks', {})

    def save(self):
        """保存锁文件"""
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        data = {'locks': self.locks}
        with open(self.lock_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def lock_template(self, template_name: str, version: str,
                      sha256: str, locked_by: str, reason: str,
                      expires_at: Optional[str] = None):
        """锁定模板版本"""
        self.locks[template_name] = {
            'version': version,
            'sha256': sha256,
            'locked_at': datetime.now().isoformat(),
            'locked_by': locked_by,
            'reason': reason,
            'expires_at': expires_at
        }
        self.save()

    def unlock_template(self, template_name: str):
        """解锁模板"""
        if template_name in self.locks:
            del self.locks[template_name]
            self.save()

    def is_locked(self, template_name: str) -> bool:
        """检查模板是否被锁定"""
        if template_name not in self.locks:
            return False

        lock = self.locks[template_name]

        # 检查是否过期
        if 'expires_at' in lock and lock['expires_at']:
            expires = datetime.fromisoformat(lock['expires_at'])
            if datetime.now() > expires:
                # 自动解锁过期的锁
                self.unlock_template(template_name)
                return False

        return True

    def get_lock_info(self, template_name: str) -> Optional[Dict[str, Any]]:
        """获取锁定信息"""
        return self.locks.get(template_name)


# ============================================
# 7. 主控制器（集成所有组件）
# ============================================

class EnterpriseSpecKit:
    """
    企业级 Spec-Kit 主控制器
    集成所有功能模块
    """

    def __init__(self, config_path: str = ".specify/config.yaml"):
        self.config_manager = ConfigManager(config_path)
        self.template_resolver = TemplateResolver(self.config_manager)
        self.policy_engine = PolicyEngine(self.config_manager)
        self.audit_engine = AuditEngine()
        self.version_manager = VersionManager()

    def initialize_project(self, project_name: str,
                          project_tags: List[str] = None,
                          tech_stack: List[str] = None,
                          user: str = "unknown") -> Dict[str, Any]:
        """
        初始化项目
        自动应用策略并下载模板
        """
        # 1. 构建项目上下文
        context = {
            'project_name': project_name,
            'project_tags': project_tags or [],
            'tech_stack': tech_stack or []
        }

        # 2. 应用策略
        policy_result = self.policy_engine.apply_policies(context)

        # 3. 解析所需的模板
        all_templates = set(policy_result['enforced_templates'] +
                           policy_result['recommended_templates'])

        templates_downloaded = []
        for template_name in all_templates:
            try:
                # 检查版本锁定
                if self.version_manager.is_locked(template_name):
                    lock_info = self.version_manager.get_lock_info(template_name)
                    print(f"⚠️  Template '{template_name}' is locked: {lock_info['reason']}")

                # 解析并下载模板
                template = self.template_resolver.resolve(template_name)
                templates_downloaded.append(template)

                # 记录审计日志
                self.audit_engine.log_template_download(
                    template_name=template_name,
                    source=template.source,
                    user=user
                )

            except Exception as e:
                print(f"❌ Failed to download template '{template_name}': {e}")

        return {
            'project_context': context,
            'policy_result': policy_result,
            'templates_downloaded': templates_downloaded
        }

    def override_template(self, template_name: str, new_source: str,
                         reason: str, user: str,
                         project_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        覆盖模板
        检查是否需要审批
        """
        # 1. 获取当前模板信息
        current_template = self.template_resolver.resolve(template_name)

        # 2. 检查版本锁定
        if self.version_manager.is_locked(template_name):
            lock_info = self.version_manager.get_lock_info(template_name)
            return {
                'success': False,
                'reason': 'template_locked',
                'lock_info': lock_info
            }

        # 3. 检查策略是否允许覆盖
        approval_check = self.policy_engine.check_override_approval(
            template_name=template_name,
            from_source=current_template.source,
            to_source=new_source,
            project_context=project_context
        )

        if approval_check and not approval_check.get('allowed'):
            # 完全禁止覆盖
            self.audit_engine.log_policy_violation(
                policy_name=approval_check['policy'],
                user=user,
                details={
                    'action': 'template_override',
                    'template': template_name,
                    'blocked_reason': approval_check['reason']
                }
            )
            return {
                'success': False,
                'reason': 'policy_blocked',
                'policy': approval_check['policy'],
                'message': approval_check['reason']
            }

        if approval_check and approval_check.get('requires_approval'):
            # 需要审批
            return {
                'success': False,
                'reason': 'approval_required',
                'approver_roles': approval_check.get('approver_roles', []),
                'policy': approval_check['policy']
            }

        # 4. 允许覆盖，执行操作
        # 这里简化，实际应该更新模板源配置
        self.audit_engine.log_template_override(
            template_name=template_name,
            from_source=current_template.source,
            to_source=new_source,
            user=user,
            reason=reason
        )

        return {
            'success': True,
            'template': template_name,
            'from_source': current_template.source,
            'to_source': new_source
        }


# ============================================
# 8. 使用示例
# ============================================

def example_usage():
    """使用示例"""

    # 初始化企业级 Spec-Kit
    spec_kit = EnterpriseSpecKit(config_path=".specify/config.yaml")

    # 场景 1: 初始化金融支付项目
    print("=" * 60)
    print("场景 1: 初始化金融支付项目")
    print("=" * 60)

    result = spec_kit.initialize_project(
        project_name="payment-gateway",
        project_tags=["finance", "payment"],
        tech_stack=["python", "fastapi"],
        user="john.doe@company.com"
    )

    print(f"\n应用的策略: {result['policy_result']['policies_applied']}")
    print(f"强制模板: {result['policy_result']['enforced_templates']}")
    print(f"推荐模板: {result['policy_result']['recommended_templates']}")
    print(f"已下载模板数: {len(result['templates_downloaded'])}")

    # 场景 2: 尝试覆盖模板
    print("\n" + "=" * 60)
    print("场景 2: 尝试覆盖强制模板（应该被拒绝）")
    print("=" * 60)

    override_result = spec_kit.override_template(
        template_name="constitution",
        new_source="team",
        reason="团队需要定制",
        user="john.doe@company.com",
        project_context={
            'project_tags': ["finance", "payment"],
            'tech_stack': ["python"]
        }
    )

    if not override_result['success']:
        print(f"\n❌ 覆盖被拒绝: {override_result['reason']}")
        if 'lock_info' in override_result:
            print(f"   锁定原因: {override_result['lock_info']['reason']}")
            print(f"   锁定人: {override_result['lock_info']['locked_by']}")

    # 场景 3: 查询审计日志
    print("\n" + "=" * 60)
    print("场景 3: 查询审计日志")
    print("=" * 60)

    events = spec_kit.audit_engine.get_events(event_type="template_download")
    print(f"\n模板下载事件数: {len(events)}")
    for event in events:
        print(f"  - {event.timestamp}: {event.action.get('template')} from {event.action.get('source')}")


if __name__ == "__main__":
    example_usage()
