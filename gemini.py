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

def extract_blocks(text, lang="python"):
    pattern = MD_TICKS + rf"(?:{lang})?\n(.*?)\n" + MD_TICKS
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
        f"[bold green]🔋 5080 智慧 Agent 完全體[/bold green] [dim]v2.9[/dim]\n"
        f"{mode_text} | 模型：[white]{MODEL_NAME}[/white]\n"
        f"──────────────────────────────────────────\n"
        f"[cyan]📝 多行貼上 [/cyan] ⮕ [white]/multi[/white] (自動過濾終端機邊界符號)\n"
        f"[green]💾 安全存檔 [/green] ⮕ [white]@save <訊息>[/white] (僅本地 Commit)\n"
        f"[blue]🚀 雲端同步 [/blue] ⮕ [white]@push \[訊息][/white] (發送至 GitHub)\n"
        f"[magenta]🧬 自我進化 [/magenta] ⮕ [white]@apply[/white] (寫入 AI 建議代碼)\n"
        f"[red]⚡ 指令執行 [/red] ⮕ [white]@run <cmd>[/white] | [yellow]📖 讀取 [/yellow] ⮕ [white]@read <路徑>[/white]\n"
        f"──────────────────────────────────────────\n"
        f"[dim]輸入 'exit' 離開，'clear' 清除畫面[/dim]"
    )
    console.print(Panel.fit(help_menu, border_style="green"))

    last_ai_response = ""

    while True:
        try:
            prompt_prefix, _, _ = get_project_info()
            user_input = input(f"\n❯ {prompt_prefix} 您：")
            
            # --- 🚀 多行輸入模式 (加入邊界符號過濾) ---
            if user_input.strip() == "/multi":
                console.print("[dim]📝 已進入多行模式！請直接貼上內容。\n(貼完後，請在新的一行輸入 [white]/end[/white] 送出，或 [white]/cancel[/white] 取消)[/dim]")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "/end": break
                    if line.strip() == "/cancel":
                        lines = None
                        break
                    
                    # 自動移除 iPad SSH 常見的右側邊界符號 '|' 以及多餘的空白
                    cleaned_line = line.rstrip()
                    if cleaned_line.endswith('|'):
                        cleaned_line = cleaned_line[:-1].rstrip()
                    lines.append(cleaned_line)
                
                if lines is None: 
                    console.print("[yellow]已取消多行輸入。[/yellow]")
                    continue
                
                user_input = "\n".join(lines)
                console.print(f"[dim]✅ 已成功接收 {len(lines)} 行內容。[/dim]")

            if user_input.lower() in ['exit', 'quit']: break
            if not user_input.strip(): continue

            # --- 指令解析 (改為嚴格比對開頭，避免誤判貼上的內容) ---
            if user_input.startswith("@save"):
                msg = user_input.replace("@save", "", 1).strip().strip("\"'")
                if not msg:
                    console.print("[yellow]⚠️ 請提供存檔描述！[/yellow]"); continue
                git_cmds = ["git add .", f'git commit -m "{msg}"']
                if run_git_cmds(git_cmds):
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
                lang = "yaml" if target.endswith(".yml") else "python"
                blocks = extract_blocks(last_ai_response, lang)
                if blocks:
                    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
                    with open(target, "w", encoding="utf-8") as f: f.write(blocks[0].strip())
                    console.print(f"[bold green]✅ 已寫入：{target}[/bold green]")
                else:
                    console.print("[yellow]⚠️ 找不到代碼區塊。[/yellow]")
                continue

            elif user_input.startswith("@run"):
                cmd_arg = user_input.replace("@run", "", 1).strip()
                if not cmd_arg or any(x in cmd_arg for x in ["上面", "自動"]):
                    blocks = extract_blocks(last_ai_response, "bash") or extract_blocks(last_ai_response, "sh")
                    for c in blocks:
                        if Confirm.ask(f"執行 [cyan]{c}[/cyan]？", default=True): os.system(c)
                else:
                    if Confirm.ask(f"執行 [red]{cmd_arg}[/red]？", default=False): os.system(cmd_arg)
                continue

            elif user_input.startswith("@read"):
                payload = user_input
                if user_input.strip() == "@read self" or user_input.startswith("@read self "):
                    with open(SELF_PATH, "r", encoding="utf-8") as f:
                        payload = user_input.replace("@read self", "", 1) + f"\n\n我的主程式代碼如下：\n{MD_TICKS}python\n{f.read()}\n{MD_TICKS}"
                    console.print(f"[dim]🧬 已讀取源碼...[/dim]")
                else:
                    file_path = os.path.expanduser(user_input.split("@read", 1)[1].strip())
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            payload = f"{user_input.split('@read', 1)[0].strip()}\n\n內容：\n{MD_TICKS}\n{f.read()}\n{MD_TICKS}"
                            console.print(f"[dim]📁 已讀取：{file_path}[/dim]")
                    except Exception as e: 
                        console.print(f"[red]失敗: {e}[/red]")
                        continue
            else:
                payload = user_input

            # --- 傳送至 5080 模型 ---
            history.append({'role': 'user', 'content': payload})
            with console.status(f"[bold green]5080 運算中...[/bold green]"):
                resp = client.chat(model=MODEL_NAME, messages=history)
                reply = resp['message']['content']
                last_ai_response = reply
                history.append({'role': 'assistant', 'content': reply})
            console.print(Panel(Markdown(reply), title=f"🤖 {MODEL_NAME}", border_style="green"))

        except KeyboardInterrupt: break
        except Exception as e: console.print(f"[bold red]❌ 錯誤: {e}[/bold red]")

if __name__ == "__main__": main()
