text = open('data/raw_draft.md', encoding='utf-8').read()
v = text.find('**Verdict**')
vt = text[v:]
wv = len(vt.split())
wt = len(text.split())
pct = wv / wt * 100
print(f'{wv}/{wt} = {pct:.1f}%')
print('PASS' if pct <= 15 else 'FAIL')
