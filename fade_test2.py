import time
import win32gui
import win32con

def find_listview():
    progman = win32gui.FindWindow("Progman", None)
    if progman:
        defview = win32gui.FindWindowEx(progman, None, "SHELLDLL_DefView", None)
        if defview:
            return win32gui.FindWindowEx(defview, None, "SysListView32", None)

    found = {"hwnd": 0}
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
                    found["hwnd"] = listview
                    return False
        return True

    win32gui.EnumWindows(_enum_cb, None)
    return found["hwnd"]

hwnd = find_listview()
print(f"ListView HWND: {hwnd}")

if hwnd:
    original = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    
    # Apply layered style ONCE
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, original | win32con.WS_EX_LAYERED)
    
    print("Fading out...")
    for alpha in range(255, -1, -15):
        win32gui.SetLayeredWindowAttributes(hwnd, 0, max(0, alpha), win32con.LWA_ALPHA)
        time.sleep(0.02)
        
    print("Holding at 0 for 2 seconds...")
    time.sleep(2)
    
    print("Fading in...")
    for alpha in range(0, 256, 15):
        win32gui.SetLayeredWindowAttributes(hwnd, 0, min(255, alpha), win32con.LWA_ALPHA)
        time.sleep(0.02)
        
    # Restore ONCE
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, original)
    print("Done")
