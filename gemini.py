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
OLLAMA_HOST = 'http://100.75.147.53:11434' 
MODEL_NAME = 'gemma4'
MD_TICKS = chr(96) * 3

try:
    client = ollama.Client(host=OLLAMA_HOST)
except Exception as e:
    console.print(f"[bold red]❌ 無法連線至伺服器: {e}[/bold red]")

# --- ✨ Tab 檔案補全 ---
def path_completer(text, state):
    matches = glob.glob(os.path.expanduser(text) + '*')
    return (matches + [None])[state]

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(path_completer)

# --- 🧠 處理邏輯 ---
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

# --- 🚀 主程式迴圈 ---
def main():
    prompt_prefix, mode_text, system_instruction = get_project_info()
    history = []
    if system_instruction:
        history.append({'role': 'system', 'content': system_instruction})

    # --- 🎨 重新設計的綠色框框 (指令全顯示) ---
    console.clear()
    help_menu = (
        f"[bold green]🔋 5080 智慧 Agent 完全體[/bold green] [dim]v2.5[/dim]\n"
        f"{mode_text} | 模型：[white]{MODEL_NAME}[/white]\n"
        f"──────────────────────────────────────────\n"
        f"[cyan]🚀 Git 同步 [/cyan] ⮕ [white]@push \"訊息\"[/white] (自動 Commit/Push)\n"
        f"[magenta]🧬 自我進化 [/magenta] ⮕ [white]@apply[/white] (將 AI 代碼寫入檔案)\n"
        f"[red]⚡ 指令執行 [/red] ⮕ [white]@run <cmd>[/white] (支援自動偵測執行)\n"
        f"[yellow]📖 檔案讀取 [/yellow] ⮕ [white]@read <路徑>[/white] (輸入 [italic]self[/italic] 讀取源碼)\n"
        f"[blue]👁️ 視覺分析 [/blue] ⮕ [white]@image <路徑> <問題>[/white]\n"
        f"──────────────────────────────────────────\n"
        f"[dim]輸入 'exit' 離開，'clear' 清除畫面[/dim]"
    )
    console.print(Panel.fit(help_menu, border_style="green"))

    last_ai_response = ""

    while True:
        try:
            prompt_prefix, _, _ = get_project_info()
            user_input = input(f"\n❯ {prompt_prefix} 您：")
            if user_input.lower() in ['exit', 'quit']: break
            if not user_input.strip(): continue

            # --- A. 智慧 GitHub 同步 (@push) ---
            if user_input.startswith("@push"):
                msg = user_input.replace("@push", "").strip()
                if not msg:
                    console.print("[yellow]⚠️ 請提供描述！[/yellow]")
                    continue
                
                git_cmds = [
                    "git add .",
                    f'git commit -m "{msg}"',
                    "git push origin main"
                ]
                if run_git_cmds(git_cmds):
                    console.print("[bold green]✅ 成功推送到 GitHub！[/bold green]")
                continue

            # --- B. 自我進化 (@apply) ---
            elif user_input.startswith("@apply"):
                target = user_input.replace("@apply", "").strip()
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

            # --- C. 智慧執行 (@run) ---
            elif user_input.startswith("@run"):
                cmd_arg = user_input.replace("@run", "").strip()
                if not cmd_arg or any(x in cmd_arg for x in ["上面", "自動", "幫我"]):
                    blocks = extract_blocks(last_ai_response, "bash") or extract_blocks(last_ai_response, "sh")
                    if not blocks:
                        console.print("[yellow]⚠️ 找不到指令。[/yellow]"); continue
                    for c in blocks:
                        if Confirm.ask(f"執行 [cyan]{c}[/cyan]？", default=True): os.system(c)
                else:
                    if Confirm.ask(f"執行 [red]{cmd_arg}[/red]？", default=False): os.system(cmd_arg)
                continue

            # --- D. 檔案讀取 ---
            payload = user_input
            if "@read self" in user_input.lower():
                with open(SELF_PATH, "r", encoding="utf-8") as f:
                    payload = user_input.replace("@read self", "") + f"\n\n我的主程式代碼如下：\n{MD_TICKS}python\n{f.read()}\n{MD_TICKS}"
                console.print(f"[dim]🧬 已讀取源碼...[/dim]")
            elif "@read" in user_input:
                parts = user_input.split("@read")
                file_path = os.path.expanduser(parts[1].strip())
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        payload = f"{parts[0].strip()}\n\n內容：\n{MD_TICKS}\n{f.read()}\n{MD_TICKS}"
                        console.print(f"[dim]📁 已讀取：{file_path}[/dim]")
                except Exception as e: console.print(f"[red]失敗: {e}[/red]"); continue

            # 送出至 5080 伺服器
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
