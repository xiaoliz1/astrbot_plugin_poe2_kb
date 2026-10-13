# AstrBot 流放之路2知识库路由插件

抓取 Poe2DB 的简体与繁体页面，清洗后写入 AstrBot 原生知识库；当对话涉及流放之路2时，插件按提问语言检索对应知识库，并把少量相关资料临时提供给模型。

插件参考了 [YunMo-yanyu/astrbot-](https://github.com/YunMo-yanyu/astrbot-) 的知识库抓取、导入和话题路由思路，针对 Poe2DB 的页面结构与简繁双语入口独立实现。

## 数据来源

- 简体中文：https://poe2db.tw/cn/
- 繁體中文：https://poe2db.tw/tw/

两个语言库分开保存，页面 slug 用作稳定文档标识。插件安装后不附带数据库内容，需要执行同步命令。

## 安装前提

1. AstrBot 4.24 或更新的 4.x 版本。
2. AstrBot 已配置可用的 Embedding Provider。
3. AstrBot 运行环境可以访问 poe2db.tw；网络受限时可在插件设置里填写 HTTP 代理。
4. AstrBot 已启用原生知识库功能。

Rerank Provider 可选。插件不会在初始化时自动抓取大量页面；默认限速为每页间隔 500 毫秒。

## 快速开始

1. 将本目录安装为 AstrBot 插件并启用。
2. 执行：

   /流放之路2知识库初始化

3. 按需分别同步简体与繁体内容，例如每种语言先抓取 200 页：

   /流放之路2知识库同步 cn / 200

   /流放之路2知识库同步 tw / 200

   也可以从指定分类开始，例如：

   /流放之路2知识库同步 cn Skill_Gems 300

4. 查看导入进度：

   /流放之路2知识库状态

同步会沿 Poe2DB 页面链接进行广度优先抓取。首页链接覆盖面很广，建议先用较小页数试运行，再按类别补充。同步中可用 /流放之路2知识库停止同步 cn 停止单一语言任务。

## 命令

| 命令 | 用途 |
| --- | --- |
| /流放之路2知识库初始化 [Embedding Provider ID] | 创建或复用简体与繁体知识库 |
| /流放之路2知识库同步 <cn/tw> [入口 slug 或 URL] [页数] | 从入口页开始后台同步 |
| /流放之路2知识库单页导入 <cn/tw> <slug 或 URL> | 导入或更新单个页面 |
| /流放之路2知识库状态 [cn/tw/all] | 查看文档数与同步任务状态 |
| /流放之路2知识库搜索 <cn/tw/auto> <检索词> | 手动检索知识库 |
| /流放之路2知识库停止同步 [cn/tw/all] | 请求停止同步任务 |

例：

- /流放之路2知识库单页导入 cn Boneshatter
- /流放之路2知识库搜索 tw 碎骨

## 路由行为

- 默认仅在当前对话或近期用户消息命中 PoE2 关键词时触发检索。
- preferred_language=auto 时按繁简字形选择语言；不明显时使用简体库。也可固定为 cn 或 tw。
- 查询结果作为当前请求的临时内容段注入，不写回聊天历史；旧版字段不可用时才回退到系统提示词。
- 知识库里没有相关内容时插件不拦截模型请求。
- 检索片段包含 Poe2DB 页面来源。版本、赛季和数值信息应以最近一次同步的数据为准。

## 配置要点

- embedding_provider_id：多个向量模型时可指定 ID；留空自动选择首个可用模型。
- preferred_language：自动、简体或繁体。
- route_keywords：额外路由词，一行一个。
- crawl_delay_ms：抓取间隔，建议至少 400 毫秒。
- max_page_chars：单页正文截断上限。
- auto_sync_after_init：默认关闭，避免初始化时意外启动大规模抓取。

## 参考资料

- AstrBot 插件参考仓库：https://github.com/YunMo-yanyu/astrbot-
- AstrBot 插件事件与 LLM 请求钩子：https://github.com/AstrBotDevs/AstrBot/blob/master/docs/en/dev/star/guides/listen-message-event.md

## 许可证与归属

本插件参考并改编了 `YunMo-yanyu/astrbot-` 的知识库抓取、导入和路由实现。上游项目采用 MIT License，其版权声明及许可文本见本仓库的 `LICENSE`。本插件针对 Poe2DB 页面结构、简繁双库和语言路由所作的适配由本项目维护。
