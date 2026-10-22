# 文档索引

所有任务先读 [项目记忆](MEMORY.md) 和 [强制契约](UPDATE_RELEASE_CONTRACT.md)，再按任务选择下列文档。历史 PRD、归档及通用参考不覆盖现行契约；有冲突时先遵守跨项目规范及更高优先级指令。

## 更新、工具箱、安装与发布

所有 Agent 在修改安装、注册表、Manifest、Runner、更新、卸载或发布逻辑前，必须依次阅读 Toolbox 仓库的 `docs/HONSEN_WINDOWS_APPLICATION_STANDARD.md`、`docs/honsen-desktop-update-protocol.md`、`docs/toolbox-integration-contract.md`、`docs/schemas/honsen.app.schema.json`。跨项目规范为事实源；与本地文档冲突须报告并按跨项目流程统一修正，系统及用户指令仍具有更高优先级。

1. [强制契约](UPDATE_RELEASE_CONTRACT.md)：最高优先级，所有任务开始前必读。
2. [当前更新与工具箱接入](CURRENT_UPDATE_AND_TOOLBOX_INTEGRATION.md)：身份、注册表、Runner、安装与卸载的具体说明。
3. [发布与自动更新](RELEASE_AND_AUTO_UPDATE.md)：Windows 发布操作步骤。
4. [测试规则](TEST_RULES.md)：测试和发布验收要求，包括真实用户 E2E 发布门禁。记录某项 E2E 未执行不等于该门禁已通过。

## 翻译

- [翻译流程与批量队列](TRANSLATION_WORKFLOW.md)：队列、输出、恢复、拆行文字处理及验收。
- [语言资源](LANGUAGE_ASSETS.md)：术语表与翻译记忆。

## 项目记录和历史

- [项目记忆](MEMORY.md)：所有任务开始前必读；记录当前状态和历史。
- [历史归档](archive/)：保留整理前资料，不取代现行规范。旧文件路径保留跳转，避免已有引用失效。其他历史 PRD 暂留原处。
- [通用 Runner 参考](UPDATE_RUNNER_REFERENCE.md) 和 [授权](LICENSING.md) 分别独立维护。
