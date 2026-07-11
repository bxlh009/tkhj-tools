# All Auto-Scripts Inventory

## _audit_build.py
- **Function**: Audit all articles: unfilled vars / too short / bad YAML
- **Schedule**: manual
- **Outputs**: stdout

## _build_backup.py
- **Function**: (backup)
- **Schedule**: N/A
- **Outputs**: N/A

## _build_backup2.py
- **Function**: (backup)
- **Schedule**: N/A
- **Outputs**: N/A

## _clean_body.py
- **Function**: Strip leaked frontmatter from LLM output
- **Schedule**: called by generate.py
- **Outputs**: cleaned text

## _full_audit.py
- **Function**: Full audit self-deletes after run
- **Schedule**: manual
- **Outputs**: stdout

## _gen.py
- **Function**: Site generation helper
- **Schedule**: N/A
- **Outputs**: stdout

## _psych_patch.py
- **Function**: Add psychology framework to persona JSON
- **Schedule**: once manual
- **Outputs**: prompts/*.json

## _sanitize.py
- **Function**: Remove exaggerated numbers from persona JSON
- **Schedule**: once manual
- **Outputs**: prompts/*.json

## ai_news_monitor.py
- **Function**: AI news monitoring standalone
- **Schedule**: manual
- **Outputs**: stdout

## analyze.py
- **Function**: Analysis tool unconfirmed
- **Schedule**: manual
- **Outputs**: unknown

## build.py
- **Function**: Build static HTML site from output/ + static/
- **Schedule**: called by daily_generate
- **Outputs**: _site/

## check_similarity.py
- **Function**: Jaccard + Cosine similarity between all articles
- **Schedule**: manual
- **Outputs**: stdout + exit code

## daily_ai_news.py
- **Function**: RSS -> Score -> Agnes LLM -> output/ai/
- **Schedule**: daily via daily_generate.py
- **Outputs**: output/ai/*.md

## daily_generate.py
- **Function**: Main daily pipeline: 1 exam + 1 AI news + rebuild site
- **Schedule**: UTC 10:00 GitHub Actions
- **Outputs**: output/* + _site/

## final_verify.py
- **Function**: Final verification
- **Schedule**: manual
- **Outputs**: unknown

## generate.py
- **Function**: Single article: vars -> LLM -> 10-dim score -> 5-layer clean -> output
- **Schedule**: manual / called by daily_generate
- **Outputs**: output/{exams,ai}/*.md

## run_all_tests.py
- **Function**: Runs test_backend + test_suite + test_scoring
- **Schedule**: manual
- **Outputs**: stdout

## setup_daily.py
- **Function**: Register Windows Task Scheduler 08:00 ET
- **Schedule**: once
- **Outputs**: Windows Task

## setup_scheduler.py
- **Function**: Alternative scheduler registration
- **Schedule**: once
- **Outputs**: Windows Task

## test_backend.py
- **Function**: 109 core function tests P0/P1
- **Schedule**: manual
- **Outputs**: stdout + exit code

## test_scoring.py
- **Function**: Scoring logic smoke test
- **Schedule**: manual
- **Outputs**: stdout

## test_suite.py
- **Function**: Comprehensive test suite
- **Schedule**: manual
- **Outputs**: stdout

## verify_site.py
- **Function**: Verify rebuilt site meets requirements
- **Schedule**: manual
- **Outputs**: stdout
