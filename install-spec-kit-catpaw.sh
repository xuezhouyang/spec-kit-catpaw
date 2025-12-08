#!/usr/bin/env bash
#
# Spec Kit CatPaw 方言版安装脚本
# 
# ⚠️  重要说明：
#   这是安装支持 CatPaw IDE 的 Spec Kit 方言版本（不是安装 CatPaw IDE 本身）。
#   本脚本安装的是基于 GitHub Spec Kit (https://github.com/github/spec-kit) 的 CatPaw 定制版本。
#   本版本专门为 CatPaw IDE 优化，包含针对内部使用的定制配置。
#   
#   📌 临时方案说明：
#   CatPaw 的支持已经向官方 spec-kit 项目提交了 PR:
#   https://github.com/github/spec-kit/pull/1305
#   
#   本脚本只是一个权衡之计（临时方案），用于在 PR 合并前提供 CatPaw 支持。
#   一旦 PR 正式合并到官方项目后，请直接使用官方版本，本脚本的使命也就结束了。
#   
#   ⚠️  免责声明：
#   本脚本和 CatPaw 官方无关，这只是为了方便大家使用 CatPaw 去用 SpecKit 指令
#   而自发添加的拓展和对应给 SpecKit 官方的 PR。如有问题，与 CatPaw 官方无关。
#   
#   如果您需要官方版本，请访问: https://github.com/github/spec-kit
# 
# 使用方法:
#   sh -c "$(curl -fsSL https://db0supabase-272.database.sankuai.com/storage/v1/object/public/turing-aicoding/install-spec-kit-catpaw.sh)"
#
# 或者直接下载后执行:
#   curl -fsSL https://db0supabase-272.database.sankuai.com/storage/v1/object/public/turing-aicoding/install-spec-kit-catpaw.sh -o install-spec-kit-catpaw.sh
#   bash install-spec-kit-catpaw.sh

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    printf "${BLUE}ℹ${NC} %s\n" "$1"
}

print_success() {
    printf "${GREEN}✓${NC} %s\n" "$1"
}

print_warning() {
    printf "${YELLOW}⚠${NC} %s\n" "$1"
}

