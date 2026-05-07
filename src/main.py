import sys
import os
import subprocess
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                             QFileDialog, QProgressBar, QListWidget, 
                             QListWidgetItem, QMessageBox, QGroupBox, 
                             QRadioButton, QSpinBox, QComboBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QDragEnterEvent, QDropEvent

ARCHIVE_EXTENSIONS = {'.7z', '.zip', '.rar', '.tar', '.gz', '.bz2', '.xz', 
                      '.cab', '.iso', '.arj', '.lzh', '.ace', '.gz', '.tgz', '.bz', '.tbz', '.txz'}

def is_archive_file(filepath):
    _, ext = os.path.splitext(filepath.lower())
    return ext in ARCHIVE_EXTENSIONS


class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, command, parent=None):
        super().__init__(parent)
        self.command = command

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.finished.emit(True, stdout)
            else:
                self.finished.emit(False, stderr)
        except Exception as e:
            self.finished.emit(False, str(e))


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    resources_path = os.path.join(base_path, relative_path)
    if os.path.exists(resources_path):
        return resources_path
    
    resources_path = os.path.join(base_path, "Resources", relative_path)
    if os.path.exists(resources_path):
        return resources_path
    
    return os.path.join(base_path, relative_path)

def find_7z_path():
    bundled_path = get_resource_path("resources/7z")
    
    if os.path.exists(bundled_path) and os.access(bundled_path, os.X_OK):
        os.chmod(bundled_path, 0o755)
        return bundled_path
    
    possible_paths = [
        os.path.join(os.path.dirname(sys.executable), "resources", "7z"),
        os.path.join(os.path.dirname(sys.executable), "..", "Frameworks", "resources", "7z"),
        os.path.expanduser("~/homebrew/bin/7z"),
        "/opt/homebrew/bin/7z",
        "/usr/local/bin/7z",
        "/usr/bin/7z",
        "/bin/7z",
    ]
    
    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    
    try:
        result = subprocess.run(["7z", "--help"], capture_output=True)
        if result.returncode == 0:
            return "7z"
    except FileNotFoundError:
        pass
    
    return None

class SevenZipGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.seven_zip_path = find_7z_path()
        if not self.seven_zip_path:
            QMessageBox.critical(None, "错误", "未找到 7z 命令！\n\n请先安装 p7zip：\n\n使用 Homebrew 安装：\nbrew install p7zip\n\n或从官网下载：\nhttps://www.7-zip.org/")
            sys.exit(1)
        self.initUI()
        self.files_to_process = []

    def initUI(self):
        self.setWindowTitle("7Z GUI")
        self.setGeometry(100, 100, 600, 500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.create_mode_group(main_layout)
        self.create_file_list(main_layout)
        self.create_options_group(main_layout)
        self.create_output_group(main_layout)
        self.create_progress_bar(main_layout)
        self.create_buttons(main_layout)

        self.setAcceptDrops(True)

    def create_mode_group(self, parent_layout):
        group_box = QGroupBox("操作模式")
        layout = QHBoxLayout(group_box)
        
        self.auto_radio = QRadioButton("自动识别")
        self.zip_radio = QRadioButton("压缩")
        self.unzip_radio = QRadioButton("解压")
        self.auto_radio.setChecked(True)
        
        layout.addWidget(self.auto_radio)
        layout.addWidget(self.zip_radio)
        layout.addWidget(self.unzip_radio)
        parent_layout.addWidget(group_box)

    def create_file_list(self, parent_layout):
        group_box = QGroupBox("待处理文件")
        layout = QVBoxLayout(group_box)
        
        self.file_list = QListWidget()
        self.file_list.setAcceptDrops(True)
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        
        add_btn = QPushButton("添加文件")
        add_folder_btn = QPushButton("添加文件夹")
        remove_btn = QPushButton("移除选中")
        clear_btn = QPushButton("清空列表")
        
        add_btn.clicked.connect(self.add_files)
        add_folder_btn.clicked.connect(self.add_folder)
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn.clicked.connect(self.clear_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(add_folder_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.file_list)
        parent_layout.addWidget(group_box)

    def create_options_group(self, parent_layout):
        group_box = QGroupBox("压缩选项")
        layout = QHBoxLayout(group_box)
        
        layout.addWidget(QLabel("压缩级别:"))
        self.compression_level = QSpinBox()
        self.compression_level.setRange(0, 9)
        self.compression_level.setValue(5)
        layout.addWidget(self.compression_level)
        
        layout.addWidget(QLabel("格式:"))
        self.archive_format = QComboBox()
        self.archive_format.addItems(["7z", "zip", "tar", "gzip"])
        layout.addWidget(self.archive_format)
        
        layout.addWidget(QLabel("加密:"))
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("输入密码（可选）")
        self.password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_edit)
        
        parent_layout.addWidget(group_box)

    def create_output_group(self, parent_layout):
        group_box = QGroupBox("输出设置")
        layout = QHBoxLayout(group_box)
        
        layout.addWidget(QLabel("输出路径:"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("选择输出目录")
        layout.addWidget(self.output_path)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_output)
        layout.addWidget(browse_btn)
        
        parent_layout.addWidget(group_box)

    def create_progress_bar(self, parent_layout):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        parent_layout.addWidget(self.progress_bar)

    def create_buttons(self, parent_layout):
        layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始")
        self.cancel_btn = QPushButton("取消")
        
        self.start_btn.clicked.connect(self.start_process)
        self.cancel_btn.clicked.connect(self.cancel_process)
        self.cancel_btn.setEnabled(False)
        
        layout.addStretch()
        layout.addWidget(self.start_btn)
        layout.addWidget(self.cancel_btn)
        parent_layout.addLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.exists(path):
                self.add_to_list(path)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择文件", "", "所有文件 (*.*)"
        )
        for file in files:
            self.add_to_list(file)

    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择文件夹", ""
        )
        if folder:
            self.add_to_list(folder)

    def add_to_list(self, path):
        if path not in self.files_to_process:
            self.files_to_process.append(path)
            item = QListWidgetItem(path)
            self.file_list.addItem(item)
        
        if self.auto_radio.isChecked():
            self.auto_detect_mode()
        
        self.auto_set_output_path()

    def auto_detect_mode(self):
        if not self.files_to_process:
            return
        
        all_archives = True
        has_non_archive = False
        
        for path in self.files_to_process:
            if os.path.isfile(path):
                if is_archive_file(path):
                    continue
                else:
                    has_non_archive = True
                    all_archives = False
            elif os.path.isdir(path):
                has_non_archive = True
                all_archives = False
        
        if all_archives:
            self.unzip_radio.setChecked(True)
        elif has_non_archive:
            self.zip_radio.setChecked(True)
    
    def all_files_are_archives(self):
        for path in self.files_to_process:
            if os.path.isfile(path):
                if not is_archive_file(path):
                    return False
            elif os.path.isdir(path):
                return False
        return len(self.files_to_process) > 0
    
    def get_current_mode(self):
        if self.unzip_radio.isChecked():
            return "extract"
        elif self.zip_radio.isChecked():
            return "compress"
        else:
            return "auto"
    
    def auto_set_output_path(self):
        if not self.files_to_process:
            return
        
        first_path = self.files_to_process[0]
        parent_dir = os.path.dirname(first_path)
        
        if not parent_dir:
            parent_dir = os.path.expanduser("~/Desktop")
        
        mode = self.get_current_mode()
        
        if mode == "extract" or (mode == "auto" and is_archive_file(first_path)):
            base_name = os.path.splitext(os.path.basename(first_path))[0]
            output_dir = os.path.join(parent_dir, base_name)
            self.output_path.setText(output_dir)
        else:
            self.output_path.setText(parent_dir)

    def remove_selected(self):
        for item in self.file_list.selectedItems():
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            del self.files_to_process[row]
        
        if self.auto_radio.isChecked():
            self.auto_detect_mode()

    def clear_list(self):
        self.file_list.clear()
        self.files_to_process.clear()
        self.auto_radio.setChecked(True)

    def browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", "")
        if path:
            self.output_path.setText(path)

    def start_process(self):
        if not self.files_to_process:
            QMessageBox.warning(self, "警告", "请添加要处理的文件")
            return
        
        output_dir = self.output_path.text()
        if not output_dir:
            output_dir = os.path.expanduser("~/Desktop")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        if self.zip_radio.isChecked() or (self.auto_radio.isChecked() and not self.all_files_are_archives()):
            self.create_archive(output_dir)
        else:
            self.extract_archive(output_dir)

    def create_archive(self, output_dir):
        level = self.compression_level.value()
        fmt = self.archive_format.currentText()
        password = self.password_edit.text()
        
        base_name = os.path.basename(self.files_to_process[0])
        if os.path.isdir(self.files_to_process[0]):
            archive_name = f"{base_name}.{fmt}"
        else:
            archive_name = f"{os.path.splitext(base_name)[0]}.{fmt}"
        
        archive_path = os.path.join(output_dir, archive_name)
        
        cmd = [self.seven_zip_path, "a", f"-mx={level}", archive_path]
        
        if password:
            cmd.append(f"-p{password}")
        
        cmd.extend(self.files_to_process)
        
        self.worker = WorkerThread(cmd)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()

    def extract_archive(self, output_dir):
        if len(self.files_to_process) != 1:
            QMessageBox.warning(self, "警告", "解压只能选择一个压缩文件")
            self.reset_ui()
            return
        
        archive_path = self.files_to_process[0]
        password = self.password_edit.text()
        
        cmd = [self.seven_zip_path, "x", archive_path, f"-o{output_dir}", "-y"]
        
        if password:
            cmd.append(f"-p{password}")
        
        self.worker = WorkerThread(cmd)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()

    def cancel_process(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
        self.reset_ui()

    def on_process_finished(self, success, message):
        if success:
            QMessageBox.information(self, "成功", "操作完成")
        else:
            QMessageBox.critical(self, "错误", message)
        self.reset_ui()

    def reset_ui(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SevenZipGUI()
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if os.path.exists(arg):
                window.add_to_list(arg)
    
    window.show()
    sys.exit(app.exec_())