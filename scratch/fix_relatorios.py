import sys

file_path = r'c:\Users\2BAEP-32KVB92\Desktop\Projetos\BAEP-Controle-Materiais\relatorios\views.py'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    with open(file_path, 'r', encoding='latin-1') as f:
        content = f.read()

# Fix the specific corrupted block
target = """                    estoque_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        material.quantidade_disponivel,
                        material.get_estado_display()
                    ])"""

replacement = """                    estoque_data.append([
                        material.identificacao,
                        material.get_tipo_display(),
                        f"{material.quantidade:.2f}",
                        f"{material.quantidade_disponivel:.2f}",
                        material.get_estado_display()
                    ])"""

if target in content:
    content = content.replace(target, replacement)
    print("Fixed corrupted table.")
else:
    print("Target block not found precisely.")
    # Try a more loose match
    import re
    pattern = r'estoque_data\.append\(\[\s+material\.identificacao,\s+material\.get_tipo_display\(\),\s+material\.quantidade_disponivel,\s+material\.get_estado_display\(\)\s+\]\)'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        print("Fixed corrupted table with regex.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
