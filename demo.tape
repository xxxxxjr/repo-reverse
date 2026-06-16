Output /tmp/repo-reverse-demo.gif
Set Theme "Dracula"
Set Width 900
Set Height 600
Set Padding 10
Set FontSize 14

Hide
Type "cd /home/xie/项目文件夹/repo-reverse && clear"
Enter
Sleep 500ms
Show

Sleep 500ms
Type "# Repo Reverse - turn any repo into design docs"
Enter
Sleep 500ms
Type "# No API key needed - static analysis runs anyway"
Enter
Sleep 1s
Type "python cli.py /home/xie/项目文件夹/repo-reverse --no-ai -o /tmp/demo-report.html"
Enter
Sleep 7s

Type "# Done. Open the HTML to see architecture, modules, deployment flow..."
Enter
Sleep 500ms
Type "xdg-open /tmp/demo-report.html"
Enter
Sleep 2s
