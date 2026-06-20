Set ws = CreateObject("WScript.Shell")

Set s1 = ws.CreateShortcut("D:\Documents\Desktop\yaoshidiyi.lnk")
s1.TargetPath = "D:\Documents\Desktop\yaoshidiyi.bat"
s1.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants"
s1.IconLocation = "C:\Users\Administrator\Documents\trae_projects\first cc\four-quadrants\icon.ico, 0"
s1.Save()

Set s2 = ws.CreateShortcut("D:\Documents\Desktop\fanqiezhong.lnk")
s2.TargetPath = "D:\Documents\Desktop\fanqiezhong.bat"
s2.WorkingDirectory = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer"
s2.IconLocation = "C:\Users\Administrator\Documents\trae_projects\first cc\pomodoro-timer\icon.ico, 0"
s2.Save()
