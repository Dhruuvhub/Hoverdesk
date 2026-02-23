import time
import win32gui
import win32con

def find_listview():
    progman = win32gui.FindWindow("Progman", None)
    if progman:
        defview = win32gui.FindWindowEx(progman, None, "SHELLDLL_DefView", None)
        if defview:
            return defview, win32gui.FindWindowEx(defview, None, "SysListView32", None)

    found = {"listview": 0, "defview": 0}
    def _enum_cb(hwnd, _lparam):
        try:
            class_name = win32gui.GetClassName(hwnd)
        except Exception:
            return True
        if class_name == "WorkerW":
            defview = win32gui.FindWindowEx(hwnd, None, "SHELLDLL_DefView", None)
            if defview:
                listview = win32gui.FindWindowEx(defview, None, "SysListView32", None)
                if listview:
                    found["defview"] = defview
                    found["listview"] = listview
                    return False
        return True

    win32gui.EnumWindows(_enum_cb, None)
    return found["defview"], found["listview"]

defview, listview = find_listview()
print(f"DefView: {defview}, ListView: {listview}")

# Test fading DefView instead of ListView
target = defview
original = win32gui.GetWindowLong(target, win32con.GWL_EXSTYLE)
win32gui.SetWindowLong(target, win32con.GWL_EXSTYLE, original | win32con.WS_EX_LAYERED)

for i in range(255, -1, -15):
    win32gui.SetLayeredWindowAttributes(target, 0, i, win32con.LWA_ALPHA)
    time.sleep(0.05)
    
win32gui.SetWindowLong(target, win32con.GWL_EXSTYLE, original)
