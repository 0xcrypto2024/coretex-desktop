import PyInstaller.__main__
import os
import shutil
import subprocess

def get_target_triple():
    try:
        result = subprocess.run(['rustc', '-vV'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith('host:'):
                return line.split(': ')[1].strip()
    except: pass
    return "x86_64-unknown-linux-gnu"

def build():
    triple = get_target_triple()
    binary_name = f"cortex-agent-{triple}"
    output_dir = os.path.join("..", "src-tauri", "binaries")
    os.makedirs(output_dir, exist_ok=True)
    if os.path.exists("dist"): shutil.rmtree("dist")
    if os.path.exists("build"): shutil.rmtree("build")
    # Clean spec file to force regeneration
    spec_file = f"{binary_name}.spec"
    if os.path.exists(spec_file): os.remove(spec_file)

    PyInstaller.__main__.run([
        'main.py',
        'notion_sync.py',
        'listener.py',
        'task_manager.py',
        f'--name={binary_name}',
        '--onefile',
        '--console',
        '--paths=.',
        '--add-data=templates:templates',
        '--add-data=system_prompt.txt:.',
        '--hidden-import=notion_sync',
        '--hidden-import=utils',
        '--hidden-import=task_manager',
        '--hidden-import=listener',
        '--hidden-import=uvicorn',
        '--hidden-import=fastapi',
        '--hidden-import=auto_session_manager',
        '--hidden-import=memory_manager',
        '--hidden-import=learning_service',
        '--clean'
    ])

    src = os.path.join("dist", binary_name)
    dst = os.path.join(output_dir, binary_name)
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"✅ Build Complete: {dst}")

if __name__ == "__main__": build()
