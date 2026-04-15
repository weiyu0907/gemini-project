import sys
import os
import time
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

# --- 🛠 系統環境強制修正 ---
os.environ["PYTHONIOENCODING"] = "utf-8"
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    pass

if sys.stdin.encoding != 'utf-8':
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 🌐 系統核心與連線配置 ---
SELF_PATH = os.path.abspath(__file__)
console = Console()

# 配置實驗室 5080 伺服器
OLLAMA_HOST = 'http://100.69.30.107:11434'
MODEL_NAME = 'gemma4'

# 防截斷變數：用 ASCII 碼生成反引號，避免 iPad 複製貼上時誤判斷行
MD_TICKS = chr(96) * 3

try:
    client = ollama.Client(host=OLLAMA_HOST)
except Exception as e:
    console.print(f"[bold red]❌ 無法初始化 Ollama 客戶端: {e}[/bold red]")

# --- ✨ Tab 檔案名稱補全邏輯 ---
def path_completer(text, state):
    expanded_text = os.path.expanduser(text)
    matches = glob.glob(expanded_text + '*')
    if state < len(matches):
        return matches[state]
    return None

readline.set_completer_delims(' \t\n;')
readline.parse_and_bind("tab: complete")
readline.set_completer(path_completer)

# --- 🧠 輔助處理函式 ---
def extract_commands(text):
    """從文本中精準擷取所有指令區塊 (徹底解決 iPad 複製截斷問題)"""
    pattern = MD_TICKS + r"(?:bash|sh|console)?\n(.*?)\n" + MD_TICKS
    code_blocks = re.findall(pattern, text, re.DOTALL)
    commands = []
    for block in code_blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip() and not line.startswith('#')]
        commands.extend(lines)
    return commands

def get_project_info():
    current_folder = os.path.basename(os.getcwd())
    if os.path.exists("GEMINI.md"):
        mode_text = f"[bold yellow]📁 專案大腦：{current_folder}[/bold yellow]"
        prompt_prefix = f"[{current_folder}]"
        try:
            with open("GEMINI.md", "r", encoding="utf-8") as f:
                instruction = f.read()
        except:
            instruction = ""
    else:
        mode_text = f"[dim]🌍 5080 本地模式 ({MODEL_NAME})[/dim]"
        prompt_prefix = "[通用]"
        instruction = ""
    return prompt_prefix, mode_text, instruction

