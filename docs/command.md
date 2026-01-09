CDP 浏览器启动：
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_debug_profile"



# 正常模式，指定概念
python main.py --concept 智能体

# 或者使用短参数
python main.py -concept 大模型领域的幻觉

# 封面测试模式（不需要 concept）
python main.py --cover

# 封面测试模式，指定主题名称
python main.py --cover 主题名

# Session 文件模式（不需要 concept）
python main.py session_file.txt