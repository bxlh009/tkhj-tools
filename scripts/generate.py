import pathlib, re, random, statistics, sys, json, os, argparse
import urllib.request, urllib.error
import time

import importlib
from datetime import datetime

SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_FILE = SCRIPTS_DIR / 'config.json'
CONFIG = json.loads(CONFIG_FILE.read_text())
PROMPTS   = SCRIPTS_DIR.parent / 'prompts'
RULES_F   = SCRIPTS_DIR.parent / 'rules' / 'WRITING_RULES.md'
SYSP_F    = PROMPTS / 'system_prompt_layer1.md'
EXAM_OUT  = SCRIPTS_DIR.parent / 'output' / 'exams'
AI_OUT   = SCRIPTS_DIR.parent / 'output' / 'ai'

def get_api_key():
    k = os.environ.get(CONFIG['api']['api_key_env'])
    if not k or not k.strip(): sys.exit('[ERROR] env missing')
    return k

def read(p): return pathlib.Path(p).read_text(encoding='utf-8')
def inj(tpl, v):
    for k, val in v.items(): tpl = tpl.replace('{'+k+'}', str(val))
    return tpl
def read_json(p): return json.loads(read(p))

def call_api(system, user, retries=3, base_delay=5):
    payload = {'model':CONFIG['api']['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}],
               'temperature':CONFIG['api']['temperature'],'top_p':CONFIG['api'].get('top_p',1.0),'max_tokens':CONFIG['api']['max_tokens']}
    req = urllib.request.Request(CONFIG['api']['base_url'], data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+get_api_key()}, method='POST')
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body = json.loads(r.read().decode())
            print('[INFO] prompt='+str(body.get('usage',{}).get('prompt_tokens'))+' cmp='+str(body.get('usage',{}).get('completion_tokens')))
            return body['choices'][0]['message']['content']
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries:
                delay = base_delay * (2 ** (attempt - 1))
                print(f'[WARN] API attempt {attempt}/{retries} failed ({type(e).__name__}: {e}); retry in {delay}s')
                time.sleep(delay)
            else:
                print(f'[ERROR] API call failed after {retries} attempts: {e}')
    raise RuntimeError(f'API call failed after {retries} attempts: {last_err}')

# Layer 1 system prompt (loaded fresh per call with rules baked in)
def sys_prompt(atype):
    rules = read(RULES_F) if RULES_F.exists() else ''
    base = read(SYSP_F)
    return base.replace('{atype}', atype).replace('{rules}', rules)

def score(t, min_words=None, max_words=None):
    """10-dimensional quality score (each 0-10, total 0-100).

    Dimensions:
      1. Avg sentence length 8-22
      2. Burstiness (stdev >= 5)
      3. Contractions >= 20
      4. Rich punctuation (!?--)
      5. Vocal markers (honestly, look, you know, I mean, basically)
      6. No banned formatting (#, *, ---, | tables)
      7. Word count within target range
      8. 2+ worked examples with solutions
      9. CTA to tkjtools.io
      10. Disclaimer present
    """
    t = t.split('---',1)[-1] if t.strip().startswith('---') else t
    wds = t.split()
    if not wds: return 0, 'EMPTY', {}
    lens = [len(s.split()) for s in re.split(r'[.!?]+', t) if len(s.split())>1]
    if not lens: lens=[1]
    t_norm = t.replace('’', "'").replace('‘', "'")  # normalize Unicode apostrophes
    contr = len(re.findall(r"[A-Za-z]+'[A-Za-z]+", t_norm))
    dash = t_norm.count('--')+t_norm.count('—')+t_norm.count('–')
    excl = t_norm.count('!'); qmark = t_norm.count('?')
    ev = statistics.stdev(lens) if len(lens)>1 else 0
    avg = sum(lens)/len(lens)
    vocal_markers = ['honestly', 'look,', 'you know', 'i mean,', 'basically,', 'turns out', 'let me be clear', 'no wait']
    vocal_count = sum(t_norm.lower().count(m) for m in vocal_markers)

    # points
    p1 = 10 if 8<=avg<=22 else 0
    p2 = 10 if ev>=5 else 0
    p3 = 10 if contr>=20 else (5 if contr>=10 else 0)
    p4 = 10 if dash+excl+qmark>=10 else (5 if dash+excl+qmark>=5 else 0)
    p5 = 10 if vocal_count>=3 else (5 if vocal_count>=1 else 0)
    # formatting bans
    has_banned_format = bool(re.search(r'(^#{1,6}\s|\|.*\||^\s*[-*]\s|---)', t_norm, re.M))
    p6 = 0 if has_banned_format else 10
    # word count
    word_count = len(wds)
    if min_words and max_words:
        p7 = 10 if min_words<=word_count<=max_words else (5 if word_count>=min_words*0.8 else 0)
    else:
        p7 = 10
    # worked examples (>=2 with Solution/思路)
    example_count = len(re.findall(r'(Worked Example|Example \d|Solution|解题思路)', t, re.I))
    p8 = 10 if example_count>=2 else (5 if example_count>=1 else 0)
    # CTA
    p9 = 10 if re.search(r'tkjtools\.io', t) else 0
    # disclaimer
    p10 = 10 if re.search(r'(disclaimer|independently written|not endorsed|不代表.*官方)', t, re.I) else 0

    total = p1+p2+p3+p4+p5+p6+p7+p8+p9+p10
    details = {
        'avg_len': round(avg,1), 'burstiness': round(ev,1), 'contractions': contr,
        'punctuation': dash+excl+qmark, 'vocal_markers': vocal_count,
        'banned_format': has_banned_format, 'word_count': word_count,
        'examples': example_count, 'cta': p9>0, 'disclaimer': p10>0,
    }
    return total, ('PASS' if total>=75 else 'WARN'), details


