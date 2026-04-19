import sys
import os
import subprocess
import re
import readline
import glob
import locale
import ollama
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm

# --- 🛠 環境強制修正 ---
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    pass

if sys.stdin.encoding != 'utf-8':
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 🌐 核心配置 ---
SELF_PATH = os.path.abspath(__file__)
console = Console()
OLLAMA_HOST = 'http://100.69.30.107:11434' 
MODEL_NAME = 'gemma4'
MD_TICKS = chr(96) * 3

try:
    client = ollama.Client(host=OLLAMA_HOST)
except Exception as e:
    console.print(f"[bold red]❌ 無法連線至伺服器: {e}[/bold red]")

def path_completer(text, state):
    matches = glob.glob(os.path.expanduser(text) + '*')
    return (matches + [None])[state]

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(path_completer)

def extract_blocks(text, langs=r"\w*"):
    pattern = MD_TICKS + rf"(?:{langs})\s*\n(.*?)\n" + MD_TICKS
    return re.findall(pattern, text, re.DOTALL)

def run_git_cmds(cmds):
    for cmd in cmds:
        console.print(f"[dim]執行：{cmd}[/dim]")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            console.print(Panel(f"[bold red]Git 錯誤：[/bold red]\n{result.stderr}", border_style="red"))
            return False
    return True

def get_project_info():
    folder = os.path.basename(os.getcwd())
    if os.path.exists("GEMINI.md"):
        try:
            with open("GEMINI.md", "r", encoding="utf-8") as f: instr = f.read()
            return f"[{folder}]", f"[bold yellow]📁 專案：{folder}[/bold yellow]", instr
        except: pass
    return "[通用]", "[dim]🌍 5080 本地模式[/dim]", ""