# --- 🚀 主程式迴圈 ---
def main():
    prompt_prefix, mode_text, system_instruction = get_project_info()
    history = []
    
    if system_instruction:
        history.append({'role': 'system', 'content': system_instruction})

    console.clear()
    panel_content = (
        f"[bold green]🔋 5080 智慧 Agent 完全體 已上線！[/bold green]\n"
        f"模型：[white]{MODEL_NAME}[/white] | 伺服器：[white]{OLLAMA_HOST}[/white]\n"
        f"{mode_text}\n"
        f"[dim]• [cyan]新增：@image 視覺分析 (若模型支援)[/cyan]\n"
        f"• [white]修復：iPad 複製截斷與 SyntaxError 問題[/white]\n"
        f"• [magenta]智慧：@run 自動擷取指令 / @apply 自我修改[/magenta]\n"
        f"• [yellow]讀取：@read <檔案> 或 @read self[/yellow][/dim]\n"
    )
    console.print(Panel.fit(panel_content, border_style="green"))

    last_ai_response = ""

    while True:
        try:
            prompt_prefix, _, _ = get_project_info()
            prompt_str = f"\n❯ {prompt_prefix} 您："
            user_input = input(prompt_str)
            
            if user_input.lower() in ['exit', 'quit']: break
            if user_input.lower() == 'clear':
                console.clear(); continue
            if not user_input.strip(): continue

            current_payload = user_input
            image_paths = []

            # --- A. 視覺分析 (@image) ---
            if user_input.startswith("@image"):
                parts = user_input.replace("@image", "").strip().split(" ", 1)
                if len(parts) > 0 and parts[0]:
                    img_path = os.path.expanduser(parts[0])
                    if os.path.exists(img_path):
                        image_paths.append(img_path)
                        current_payload = parts[1] if len(parts) > 1 else "請幫我分析這張圖片的內容。"
                        console.print(f"[dim]👁️ 已附加圖片：{img_path}[/dim]")
                    else:
                        console.print(f"[bold red]❌ 找不到圖片：{img_path}[/bold red]")
                        continue
                else:
                    console.print("[yellow]⚠️ 用法：@image <圖片路徑> <問題>[/yellow]")
                    continue

            # --- B. 智慧執行 (@run) ---
            elif user_input.startswith("@run"):
                cmd_arg = user_input.replace("@run", "").strip()
                
                if not cmd_arg or any(x in cmd_arg for x in ["幫我", "自動", "上面", "執行"]):
                    if not last_ai_response:
                        console.print("[yellow]⚠️ 目前沒有歷史指令可執行。[/yellow]")
                        continue
                    
                    cmds = extract_commands(last_ai_response)
                    if not cmds:
                        console.print("[yellow]⚠️ 找不到任何指令區塊。[/yellow]")
                        continue
                    
                    console.print(f"[bold cyan]🔍 偵測到 {len(cmds)} 條指令：[/bold cyan]")
                    for i, c in enumerate(cmds):
                        console.print(f"  {i+1}. [white]{c}[/white]")
                    
                    if Confirm.ask("\n[bold yellow]是否要依序執行以上指令？[/bold yellow]", default=True):
                        for c in cmds:
                            console.print(Panel(f"[bold white]{c}[/bold white]", title="🚀 執行中", border_style="blue"))
                            os.system(c)
                    continue
                else:
                    console.print(Panel(f"[bold white]{cmd_arg}[/bold white]", title="[bold red]⚠️ 安全確認[/bold red]", border_style="red"))
                    if Confirm.ask("[bold yellow]確定執行此指令？[/bold yellow]", default=False):
                        if cmd_arg.startswith("cd "):
                            try:
                                os.chdir(os.path.expanduser(cmd_arg[3:].strip().strip("'\"")))
                                console.print(f"[dim]📂 已切換路徑: {os.getcwd()}[/dim]")
                            except Exception as e: console.print(f"[red]{e}[/red]")
                        else:
                            os.system(cmd_arg)
                    continue

            # --- C. 自動進化 (@apply) ---
            elif user_input.startswith("@apply"):
                target = user_input.replace("@apply", "").strip()
                file_to_write = SELF_PATH if (not target and "我的主程式" in last_ai_response) else os.path.expanduser(target)
                match = re.search(MD_TICKS + r"(?:python)?\n(.*?)\n" + MD_TICKS, last_ai_response, re.DOTALL)
                if match:
                    with open(file_to_write, "w", encoding="utf-8") as f: 
                        f.write(match.group(1).strip())
                    console.print(f"[bold green]✅ 自我進化成功！寫入至 {file_to_write}。請重啟。[/bold green]")
                else:
                    console.print("[yellow]⚠️ 找不到可套用的代碼區塊。[/yellow]")
                continue

            # --- D. 檔案讀取 (@read / @read self) ---
            elif "@read self" in user_input.lower():
                with open(SELF_PATH, "r", encoding="utf-8") as f:
                    current_payload = user_input.replace("@read self", "") + f"\n\n我的主程式代碼如下：\n{MD_TICKS}python\n{f.read()}\n{MD_TICKS}"
                console.print(f"[dim]🧬 已讀取主程式源碼...[/dim]")
                
            elif "@read" in user_input:
                parts = user_input.split("@read")
                file_path = os.path.expanduser(parts[1].strip())
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        current_payload = f"{parts[0].strip()}\n\n內容：\n{MD_TICKS}\n{f.read()}\n{MD_TICKS}"
                        console.print(f"[dim]📁 已讀取檔案：{file_path}[/dim]")
                except Exception as e: 
                    console.print(f"[red]讀取失敗: {e}[/red]")
                    continue

            # --- 🚀 送出至 5080 伺服器 ---
            user_message = {'role': 'user', 'content': current_payload}
            if image_paths:
                user_message['images'] = image_paths
            
            history.append(user_message)
            
            with console.status(f"[bold green]5080 ({MODEL_NAME}) 運算中...[/bold green]", spinner="dots"):
                response = client.chat(model=MODEL_NAME, messages=history)
                reply = response['message']['content']
                last_ai_response = reply
                history.append({'role': 'assistant', 'content': reply})
            
            console.print(Panel(Markdown(reply), title=f"🤖 {MODEL_NAME}", border_style="green"))

        except KeyboardInterrupt: 
            break
        except Exception as e:
            console.print(f"[bold red]❌ 伺服器錯誤: {e}[/bold red]")

if __name__ == "__main__":
    main()