def strip_banned_formatting(text):
    """Strip banned markdown formatting from article body (preserves frontmatter)."""
    fm, body = split_fm(text)
    lines = body.split('\n')
    out = []
    fixes = 0
    for line in lines:
        orig = line
        # strip heading markers
        line = re.sub(r'^#{1,6}\s+', '', line)
        # convert horizontal rules to paragraph breaks (don't delete — avoids blank gaps)
        if re.match(r'^[_*-]{3,}\s*$', line):
            fixes += 1
            out.append('')
            continue
        # strip table rows
        if re.match(r'^\s*\|.*\|\s*$', line):
            fixes += 1
            continue
        # strip bullet markers at line start
        line = re.sub(r'^\s*[-*]\s+', '', line)
        if line != orig:
            fixes += 1
        out.append(line)
    return fm + '\n'.join(out), fixes


def split_fm(t):
    m = re.match(r'^---\n.*?\n---\n', t, re.S)
    return (m.group(0), t[m.end():]) if m else ('', t)

# Layer 2e: paragraph-level GPT rewrite that injects contractions
CASUAL_SYS = "You are Evan, blogger. Rewrite this paragraph using HEAVY contractions (it's, don't, can't, I'm, you're, they're, here's, there's, won't, wouldn't, shouldn't, hasn't, we've, didn't), add spoken rhythm (em-dashes, interruptions), make it sound genuinely human. Same meaning and facts, roughly same length. Output ONLY the rewritten text."
def rewrite_para(p):
    if len(p.split())<15: return p
    try:
        return call_api(CASUAL_SYS, 'Paragraph to rewrite:\n'+p)
    except SystemExit: return p
def force_casual(text, n=6):
    fm, body = split_fm(text)
    paras = body.split('\n\n')
    cands = [(i, p) for i, p in enumerate(paras) if len(p.split())>25 and not p.strip().startswith('#')]
    random.shuffle(cands)
    for i, p in cands[:n]:
        paras[i] = rewrite_para(p)
    return fm + '\n\n'.join(paras)

# Layer 2bcd: programmatic fallbacks
PLAIN=["it is","do not","does not","cannot","I am","you are","they are","that is","there is","has not","have not"]
CO=["it's","don't","doesn't","can't","I'm","you're","they're","that's","there's","hasn't","haven't"]
PAIRS=list(zip(PLAIN,CO))
def force_contr(text, target=18):
    fm, body = split_fm(text)
    random.shuffle(PAIRS); ch=0
    for pl, co in PAIRS:
        if ch>=target: break
        rx=re.compile(r'(?<![a-zA-Z-])'+re.escape(pl)+r'(?![a-zA-Z-])',re.I)
        ms=list(rx.finditer(body))
        for mat in reversed(ms[:min(len(ms),target-ch)]):
            s,e=mat.span()
            body=body[:s]+(co[0].upper()+co[1:] if body[s].isupper() else co)+body[e:]
            ch+=1
    return fm+body, ch

