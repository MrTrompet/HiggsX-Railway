# admin_panel_widget.py
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QMessageBox
from telegram_handler import send_telegram_message

class AdminPanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Escribe el mensaje para enviar a Telegram...")
        self.layout.addWidget(self.text_edit)
        
        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)
        
        self.setLayout(self.layout)
    
    def send_message(self):
        message = self.text_edit.toPlainText().strip()
        if message:
            try:
                send_telegram_message(message)
                QMessageBox.information(self, "Mensaje Enviado", "El mensaje se ha enviado correctamente.")
                self.text_edit.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error al enviar el mensaje: {str(e)}")
        else:
            QMessageBox.warning(self, "Mensaje Vacío", "Por favor, escribe un mensaje antes de enviar.")

# Si deseas probarlo de forma independiente:
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = AdminPanelWidget()
    window.show()
    sys.exit(app.exec_())
