# TKHJ Tools 内容引擎

面向 **Learning + AI** 双领域的候选稿生成、阻断式质量门禁、受控自动发布与静态网站策展系统。

## 发布边界

自动发布只在两个固定栏目时段运行，不设每日配额，也不会为了凑数强制产出：

1. 草稿通过确定性质量门后保存在 `output/`。
2. 自动稿必须使用维护者预先批准的阅读路径；Learning 至少一个官方来源，AI 至少两个独立官方来源。
3. 发布器会重新运行质量门，再登记到 `guides.json` 与 `curation.json`。
4. 翻译、整站构建、回归或 AdSense 就绪审计任一失败，都不会提交公开内容。

`Controlled Automatic Publishing` 在周一评估 Learning、周四评估 AI，每次最多一篇；
无合格主题就安全跳过。`Backfill Editorial Drafts` 仍只允许手动触发并只提交草稿。

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
site/content/*.md + guides.json + curation.json 中的明确决策
        ↓
site/build.py
        ↓
site/_site
```

`output/` 是生成记录，不能单独进入网站。手动发布仍需要显式编辑批准；自动发布则必须
通过预批准路径、官方来源、发布前复检和整站验证四层规则，否则构建会阻断。

## 关键文件

```text
rules/WRITING_RULES.md             双领域事实与质量规则
prompts/system_prompt_editorial.md 统一、非虚构作者系统提示词
prompts/exam-method-prompt.md      Learning 生成任务
prompts/ai-news-prompt.md          AI 生成任务
scripts/generate.py                通用生成器
scripts/daily_generate.py          双领域候选稿入口
scripts/daily_ai_news.py           AI 新闻发现与常青主题回退
scripts/content_quality.py         阻断式质量门禁
scripts/publish_article.py         公开内容与清单登记
site/build.py                      静态网站构建
```

## 质量门禁

自动稿件出现以下任一问题就不会进入编辑队列：

- 未达到要求字数或缺少可扫描结构；
- 没有提供来源；
- 虚构教师、学生、测试经验、成绩、用户量、引用或结果承诺；
- 存在待填占位符；
- 正文包含第二个 H1、重复 `Sources` 或重复段落灌水；
- 来源不是 HTTPS 实际发布方链接；
- Learning 缺少两个原创练习以及答案推理；
- AI 缺少局限、不确定性或读者决策；
- 与同领域既有草稿相似度达到 30%；
- 模型返回空内容、JSON 元数据或 API 调用失败。

Learning 生成失败会更换主题，最多尝试3次，选题耗尽后停止而不生成数字后缀重复稿。
自动 AI 只使用已批准的常青官方主题，不使用单一 RSS 新闻源。通过门禁不代表已通过
AdSense 审核；它只代表文章符合本站当前自动发布政策。

## 本地使用

PowerShell 设置 API key：

```powershell
$env:AGNES_API_KEY = "your-key"
```

生成 Learning 草稿但不公开：

```powershell
python scripts\generate.py --type exam --vars vars\example-toefl-reading.json
```

生成、过门禁并在明确编辑批准后登记到公开目录：

```powershell
python scripts\generate.py --type exam --vars vars\example-toefl-reading.json --publish --editorial-approval
```

随后必须在 `site/content/curation.json` 中将新 slug 选入阅读路径或明确排除，
再运行构建与 AdSense 就绪审计。

运行一次候选稿生成任务（不会发布）：

```powershell
python scripts\daily_generate.py
```

本地模拟受控自动发布（仍不会部署）：

```powershell
python scripts\daily_generate.py --track learning --auto-publish
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

也可以在 GitHub 的 Actions 页面手动运行 `Backfill Editorial Drafts`。它会
使用仓库 Secret `AGNES_API_KEY`，无需在日志或代码中暴露密钥。脚本按
公开目录和 `output/` 检测每个领域已有日期，因此中断后可安全重跑；它不会
修改公开目录或触发部署。

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
- 质量门通过不等于发布、独立事实核验、第三方认可或 AdSense 批准。

Google 不保证任何技术或内容调整一定通过 AdSense。申请复审前应确认生产
环境已部署最新版本、旧低价值页面已下线、站点地图可抓取。
