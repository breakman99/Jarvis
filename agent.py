"""
Jarvis 顶层入口。

通过 `python agent.py` 启动时，将执行转发至 src.main.main()，
由后者完成 CLI REPL 的初始化与交互循环。
"""
from src.main import main


if __name__ == "__main__":
    main()
