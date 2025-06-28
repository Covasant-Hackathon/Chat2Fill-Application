import os

EXCLUDE_DIRS = {'node_modules','env','.git','myenv', '__pycache__'}

def print_tree(start_path='.', prefix=''):
    entries = sorted(os.listdir(start_path))
    entries = [e for e in entries if e not in EXCLUDE_DIRS]

    for idx, entry in enumerate(entries):
        full_path = os.path.join(start_path, entry)
        connector = '└── ' if idx == len(entries) - 1 else '├── '
        print(prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = '    ' if idx == len(entries) - 1 else '│   '
            print_tree(full_path, prefix + extension)

# Run it
print_tree()
