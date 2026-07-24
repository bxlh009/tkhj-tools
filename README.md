# TKHJ Tools 内容引擎

面向 **Learning + AI** 双领域的每日内容生成、质量门禁和静态网站发布系统。

## 每日目标

GitHub Actions 每天提供北京时间 18:00、21:00、次日 00:00 三个运行窗口：

1. 生成并发布 1 篇 Learning 文章。
2. 生成并发布 1 篇 AI 文章。
3. 运行质量门禁和网站审计。
4. 将通过门禁的稿件、公开清单与日志提交回仓库。

第一次成功后，后续窗口会检测当天已发布状态并跳过；第一次遇到 API、RSS
或质量门禁临时失败时，后续窗口继续重试，不会重复发布。

AI 有合格重大新闻时生成来源限定的新闻分析；没有时从带官方来源的
常青主题队列中选择工作流、提示词或评估主题。不得保存短占位稿凑数。

## 内容链路

```text
vars / RSS / 官方来源主题
        ↓
source-grounded prompt
        ↓
scripts/generate.py 或 scripts/daily_ai_news.py
        ↓
scripts/content_quality.py
        ↓ 仅 PASS
output/ 保留生成稿
        ↓
scripts/publish_article.py
        ↓
site/content/*.md + guides.json
        ↓
site/build.py
        ↓
site/_site
```

`output/` 是生成记录，不能单独进入网站。只有通过质量门禁并被
`publish_article.py` 登记进 `site/content/guides.json` 的文章才会公开。

## 关键文件

```text
rules/WRITING_RULES.md             双领域事实与质量规则
prompts/system_prompt_editorial.md 统一、非虚构作者系统提示词
prompts/exam-method-prompt.md      Learning 生成任务
prompts/ai-news-prompt.md          AI 生成任务
scripts/generate.py                通用生成器
scripts/daily_generate.py          每日双领域入口
scripts/daily_ai_news.py           AI 新闻发现与常青主题回退
scripts/content_quality.py         阻断式质量门禁
scripts/publish_article.py         公开内容与清单登记
site/build.py                      静态网站构建
```

## 质量门禁

自动稿件出现以下任一问题就不会发布：

- 未达到要求字数或缺少可扫描结构；
- 没有提供来源；
- 虚构教师、学生、测试经验、成绩、用户量、引用或结果承诺；
- 存在待填占位符；
- Learning 缺少两个原创练习以及答案推理；
- AI 缺少局限、不确定性或读者决策；
- 与同领域既有草稿相似度达到 30%；
- 模型返回空内容、JSON 元数据或 API 调用失败。

Learning 生成失败会更换主题，最多尝试3次。AI 会按“新事件优先、常青官方
主题回退”的顺序尝试最多3个主题。当天配额不完整时 GitHub Actions 失败，
不会把失败稿伪装成成功发布。

## 本地使用

PowerShell 设置 API key：

```powershell
$env:AGNES_API_KEY = "your-key"
```

生成 Learning 草稿但不公开：

```powershell
python scripts\generate.py --type exam --vars vars\example-toefl-reading.json
```

生成、过门禁并自动进入公开清单：

```powershell
python scripts\generate.py --type exam --vars vars\example-toefl-reading.json --publish
```

运行完整每日任务：

```powershell
python scripts\daily_generate.py
```

## 回填历史时间线

查看从2026年7月6日至7月24日还缺哪些日期：

```powershell
python scripts\backfill_timeline.py --start 2026-07-06 --end 2026-07-24 --dry-run
```

本地配置 `AGNES_API_KEY` 后执行实际回填：

```powershell
python scripts\backfill_timeline.py --start 2026-07-06 --end 2026-07-24
```

也可以在 GitHub 的 Actions 页面手动运行 `Backfill Content Timeline`。它会
使用仓库 Secret `AGNES_API_KEY`，无需在日志或代码中暴露密钥。脚本按
`guides.json` 检测每个领域已有的发布日期，因此中断后可安全重跑。

## 构建与测试

```powershell
python scripts\run_all_tests.py
python scripts\test_content_quality.py
python site\build.py
python scripts\audit_adsense_readiness.py
```

构建输出为 `site/_site`。Cloudflare Pages 配置：

```text
Build command: python site/build.py
Build output directory: site/_site
Production branch: main
```

## 发布规则

- 公开作者统一为 TKHJ Tools Editorial Team。
- 自动化和 AI 辅助必须披露。
- 考试格式依赖官方考试机构页面。
- 时效性 AI 内容优先使用产品或机构的一手资料。
- 供应商声明必须明确归因，不能写成独立实测结论。
- 自动发布不等于事实已由第三方独立确认；重要内容仍应定期抽查。

Google 不保证任何技术或内容调整一定通过 AdSense。申请复审前应确认生产
环境已部署最新版本、旧低价值页面已下线、站点地图可抓取。