print_error() {
    printf "${RED}✗${NC} %s\n" "$1"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查 uv 是否安装
check_uv() {
    echo ""
    print_info "步骤 1/3: 检查依赖工具..."
    
    if ! command_exists uv; then
        print_error "✗ 未找到 uv 工具"
        echo ""
        echo "请先安装 uv:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo ""
        echo "或者访问: https://docs.astral.sh/uv/"
        exit 1
    fi
    print_success "✓ 已检测到 uv 工具"
}

# 检查 specify-cli 是否已安装
check_specify_cli() {
    if command_exists specify; then
        return 0
    fi
    return 1
}

# 检测 specify-cli 的安装来源
detect_specify_cli_source() {
    local tool_list_output
    local receipt_file="$HOME/.local/share/uv/tools/specify-cli/uv-receipt.toml"
    
    # 方式 1: 通过 uv tool list 检查 (最安全，无权限问题)
    print_info "   正在通过 uv 命令检查安装信息..."
    tool_list_output=$(uv tool list 2>/dev/null | grep -i "specify-cli" || true)
    
    if [ -z "$tool_list_output" ]; then
        print_info "   未通过 uv 检测到 specify-cli"
        return 2  # 无法确定
    fi
    
    # 检查输出中是否包含仓库信息
    if echo "$tool_list_output" | grep -q "xuezhouyang/spec-kit-catpaw"; then
        print_info "   通过 uv tool list 确认: 来自 CatPaw 定制仓库"
        return 0
    elif echo "$tool_list_output" | grep -q "github.com/github/spec-kit"; then
        print_info "   通过 uv tool list 确认: 来自官方仓库"
        return 1
    fi
    
    # 方式 2: 如果 uv tool list 没显示来源 (例如 PyPI 安装或输出格式差异)
    # 尝试读取安装凭据文件作为兜底，但必须先检查权限
    print_info "   uv tool list 未显示详细来源，尝试检查安装凭据..."
    
    local uv_tools_dir=$(dirname "$receipt_file")
    
    # 分层权限检测：
    # 1. 检查目录是否存在且当前用户有执行(进入)权限
    if [ ! -d "$uv_tools_dir" ] || [ ! -x "$uv_tools_dir" ]; then
        print_info "   uv 工具目录不存在或无访问权限，跳过文件检查"
    # 2. 检查文件是否存在且当前用户有读取权限
    elif [ ! -r "$receipt_file" ]; then
        print_info "   安装凭据文件不可读(可能是权限限制)，跳过文件检查"
    else
        # 3. 权限检查通过，安全读取
        if grep -q "xuezhouyang/spec-kit-catpaw" "$receipt_file" 2>/dev/null; then
            print_info "   通过凭据文件确认: 来自 CatPaw 定制仓库"
            return 0
        elif grep -q "github.com/github/spec-kit" "$receipt_file" 2>/dev/null; then
            print_info "   通过凭据文件确认: 来自官方仓库"
            return 1
        fi
    fi
    
    # 两种方式都无法确认，通常意味着是从 PyPI 安装的官方版 (因为 CatPaw 版目前只在 Git 上)
    print_info "   无法确定具体安装来源 (可能是 PyPI 版本)"
    return 2  # 未知来源
}

# 安装 specify-cli
install_specify_cli() {
    local need_reinstall=false
    local source_status
    
    echo ""
    print_info "步骤 2/3: 检查 specify-cli 安装状态..."
    
    # 检查是否已安装
    if check_specify_cli; then
        print_info "检测到 specify-cli 已安装，正在检查安装来源..."
        
        # 检测安装来源
        # 临时禁用 set -e，因为函数返回非零值是正常的（用于表示不同的状态）
        set +e
        detect_specify_cli_source
        source_status=$?
        set -e
        
        # 显示检测结果
        echo ""
        case $source_status in
            0)
                print_info "✓ 检测结果: 来自 CatPaw 定制仓库"
                ;;
            1)
                print_info "✓ 检测结果: 来自官方仓库"
                ;;
            2)
                print_warning "⚠️  检测结果: 无法确定安装来源"
                print_info "   可能原因: 安装信息文件不存在或格式异常"
                ;;
        esac
        echo ""
        
        if [ $source_status -eq 1 ]; then
            # 来自官方仓库，需要重新安装
            echo ""
            print_warning "⚠️  检测到已安装的 specify-cli 来自官方仓库"
            print_warning "   仓库地址: github.com/github/spec-kit"
            print_info "需要重新安装 CatPaw 定制版本"
            
            if is_interactive; then
                read -p "是否卸载官方版本并安装 CatPaw 定制版? (Y/n): " -n 1 -r
                echo ""
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    need_reinstall=true
                else
                    print_warning "跳过安装，继续使用官方版本"
                    return 0
                fi
            else
                # 非交互模式，自动重新安装
                print_info "非交互模式，自动重新安装 CatPaw 定制版"
                need_reinstall=true
            fi
            
            if [ "$need_reinstall" = true ]; then
                print_info "正在卸载官方版本..."
                if uv tool uninstall specify-cli 2>/dev/null; then
                    print_success "官方版本卸载完成"
                else
                    print_warning "卸载过程中出现警告，继续安装..."
                fi
            fi
        elif [ $source_status -eq 0 ]; then
            # 已经是 CatPaw 定制版
            echo ""
            print_success "✓ 检测到已安装 CatPaw 定制版，版本正确"
            print_success "✓ 无需重新安装，跳过此步骤"
            return 0
        else
            # 无法检测来源，建议重新安装以确保版本正确
            echo ""
            print_warning "⚠️  无法确定 specify-cli 的安装来源"
            print_info "为了确保使用正确的 CatPaw 定制版本，建议重新安装"
            echo ""
            
            if is_interactive; then
                read -p "是否重新安装 CatPaw 定制版? (Y/n): " -n 1 -r
                echo ""
                echo ""
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    need_reinstall=true
                    print_info "正在卸载现有版本..."
                    if uv tool uninstall specify-cli 2>/dev/null; then
                        print_success "现有版本卸载完成"
                    else
                        print_warning "卸载过程中出现警告，将使用 --force 强制安装..."
                    fi
                else
                    print_warning "跳过安装，继续使用现有版本"
                    print_info "如果遇到问题，请手动运行: uv tool install specify-cli --force --from git+https://github.com/xuezhouyang/spec-kit-catpaw.git"
                    return 0
                fi
            else
                print_info "非交互模式，将使用 --force 强制安装以确保版本正确"
                need_reinstall=true
            fi
        fi
    else
        print_info "未检测到 specify-cli，将进行全新安装"
    fi
    
    # 如果需要安装或重新安装
    if [ "$need_reinstall" = true ] || ! check_specify_cli; then
        echo ""
        echo ""
        print_info "正在安装 specify-cli (CatPaw 定制版)..."
        print_info "   仓库地址: github.com/xuezhouyang/spec-kit-catpaw"
        print_info "   这可能需要几分钟时间，请耐心等待..."
        
        # 使用 --force 强制安装（覆盖现有版本）
        if uv tool install specify-cli --force --from git+https://github.com/xuezhouyang/spec-kit-catpaw.git 2>&1; then
            echo ""
            print_success "✓ specify-cli (CatPaw 定制版) 安装成功"
        else
            echo ""
            print_error "✗ specify-cli 安装失败"
            print_error "请检查网络连接或稍后重试"
            exit 1
        fi
    fi
}

