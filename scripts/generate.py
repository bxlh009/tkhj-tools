import pathlib, re, random, statistics, sys, json, os, argparse
import urllib.request, urllib.error
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
    if not k: sys.exit('[ERROR] env missing')
    return k

def read(p): return pathlib.Path(p).read_text(encoding='utf-8')
def inj(tpl, v):
    for k, val in v.items(): tpl = tpl.replace('{'+k+'}', str(val))
    return tpl
def read_json(p): return json.loads(read(p))

def call_api(system, user):
    payload = {'model':CONFIG['api']['model'],'messages':[{'role':'system','content':system},{'role':'user','content':user}],
               'temperature':CONFIG['api']['temperature'],'top_p':CONFIG['api'].get('top_p',1.0),'max_tokens':CONFIG['api']['max_tokens']}
    req = urllib.request.Request(CONFIG['api']['base_url'], data=json.dumps(payload).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+get_api_key()}, method='POST')
    with urllib.request.urlopen(req, timeout=180) as r:
        body = json.loads(r.read().decode())
    print('[INFO] prompt='+str(body.get('usage',{}).get('prompt_tokens'))+' cmp='+str(body.get('usage',{}).get('completion_tokens')))
    return body['choices'][0]['message']['content']

# Layer 1 system prompt (loaded fresh per call with rules baked in)
def sys_prompt(atype):
    rules = read(RULES_F) if RULES_F.exists() else ''
    base = read(SYSP_F)
    return base.replace('{atype}', atype).replace('{rules}', rules)

def score(t):
    t = t.split('---',1)[-1] if t.strip().startswith('---') else t
    wds = t.split()
    if not wds: return 0, 'EMPTY'
    lens = [len(s.split()) for s in re.split(r'[.!?]+', t) if len(s.split())>1]
    if not lens: lens=[1]
    t = t.replace('’', "'").replace('‘', "'")  # normalize Unicode apostrophes
    contr = len(re.findall(r"[A-Za-z]+'[A-Za-z]+", t))
    dash = t.count('--')+t.count('—')+t.count('–')
    excl = t.count('!'); qmark = t.count('?')
    ev = statistics.stdev(lens) if len(lens)>1 else 0
    avg = sum(lens)/len(lens)
    sc = (25 if 8<=avg<=22 else 0)+(25 if ev>=5 else 0)+(25 if contr>=15 else 0)+(25 if dash+excl+qmark>=10 else 0)
    return sc, ('PASS' if sc>=75 else 'WARN')

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

def wc(t):
    return len(re.findall(r'[A-Za-z一-鿿]+', t.split('---')[-1] if t.startswith('---') else t))

def write_output(content, slug, out_dir):
    ensure_dir(out_dir)
    p=first_free(out_dir, slug)
    content = content.replace('’', "'").replace('‘', "'")  # normalize Unicode apostrophes
    p.write_text(content, encoding='utf-8')
    return p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--type', required=True, choices=['exam','ai'])
    ap.add_argument('--vars', required=True)
    args=ap.parse_args()
    tpl = read(PROMPTS / ('exam-method-prompt.md' if args.type=='exam' else 'ai-news-prompt.md'))
    vars_data = read_json(args.vars)
    vars_data["current_date"] = datetime.now().strftime("%Y-%m-%d")
    up = inj(tpl, vars_data)
    # Random format seed for article variability
    up = up + "\n\n--- FORMAT INSTRUCTION ---\nStart with a relatable student mistake or confusion. Mix short sections and long deep-dives. No numbered lists.\n"
    print('[INFO] generating [%s]...' % args.type)
    article = call_api(sys_prompt(args.type), up)
    sc, verdict = score(article)
    print('[OK]   Score: %d/100 verdict=%s' % (sc, verdict))
    # Layer 2e: GPT paragraph rewrite (ONLY other instance adds contractions)
    if verdict == 'WARN':
        article = force_casual(article, n=6)
        sc, verdict = score(article)
        print('[OK]   Layer-2e casual rewrite: %d/100' % sc)
    # Layer 2bcd: programmatic fallbacks
    if verdict == 'WARN':
        article, c1 = force_contr(article, target=18)
        article = force_dashes(article, n=5)
        article = force_merge(article)
        article = force_markers(article)
        sc, verdict = score(article)
        print('[OK]   Layer-2bcd: %d contractions injected; new score: %d/100' % (c1, sc))
    if verdict == 'WARN':
        print('[WARN] still WARN; 5-min human polish pushes >90')
    # Force-rewrite banned opening lines (Most students think...)
    try:
        import importlib, sys as _sys
        _mod = importlib.import_module("_force_opener")
        if _mod.has_banned_opener(article):
            article = _mod.rewrite_opening(article, call_api)
            sc_after, _ = score(article)
            print("[OK]   opener rewritten; new score:", sc_after)
    except Exception as e_op:
        print("[WARN] opener fix failed:", e_op)

    slug = extract_slug(article) or 'untitled-'+datetime.now().strftime('%Y%m%d-%H%M%S')
    cur_out = EXAM_OUT if args.type == "exam" else AI_OUT
    ensure_dir(cur_out)
    out = write_output(article, slug, cur_out)
    print('[OK]   written: %s (~%d words)' % (out, wc(article)))

if __name__ == '__main__':
    main()