def force_dashes(text, n=6):
    fm, body = split_fm(text)
    for _ in range(n):
        m=re.search(r',\s+(actually|basically|honestly|frankly|look|yes|no|well),',body,re.I)
        if not m: break
        body=body[:m.start()]+' \u2014 '+random.choice(['actually','honestly'])+' \u2014 '+body[m.end():]
    return fm+body

def force_merge(text):
    fm, body = split_fm(text)
    ss=re.split(r'(?<=[.!?])\s+', body); out=[]; i=0; mg=0
    while i<len(ss) and mg<4:
        w1=ss[i].split()
        if 3<=len(w1)<=9 and i+1<len(ss) and 3<=len(ss[i+1].split())<=9:
            c=random.choice([', and', ', but', ', so', ', yet'])
            out.append(ss[i].rstrip('.!?')+c+' '+ss[i+1][0].lower()+ss[i+1][1:])
            i+=2; mg+=1; continue
        out.append(ss[i]); i+=1
    out.extend(ss[i:])
    return fm+' '.join(out)

def force_markers(text):
    MARKERS=['honestly,', 'look,', 'I mean,', 'basically,', 'turns out,']
    fm, body = split_fm(text)
    paras=body.split('\n\n')
    n_target=max(4, len(paras)//4)
    for idx in random.sample(range(len(paras)), min(n_target, len(paras))):
        p=paras[idx]
        if not p.strip() or p.strip().startswith(('#','-','*','|')): continue
        ss=re.split(r'(?<=[.!?])\s+', p)
        if len(ss)<2: continue
        ss.insert(random.randint(1,len(ss)-1),random.choice(MARKERS))
        paras[idx]=' '.join(ss)
    return fm+'\n\n'.join(paras)

def ensure_dir(p): p.mkdir(parents=True, exist_ok=True)
def first_free(d, slug, ext='.md'):
    b=d/(slug+ext)
    if not b.exists(): return b
    n=2
    while (d/('%s-%d%s'%(slug,n,ext))).exists(): n+=1
    return d/('%s-%d%s'%(slug,n,ext))

def extract_slug(content):
    m=re.match(r'^---\n.*?\n---', content, re.S)
    if not m: return None
    for ln in m.group(0).splitlines():
        if 'slug:' in ln:
            return ln.split('slug:')[1].strip().strip("'\"")
    return None

def pick_template(atype):
    """Pick a random template letter (A-H) for the given article type."""
    import random
    return random.choice("ABCDEFGHIJKLMNOP" if atype == "ai" else "ABCDEFGHIJKL")

def wc(t):
    return len(re.findall(r'[A-Za-z一-鿿]+', t.split('---')[-1] if t.startswith('---') else t))

def write_output(content, slug, out_dir):
    ensure_dir(out_dir)
    p=first_free(out_dir, slug)
    content = content.replace('’', "'").replace('‘', "'")  # normalize Unicode apostrophes
    p.write_text(content, encoding='utf-8')
    return p

def ensure_cta_and_disclaimer(article, atype):
    """Append CTA and disclaimer if missing from the article."""
    import re as _re
    has_cta = bool(_re.search(r'tkjtools', article))
    has_disclaimer = bool(_re.search(r'(disclaimer|independently written|not endorsed|不代表.*官方)', article, _re.I))
    tail = ""
    # CTA links removed per user request - no tkjtools.io self-promotion
    if not has_disclaimer:
        tail += "\n> Disclaimer: This is independently written educational content. Not endorsed by any exam body or vendor. Example questions are rewritten for teaching purposes.\n"
    if tail:
        article = article.rstrip() + tail
    return article


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--type', required=True, choices=['exam','ai'])
    ap.add_argument('--vars', required=True)
    args=ap.parse_args()
    tpl = read(PROMPTS / ('exam-method-prompt.md' if args.type=='exam' else 'ai-news-prompt.md'))
    vars_data = read_json(args.vars)
    vars_data["current_date"] = datetime.now().strftime("%Y-%m-%d")
    up = inj(tpl, vars_data)
    # Random format seed for article variability + template rotation
    tpl_letter = pick_template(args.type)
    up = up + "\n\n--- FORMAT INSTRUCTION ---\nStart with a relatable student mistake or confusion. Mix short sections and long deep-dives. No numbered lists.\n"
    up = up + f"\nYOU MUST FOLLOW Template {tpl_letter} from the Structure Rotation section. Do not deviate from that skeleton.\n"
    print('[INFO] generating [%s]...' % args.type)
    article = call_api(sys_prompt(args.type), up)
    # Clean stray frontmatter / YAML / JSON leaking into body
    try:
        _clean = importlib.import_module("_clean_body")
        cleaned = _clean.clean_body(article)
        if cleaned != article:
            print("[OK]   cleaned frontmatter/YAML leakage from body")
        article = cleaned
    except Exception as _e:
        print(f"[WARN] _clean_body failed: {_e}")

    min_w = vars_data.get("min_words", 1500)
    max_w = vars_data.get("max_words", 2500)
    sc, verdict, det = score(article, min_w, max_w)
    print("[OK]   Score: %d/100 verdict=%s | %s" % (sc, verdict, det))
    # Layer 2e: GPT paragraph rewrite (ONLY other instance adds contractions)
    if verdict == 'WARN':
        article = force_casual(article, n=6)
        sc, verdict, det = score(article, min_w, max_w)
        print('[OK]   Layer-2e casual rewrite: %d/100 | %s' % (sc, det))
    # Layer 2bcd: programmatic fallbacks
    if verdict == 'WARN':
        article, c1 = force_contr(article, target=18)
        article = force_dashes(article, n=5)
        article = force_merge(article)
        article = force_markers(article)
        sc, verdict, det = score(article, min_w, max_w)
        print('[OK]   Layer-2bcd: %d contractions injected; new score: %d/100 | %s' % (c1, sc, det))
    # Layer 2f: strip banned formatting that survived (#, *, ---, |)
    if verdict == 'WARN' and det.get('banned_format'):
        article, n_fix = strip_banned_formatting(article)
        sc, verdict, det = score(article, min_w, max_w)
        print('[OK]   Layer-2f formatting strip: %d fixes; new score: %d/100' % (n_fix, sc))
    if verdict == 'WARN':
        missing = [k for k, v in {'examples': det.get('examples',0)>=2, 'cta': det.get('cta'), 'disclaimer': det.get('disclaimer'), 'word_count': det.get('word_count',0)>=min_w} .items() if not v]
        print('[WARN] still WARN; missing or weak: %s; needs ' % ', '.join(missing) if missing else '[WARN] still WARN; needs 5-min human polish')
    # Force-rewrite banned opening lines (Most students think...)
    try:
        from _force_opener import has_banned_opener, rewrite_opening
        if has_banned_opener(article):
            article = rewrite_opening(article, call_api)
            sc_after, _, _ = score(article, min_w, max_w)
            print("[OK]   opener rewritten; new score:", sc_after)
    except Exception as e_op:
        print("[WARN] opener fix failed:", e_op)

    # Auto-append CTA + disclaimer if missing
    article = ensure_cta_and_disclaimer(article, args.type)

    # Similarity check BEFORE writing (avoid content self-cannibalization)
    cur_out = EXAM_OUT if args.type == "exam" else AI_OUT
    try:
        from check_similarity import check_new_article
        too_sim, sim_name, sim_score = check_new_article(article, str(cur_out))
        if too_sim:
            print(f"[WARN] too similar to {sim_name} ({sim_score:.0%}); consider different vars")
        else:
            print(f"[OK]   similarity OK (max {sim_score:.0%} vs existing)")
    except Exception as e:
        print(f"[WARN] similarity check failed: {e}")

    slug = extract_slug(article) or 'untitled-'+datetime.now().strftime('%Y%m%d-%H%M%S')
    ensure_dir(cur_out)
    out = write_output(article, slug, cur_out)
    print('[OK]   written: %s (~%d words)' % (out, wc(article)))

if __name__ == '__main__':
    main()
