with open('data/screen_decisions.json', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('"action":', '"decision":')
with open('data/screen_decisions.json', 'w', encoding='utf-8') as f:
    f.write(text)
