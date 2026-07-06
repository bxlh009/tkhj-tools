# 内容引擎

考试 + AI 站群的自动化生产基地。

一、目录结构

    content-engine/
      rules/
        WRITING_RULES.md           写作规则（所有 prompt 和脚本的根）
      prompts/
        exam-method-prompt.md      考试方法论文 prompt 模板
        ai-news-prompt.md          AI 新闻/工具评测 prompt 模板
      vars/
        example-toefl-reading.json 考试变量示例
        example-ai-gpt5.json       AI 变量示例
      scripts/
        generate.py                文章生成脚本
        check_similarity.py        相似度检测脚本
        config.json                API 配置
      output/                      GPT 生成的文章落地目录

二、快速开始

1 设置环境变量

    set OPENAI_API_KEY=sk-xxx         Windows Cmd
    $env:OPENAI_API_KEY = "sk-xxx"    PowerShell

2 生成一篇 TOEFL 阅读方法论文章

    python scripts/generate.py --type exam --vars vars/example-toefl-reading.json

3 生成一篇 AI 新闻对比文章

    python scripts/generate.py --type ai --vars vars/example-ai-gpt5.json

4 发布前检测相似度

    python scripts/check_similarity.py --threshold 0.30

三、变量文件格式

每篇文章对应一个 JSON 文件，根据所选模板填写变量。

考试模板变量
    exam_name          TOEFL / IELTS / GRE / SAT / GMAT / LSAT / MCAT
    section_name       阅读 / 写作 / 听力 / 口语 / 词汇
    years              3-8（教龄体感）
    bottleneck_score   阅读卡在 22
    min_words          1500
    max_words          2500
    primary_keyword    SEO 主关键词
    long_tail_keywords [...]
    slug              URL 路径片段

AI 模板变量
    type               ai-news / tool-review / comparison
    target_audience   人群描述
    category           ai-news / tool-review / comparison
    primary_keyword    SEO 主关键词
    long_tail_keywords [...]
    slug              URL 路径片段

四、写作规则核心要点（详见 rules/WRITING_RULES.md）

1 作者身份固定为 Evan，带过 300+ 学生的 TOEFL/GRE 讲师 + AI 工具研究员
2 版权红线：不得复制真题原文，不得使用官方 Logo，不得声称官方授权
3 例题必须改写：独立编写场景、替换人物、同义替换
4 每篇文章发布前必须过自查清单：经验句、例题、关键词、免责声明缺一不可
5 发布前相似度必须 < 30%，避免内容自噬

五、发布工作流

    写变量 JSON
        ↓
    generate.py 调用
        ↓
    output/ 产出草稿
        ↓
    人工事实核查（数据、价格、例题答案）
        ↓
    替换模板占位符、添加图片
        ↓
    check_similarity.py 检测相似度
        ↓
    提交到 Git / 部署到 tkjtools.io 主站

六、配置说明

    api.model          gpt-4o-mini     主力模型（性价比高）
    api.temperature    0.7             略高以提升文章多样性
    api.max_tokens     4096            限制单篇最长输出
    output_dir         ../output       生成文件落地位置

七、依赖说明

仅依赖 Python 3.8+ 内建库：urllib / json / re / pathlib
不依赖任何 pip 包（无 requests / openai SDK）
唯一外部依赖：OpenAI 兼容的 API key

八、扩展新文章类型

在 prompts/ 新建 xxx-prompt.md，模板中引用 {变量名}
在 vars/ 新建示例 JSON
在 generate.py argparse choices 加上新类型
主调逻辑中增加类型分发