# 检测用户的默认 shell 并返回所有可能的配置文件
detect_shell_configs() {
    local configs=()
    local default_shell=$(basename "$SHELL" 2>/dev/null || echo "bash")
    
    # 根据用户的默认 shell 确定主配置文件
    case "$default_shell" in
        zsh)
            configs+=("$HOME/.zshrc")
            ;;
        bash)
            # bash 优先使用 .bash_profile，如果不存在则使用 .bashrc
            if [ -f "$HOME/.bash_profile" ]; then
                configs+=("$HOME/.bash_profile")
            else
                configs+=("$HOME/.bashrc")
            fi
            ;;
        *)
            # 未知 shell，尝试通用配置文件
            configs+=("$HOME/.profile")
            ;;
    esac
    
    # 为了兼容性，也检查其他常见配置文件
    # 如果用户在不同 shell 之间切换，这样可以确保环境变量在所有 shell 中都可用
    if [ "$default_shell" = "zsh" ] && [ -f "$HOME/.bashrc" ]; then
        configs+=("$HOME/.bashrc")
    elif [ "$default_shell" = "bash" ] && [ -f "$HOME/.zshrc" ]; then
        configs+=("$HOME/.zshrc")
    fi
    
    # 返回配置文件列表（用空格分隔）
    echo "${configs[@]}"
}

# 获取主配置文件（第一个）
get_primary_config() {
    local configs=($(detect_shell_configs))
    echo "${configs[0]}"
}

