import os
import sys
import traceback

app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(app_dir, "app_startup_log.txt")

def log_debug(msg):
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
    except Exception:
        pass

log_debug("=== Starting TKStug Whiteboard Studio ===")

# Set Qt plugin path
if getattr(sys, 'frozen', False):
    internal_dir = os.path.join(app_dir, "_internal")
    plugins_dir = os.path.join(internal_dir, "PyQt6", "Qt6", "plugins")
    if os.path.exists(plugins_dir):
        os.environ["QT_PLUGIN_PATH"] = plugins_dir
        log_debug(f"Set QT_PLUGIN_PATH: {plugins_dir}")

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def exception_hook(exctype, value, tb):
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    log_debug(f"CRITICAL ERROR:\n{err_msg}")
    try:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Lỗi Khởi Động", f"Đã xảy ra lỗi:\n\n{err_msg[:400]}")
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_hook

try:
    log_debug("Importing PyQt6...")
    from PyQt6.QtWidgets import QApplication, QMessageBox
    log_debug("Importing MainWindow...")
    from gui.main_window import MainWindow

    def main():
        log_debug("Creating QApplication...")
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        log_debug("Creating MainWindow...")
        window = MainWindow()
        window.show()
        log_debug("Entering app.exec()...")
        sys.exit(app.exec())

    if __name__ == "__main__":
        main()
except Exception as e:
    log_debug(f"Top-level exception:\n{traceback.format_exc()}")