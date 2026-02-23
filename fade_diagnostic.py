import time
import win32gui
import win32con
import sys

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
if not hwnd:
    print("Could not find desktop icons.")
    sys.exit()

original = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

print("Starting in 3 seconds...")
time.sleep(3)

print("\n--- STAGE 1: APPLYING LAYERED FLAG ---")
# Apply layered style, but keep alpha at 255
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, original | win32con.WS_EX_LAYERED)
win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
print("Flag applied. Waiting 3 seconds. DID IT FLICKER JUST NOW?")
time.sleep(3)

print("\n--- STAGE 2: FADING OUT ---")
for alpha in range(255, -1, -5):
    win32gui.SetLayeredWindowAttributes(hwnd, 0, max(0, alpha), win32con.LWA_ALPHA)
    time.sleep(0.01)
print("Faded out. Waiting 3 seconds. DID IT FLICKER DURING FADE?")
time.sleep(3)

print("\n--- STAGE 3: FADING IN ---")
for alpha in range(0, 256, 5):
    win32gui.SetLayeredWindowAttributes(hwnd, 0, min(255, alpha), win32con.LWA_ALPHA)
    time.sleep(0.01)
print("Faded in. Waiting 3 seconds. DID IT FLICKER DURING FADE?")
time.sleep(3)

print("\n--- STAGE 4: REMOVING LAYERED FLAG ---")
win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, original)
print("Flag removed. DID IT FLICKER JUST NOW?")
time.sleep(2)
print("Test complete.")