# 设置环境变量
setup_environment() {
    local configs=($(detect_shell_configs))
    local primary_config="${configs[0]}"
    local env_vars="
# Spec Kit CatPaw 定制版环境变量
# 这是基于 GitHub Spec Kit (https://github.com/github/spec-kit) 的 CatPaw 定制版本
export SPEC_KIT_REPO_OWNER=xuezhouyang
export SPEC_KIT_REPO_NAME=spec-kit-catpaw
"
    local default_shell=$(basename "$SHELL" 2>/dev/null || echo "bash")
    local updated_files=()
    local skipped_files=()
    
    echo ""
    print_info "步骤 3/3: 配置环境变量..."
    print_info "检测到默认 shell: $default_shell"
    echo ""
    
    # 遍历所有配置文件并添加环境变量
    for config_file in "${configs[@]}"; do
        # 确保配置文件存在
        if [ ! -f "$config_file" ]; then
            touch "$config_file"
            print_info "创建配置文件: $config_file"
        fi
        
        # 增强的重复检测：使用更宽容的正则，忽略行首空格
        # 检查是否已经存在 SPEC_KIT_REPO_OWNER (忽略注释行)
        local has_owner=$(grep -c "^[[:space:]]*export[[:space:]]\+SPEC_KIT_REPO_OWNER=" "$config_file" 2>/dev/null || echo "0")
        local has_name=$(grep -c "^[[:space:]]*export[[:space:]]\+SPEC_KIT_REPO_NAME=" "$config_file" 2>/dev/null || echo "0")
        
        if [ "$has_owner" -gt 0 ] && [ "$has_name" -gt 0 ]; then
            print_info "环境变量已存在于 '$config_file'，跳过配置"
            skipped_files+=("$config_file")
        elif [ "$has_owner" -gt 0 ] || [ "$has_name" -gt 0 ]; then
            # 部分存在，可能是不完整的配置，给出警告
            print_warning "⚠️  '$config_file' 中存在部分环境变量配置"
            print_info "   将跳过以避免重复，请手动检查配置文件"
            skipped_files+=("$config_file")
        else
            # 准备修改文件
            
            # 1. 创建备份
            local backup_file="${config_file}.bak.$(date +%Y%m%d%H%M%S)"
            cp "$config_file" "$backup_file"
            print_info "   已创建备份: '$backup_file'"
            
            # 2. 智能追加：检查文件末尾是否有换行符
            # 如果文件不为空且最后一行没有换行符，先追加一个换行符
            if [ -s "$config_file" ] && [ "$(tail -c 1 "$config_file" | wc -l)" -eq 0 ]; then
                echo "" >> "$config_file"
                # print_info "   补充文件末尾换行符"
            fi
            
            # 3. 追加环境变量
            echo "$env_vars" >> "$config_file"
            print_success "✓ 环境变量已添加到 '$config_file'"
            updated_files+=("$config_file")
        fi
    done
    
    echo ""
    
    # 显示总结信息
    if [ ${#updated_files[@]} -gt 0 ]; then
        print_success "环境变量配置完成！已更新 ${#updated_files[@]} 个配置文件"
        echo ""
        print_info "请运行以下命令使环境变量生效（根据您使用的 shell）:"
        for config_file in "${updated_files[@]}"; do
            echo "  source $config_file"
        done
        echo ""
        print_warning "或者重新打开终端窗口"
    elif [ ${#skipped_files[@]} -gt 0 ]; then
        print_info "所有配置文件中已存在环境变量，无需更新"
    fi
    
    # 为当前会话设置环境变量
    export SPEC_KIT_REPO_OWNER=xuezhouyang
    export SPEC_KIT_REPO_NAME=spec-kit-catpaw
    echo ""
    print_success "✓ 当前会话环境变量已设置"
}

# 检查是否为交互式终端
is_interactive() {
    [ -t 0 ] && [ -t 1 ]
}

# 初始化项目
init_project() {
    local init_in_current_dir=false
    
    # 检查当前目录是否为空
    if [ -z "$(ls -A . 2>/dev/null)" ]; then
        print_info "当前目录为空，将在此目录初始化项目"
        init_in_current_dir=true
    else
        if is_interactive; then
            echo ""
            print_warning "当前目录不为空"
            read -p "是否在当前目录初始化项目? (y/N): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                init_in_current_dir=true
            fi
        else
            print_warning "当前目录不为空，跳过自动初始化"
            print_info "请手动运行以下命令初始化项目:"
            echo "  specify init <项目名称> --ai catpaw"
            echo "  或者"
            echo "  specify init . --ai catpaw"
            return 0
        fi
    fi
    
    if [ "$init_in_current_dir" = true ]; then
        print_info "正在初始化 Spec Kit CatPaw 项目..."
        if specify init . --ai catpaw; then
            print_success "项目初始化成功！"
        else
            print_error "项目初始化失败"
            exit 1
        fi
    else
        print_info "请手动运行以下命令初始化项目:"
        echo "  specify init <项目名称> --ai catpaw"
        echo ""
        echo "或者在当前目录初始化:"
        echo "  specify init . --ai catpaw"
    fi
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "  Spec Kit CatPaw 方言版安装脚本"
    echo "=========================================="
    echo ""
    echo "📝 说明: 这是安装支持 CatPaw IDE 的 Spec Kit 方言版本"
    echo "   （不是安装 CatPaw IDE 本身）"
    echo ""
    echo "📌 版本说明:"
    echo "   • 这是基于 GitHub Spec Kit 的 CatPaw 定制版本"
    echo "   • 官方开源项目: https://github.com/github/spec-kit"
    echo "   • 本版本专门为 CatPaw IDE 优化"
    echo "   • 包含针对内部使用的定制配置"
    echo ""
    echo "⚠️  临时方案说明:"
    echo "   CatPaw 支持已提交 PR 到官方项目:"
    echo "   https://github.com/github/spec-kit/pull/1305"
    echo ""
    echo "   本脚本仅为临时方案，等 PR 合并后请使用官方版本"
    echo ""
    echo "⚠️  免责声明:"
    echo "   本脚本和 CatPaw 官方无关，这只是为了方便大家使用 CatPaw"
    echo "   去用 SpecKit 指令而自发添加的拓展。如有问题，与 CatPaw 官方无关。"
    echo ""
    
    # 检查依赖
    check_uv
    
    # 安装 specify-cli
    install_specify_cli
    
    # 设置环境变量
    setup_environment
    
    echo ""
    echo "=========================================="
    print_success "✓ 所有步骤完成！安装成功！"
    echo "=========================================="
    echo ""
    
    # 询问是否立即初始化（仅在交互式终端中）
    if is_interactive; then
        read -p "是否立即初始化项目? (Y/n): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            init_project
        else
            echo ""
            print_info "您可以稍后运行以下命令初始化项目:"
            echo "  specify init <项目名称> --ai catpaw"
            echo "  或者"
            echo "  specify init . --ai catpaw"
        fi
    else
        print_info "非交互式模式，跳过项目初始化"
        echo ""
        print_info "您可以稍后运行以下命令初始化项目:"
        echo "  specify init <项目名称> --ai catpaw"
        echo "  或者"
        echo "  specify init . --ai catpaw"
    fi
    
    echo ""
    print_success "安装脚本执行完成！"
    echo ""
}

# 执行主函数
main "$@"
