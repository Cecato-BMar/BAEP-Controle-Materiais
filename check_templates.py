import os, re

with open('estoque/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Procura render(request, 'estoque/template.html', ...)
templates = re.findall(r"render\(request, ['\"](.+?)['\"]", content)

print("Checking templates used in views.py...")
missing = []
for t in sorted(set(templates)):
    path = os.path.join('templates', t)
    if not os.path.exists(path):
        missing.append(t)
        print(f"MISSING: {t}")
    else:
        print(f"FOUND:   {t}")

if not missing:
    print("\nSUCCESS: All templates found!")
else:
    print(f"\nTOTAL MISSING: {len(missing)}")
