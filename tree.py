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
def print_folders(start_path='.', prefix=''):
    entries = sorted(os.listdir(start_path))
    entries = [e for e in entries if e not in EXCLUDE_DIRS]
    folders = [e for e in entries if os.path.isdir(os.path.join(start_path, e))]

    for idx, folder in enumerate(folders):
        full_path = os.path.join(start_path, folder)
        connector = '└── ' if idx == len(folders) - 1 else '├── '
        print(prefix + connector + folder)
        extension = '    ' if idx == len(folders) - 1 else '│   '
        print_folders(full_path, prefix + extension)

def print_excluded_folders(start_path='.', prefix=''):
    entries = sorted(os.listdir(start_path))
    folders = [e for e in entries if os.path.isdir(os.path.join(start_path, e))]
    for idx, folder in enumerate(folders):
        full_path = os.path.join(start_path, folder)
        connector = '└── ' if idx == len(folders) - 1 else '├── '
        print(prefix + connector + folder)
        # If folder is in EXCLUDE_DIRS, don't recurse into it
        if folder not in EXCLUDE_DIRS:
            extension = '    ' if idx == len(folders) - 1 else '│   '
            print_excluded_folders(full_path, prefix + extension)

print_excluded_folders()
print_folders()