# Spec Kit CatPaw 方言版快速开始

> ⚠️ **重要说明**：
> 
> 这是安装支持 CatPaw IDE 的 **Spec Kit 方言版本**（不是安装 CatPaw IDE 本身）。
> 本版本基于 [GitHub Spec Kit](https://github.com/github/spec-kit)，专门为 CatPaw IDE 优化，包含针对内部使用的定制配置。
> 
> 📌 **临时方案说明**：
> 
> CatPaw 的支持已经向官方 spec-kit 项目提交了 PR: [github/spec-kit#1305](https://github.com/github/spec-kit/pull/1305)
> 
> **本脚本只是一个权衡之计（临时方案）**，用于在 PR 合并前提供 CatPaw 支持。
> 一旦 PR 正式合并到官方项目后，请直接使用官方版本，本脚本的使命也就结束了。
> 
> ⚠️ **免责声明**：
> 
> **本脚本和 CatPaw 官方无关**，这只是为了方便大家使用 CatPaw 去用 SpecKit 指令
> 而自发添加的拓展和对应给 SpecKit 官方的 PR。**如有问题，与 CatPaw 官方无关。**
> 
> 如果您需要官方开源版本，请访问: https://github.com/github/spec-kit

## 一键安装（推荐）

```bash
sh -c "$(curl -fsSL https://db0supabase-272.database.sankuai.com/storage/v1/object/public/turing-aicoding/install-spec-kit-catpaw.sh)"
```

> 📝 **注意**: 这是安装支持 CatPaw IDE 的 Spec Kit 方言版本，**不是安装 CatPaw IDE 本身**。

## 手动安装

如果您更喜欢手动安装，可以按照以下步骤操作：

```bash
# 1. 安装 specify-cli
uv tool install specify-cli --from git+https://github.com/xuezhouyang/spec-kit-catpaw.git

# 2. 设置环境变量（CatPaw 定制版需要）
export SPEC_KIT_REPO_OWNER=xuezhouyang
export SPEC_KIT_REPO_NAME=spec-kit-catpaw

# 3. 初始化项目
specify init . --ai catpaw
```

## 与官方版本的区别

- ✅ 专门为 CatPaw IDE 优化
- ✅ 包含内部定制配置
- ✅ 使用 CatPaw 专用的仓库地址
- ✅ 自动配置 CatPaw 相关的环境变量

## 关于临时方案

> ⚠️ **请注意**：这是一个临时方案。
> 
> CatPaw 支持已提交 PR 到官方项目: [github/spec-kit#1305](https://github.com/github/spec-kit/pull/1305)
> 
> 一旦 PR 合并后，请切换到官方版本：
> ```bash
> uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
> specify init . --ai catpaw
> ```

## 免责声明

> ⚠️ **重要**：
> 
> - **本脚本和 CatPaw 官方无关**
> - 这只是为了方便大家使用 CatPaw 去用 SpecKit 指令而**自发添加的拓展**
> - 以及对应给 SpecKit 官方的 PR
> - **如有问题，与 CatPaw 官方无关**

## 更多信息

- 官方 Spec Kit 项目: https://github.com/github/spec-kit
- CatPaw 支持 PR: https://github.com/github/spec-kit/pull/1305
- CatPaw IDE 文档: https://catpaw.meituan.com/
