import os

def fix_file(path):
    try:
        with open(path, 'rb') as f:
            content = f.read()
        
        # Detect UTF-16 BOM
        if content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
            print(f"Fixing UTF-16: {path}")
            text = content.decode('utf-16')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
        elif b'\x00' in content:
            print(f"Fixing null bytes: {path}")
            if path.endswith('__init__.py'):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('')
            else:
                try:
                    text = content.decode('utf-8').replace('\x00', '')
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(text)
                except:
                    print(f"Failed to fix: {path}")
    except Exception as e:
        print(f"Error processing {path}: {e}")

root_dir = r'C:\Users\basse\OneDrive\Bureau\virtual-closet\backend'
for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.py'):
            fix_file(os.path.join(root, file))
