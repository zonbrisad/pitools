

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QDialogButtonBox
)

class InfoDialog(QDialog):
    def __init__(self, text: str, title: str="", x: int=400, y: int=300, parent=None):
        super(InfoDialog, self).__init__(parent)

        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(x,y)
        self.setContentsMargins(1,1,1,1)
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setSpacing(5)
        self.setLayout(self.verticalLayout)

        # TextEdit
        self.textEdit = QTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.verticalLayout.addWidget(self.textEdit)
        self.textEdit.insertHtml(text)

        # Buttonbox
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.setCenterButtons(True)
        self.verticalLayout.addWidget(self.buttonBox)

    @staticmethod
    def show(text:str, title: str="", x=400, y=300, parent=None):
        
        dialog = InfoDialog(text, title=title,x=x, y=y, parent=parent)
        result = dialog.exec_()
        return result == QDialog.Accepted
    
    
    
    if __name__ == "__main__":
        import sys
        app = QApplication(sys.argv)
        #InfoDialog.show("<h1>This is a test</h1><p>Hello World!</p>", title="Info Dialog Test", x=500, y=400)
    
        dialog = InfoDialog("<h1>This is a test</h1><p>Hello World!</p>", title="Info Dialog Test", x=500, y=400)
        dialog.exec_()