def main():
    prompt_prefix, mode_text, system_instruction = get_project_info()
    history = []
    if system_instruction:
        history.append({'role': 'system', 'content': system_instruction})

    console.clear()
    help_menu = (
        f"[bold green]🔋 5080 智慧 Agent 完全體[/bold green] [dim]v3.2 (多語言解鎖版)[/dim]\n"
        f"{mode_text} | 模型：[white]{MODEL_NAME}[/white]\n"
        f"──────────────────────────────────────────\n"
        f"[cyan]📝 多行貼上 [/cyan] ⮕ [white]/multi[/white]\n"
        f"[green]💾 本地存檔 [/green] ⮕ [white]@save <訊息>[/white] | [blue]🚀 雲端同步 [/blue] ⮕ [white]@push \[訊息][/white]\n"
        f"[magenta]🧬 自我進化 [/magenta] ⮕ [white]@apply <路徑>[/white] (支援 Python/C/C++/YAML/JS...)\n"
        f"[red]⚡ 指令執行 [/red] ⮕ [white]@run <cmd>[/white] \n"
        f"[yellow]📖 讀取檔案 [/yellow] ⮕ [white]@read <路徑> <問題>[/white]\n"
        f"[cyan]👁️ 視覺分析 [/cyan] ⮕ [white]@image <路徑> <問題>[/white]\n"
        f"──────────────────────────────────────────\n"
        f"[dim]輸入 'exit' 離開，'clear' 清除畫面[/dim]"
    )
    console.print(Panel.fit(help_menu, border_style="green"))

    last_ai_response = ""

    while True:
        try:
            prompt_prefix, _, _ = get_project_info()
            user_input = input(f"\n❯ {prompt_prefix} 您：")
            
            image_paths = []
            payload = ""

            if user_input.strip() == "/multi":
                console.print("[dim]📝 已進入多行模式！請直接貼上內容。\n(貼完後，請在新的一行輸入 [white]/end[/white] 送出，或 [white]/cancel[/white] 取消)[/dim]")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "/end": break
                    if line.strip() == "/cancel":
                        lines = None
                        break
                    cleaned_line = line.rstrip()
                    if cleaned_line.endswith('|'): cleaned_line = cleaned_line[:-1].rstrip()
                    lines.append(cleaned_line)
                
                if lines is None: 
                    console.print("[yellow]已取消多行輸入。[/yellow]")
                    continue
                user_input = "\n".join(lines)
                console.print(f"[dim]✅ 已成功接收 {len(lines)} 行內容。[/dim]")

            if user_input.lower() in ['exit', 'quit']: break
            if not user_input.strip(): continue

            if user_input.startswith("@save"):
                msg = user_input.replace("@save", "", 1).strip().strip("\"'")
                if not msg:
                    console.print("[yellow]⚠️ 請提供存檔描述！[/yellow]"); continue
                if run_git_cmds(["git add .", f'git commit -m "{msg}"']):
                    console.print("[bold green]💾 已完成本地存檔。[/bold green]")
                continue

            elif user_input.startswith("@push"):
                msg = user_input.replace("@push", "", 1).strip().strip("\"'")
                git_cmds = ["git add .", f'git commit -m "{msg}"', "git push origin main"] if msg else ["git push origin main"]
                if run_git_cmds(git_cmds):
                    console.print("[bold blue]🚀 成功同步至 GitHub 雲端！[/bold blue]")
                continue

            elif user_input.startswith("@apply"):
                target = user_input.replace("@apply", "", 1).strip()
                if not target:
                    if "我的主程式代碼如下" in last_ai_response: target = SELF_PATH
                    else:
                        match_yml = re.search(r"(\.github/workflows/\w+\.yml)", last_ai_response)
                        target = match_yml.group(1) if match_yml else ""
                if not target:
                    console.print("[yellow]⚠️ 請指定路徑！[/yellow]"); continue
                
                # 🚀 v3.2 智慧副檔名路由器
                ext = os.path.splitext(target)[1].lower()
                if ext in ['.yml', '.yaml']: lang = r"yaml|yml"
                elif ext in ['.c', '.h']: lang = r"c"
                elif ext in ['.cpp', '.hpp', '.cc']: lang = r"cpp|c\+\+"
                elif ext in ['.sh', '.bash']: lang = r"bash|sh"
                elif ext in ['.js', '.json', '.html', '.css']: lang = r"javascript|js|json|html|css"
                elif ext in ['.md', '.txt', '']: lang = r"\w*"  # 無副檔名或文本，允許抓取任何代碼塊
                else: lang = r"python|py" # 預設保護 Python

                blocks = extract_blocks(last_ai_response, lang)
                if blocks:
                    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
                    with open(target, "w", encoding="utf-8") as f: f.write(blocks[0].strip())
                    console.print(f"[bold green]✅ 已寫入：{target}[/bold green]")
                else:
                    console.print(f"[yellow]⚠️ 找不到對應的代碼區塊 ({lang})。[/yellow]")
                continue

            elif user_input.startswith("@run"):
                cmd_arg = user_input.replace("@run", "", 1).strip()
                if not cmd_arg or any(x in cmd_arg for x in ["上面", "自動"]):
                    blocks = extract_blocks(last_ai_response, r"bash|sh|console")
                    if not blocks:
                        console.print("[yellow]⚠️ 找不到可執行的 shell/bash 指令區塊。[/yellow]"); continue
                    for c in blocks:
                        if Confirm.ask(f"執行 [cyan]{c}[/cyan]？", default=True): os.system(c)
                else:
                    if Confirm.ask(f"執行 [red]{cmd_arg}[/red]？", default=False): os.system(cmd_arg)
                continue

            elif user_input.startswith("@image"):
                parts = user_input.replace("@image", "", 1).strip().split(" ", 1)
                if parts and parts[0]:
                    img_path = os.path.expanduser(parts[0])
                    if os.path.exists(img_path):
                        image_paths.append(img_path)
                        payload = parts[1] if len(parts) > 1 else "請分析這張圖片。"
                        console.print(f"[dim]👁️ 已附加圖片：{img_path}[/dim]")
                    else:
                        console.print(f"[bold red]❌ 找不到圖片：{img_path}[/bold red]")
                        continue
                else:
                    console.print("[yellow]⚠️ 用法：@image <路徑> <問題>[/yellow]"); continue

            elif user_input.startswith("@read"):
                if user_input.strip() == "@read self" or user_input.startswith("@read self "):
                    user_prompt = user_input.replace("@read self", "", 1).strip()
                    with open(SELF_PATH, "r", encoding="utf-8") as f:
                        payload = f"{user_prompt}\n\n我的主程式代碼如下：\n{MD_TICKS}python\n{f.read()}\n{MD_TICKS}"
                    console.print(f"[dim]🧬 已讀取源碼...[/dim]")
                else:
                    parts = user_input.replace("@read", "", 1).strip().split(" ", 1)
                    if parts and parts[0]:
                        file_path = os.path.expanduser(parts[0])
                        user_prompt = parts[1] if len(parts) > 1 else ""
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                payload = f"{user_prompt}\n\n內容：\n{MD_TICKS}\n{f.read()}\n{MD_TICKS}"
                                console.print(f"[dim]📁 已讀取：{file_path}[/dim]")
                        except Exception as e:
                            console.print(f"[red]失敗: {e}[/red]"); continue
                    else:
                        console.print("[yellow]⚠️ 請提供路徑！[/yellow]"); continue
            else:
                payload = user_input

            user_message = {'role': 'user', 'content': payload}
            if image_paths: user_message['images'] = image_paths
            history.append(user_message)

            with console.status(f"[bold green]5080 運算中...[/bold green]"):
                resp = client.chat(model=MODEL_NAME, messages=history)
                reply = resp['message']['content']
                last_ai_response = reply
                history.append({'role': 'assistant', 'content': reply})
            console.print(Panel(Markdown(reply), title=f"🤖 {MODEL_NAME}", border_style="green"))

        except KeyboardInterrupt: break
        except Exception as e: console.print(f"[bold red]❌ 錯誤: {e}[/bold red]")

if __name__ == "__main__": main()
