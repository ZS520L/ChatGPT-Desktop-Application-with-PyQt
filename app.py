import sys
from PyQt5.QtWidgets import QTextBrowser, QLabel, QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLineEdit, \
    QComboBox, QDesktopWidget, QListWidget, QInputDialog, QHBoxLayout
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPalette, QColor, QTextCursor
import requests
import json
import os
from PIL import Image
from io import BytesIO


def download_image(url):
    response = requests.get(url[4:-1])
    img = Image.open(BytesIO(response.content))
    img.save('tmp.png')
    return f'\n\n![s](./tmp.png)\n\n'


class RequestThread(QThread):
    signal = pyqtSignal(str)

    def __init__(self, model, question):
        QThread.__init__(self)
        self.model = model
        self.question = question

    def run(self):
        headers = {
            "Content-Type": "application/json"
        }
        data = {'model': self.model.split('(')[0], 'messages': self.question, 'stream': True}

        # Read URL from txt file
        with open('url.txt', 'r') as f:
            url = f.read().strip()

        response = requests.post(url, headers=headers, data=json.dumps(data), stream=True)

        for chunk in response.iter_lines():
            if chunk:
                decoded_chunk = chunk.decode('utf-8')
                if decoded_chunk.startswith('data:'):
                    try:
                        parsed_chunk = json.loads(decoded_chunk[5:])
                        current_sentence = parsed_chunk['choices'][0]['delta']['content']
                        if '![](' in current_sentence:
                            current_sentence = download_image(current_sentence)
                        self.signal.emit(current_sentence)
                    except:
                        pass
        self.signal.emit('end!!!')


class MyTextEdit(QTextEdit):
    ctrl_enter_pressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and QApplication.keyboardModifiers() == Qt.ControlModifier:
            self.ctrl_enter_pressed.emit()
        else:
            super().keyPressEvent(event)


class MyApp(QWidget):
    def __init__(self, app):
        super().__init__()

        self.app = app
        self.initUI()

        self.messages = []
        # Load the conversation history
        self.load_conversation_history()

        screen_rect = QDesktopWidget().screenGeometry()  # 获取屏幕大小
        half_width = int(screen_rect.width() / 4)  # 屏幕宽度的一半
        half_height = int(screen_rect.height() / 4)  # 屏幕高度的一半
        self.setGeometry(half_width, half_height, 2 * half_width, 2 * half_height)  # 设置窗口大小和位置

    def initUI(self):

        self.qle = MyTextEdit(self)
        # self.qle.returnPressed.connect(self.query)
        self.qle.ctrl_enter_pressed.connect(self.query)
        self.qle.setFixedHeight(100)  # 设置初始高度为100像素
        self.qle.setPlaceholderText("Enter your question here...\nctrl+enter send message")

        self.btn = QPushButton('Ask', self)
        self.btn.clicked.connect(self.query)

        self.te = QTextBrowser(self)
        # self.te.setEnabled(False)

        self.cb = QComboBox(self)
        self.cb.addItem('gpt-3.5-turbo(免费)')
        self.cb.addItem('gpt-3.5-turbo-16k(免费)')
        self.cb.addItem('net-gpt-3.5-turbo-16k(扣一次)')
        self.cb.addItem('gpt-4(扣一次)')
        self.cb.addItem('gpt-4-0314(扣一次)')
        self.cb.addItem('gpt-4-0613(扣一次)')
        self.cb.addItem('net-gpt-4(扣一次)')
        self.cb.addItem('gpt-32k(扣三次)')
        self.cb.addItem('bing(扣一次)')
        self.cb.addItem('spark(扣一次)')
        self.cb.addItem('ChatGLM-Pro(扣一次)')
        self.cb.addItem('ERNIE-Bot(扣一次)')
        self.cb.addItem('chat-pdf(扣一次)')
        self.cb.addItem('midjourney(扣一次)')
        self.cb.addItem('stable-diffusion(扣一次)')

        self.cb.addItem('chatMi(免费)')
        self.cb.addItem('feifei(免费)')
        self.cb.addItem('tts(免费)')
        self.cb.addItem('派蒙(免费)')
        self.cb.addItem('claude-instance(免费)')
        self.cb.addItem('claude-100k(免费)')
        self.cb.addItem('claude-2-100k(免费)')
        self.cb.addItem('google-plam(免费)')
        self.cb.addItem('llama-2-7b(免费)')
        self.cb.addItem('llama-2-13b(免费)')
        self.cb.addItem('llama-2-70b(免费)')

        # Add more models if needed

        self.historyList = QListWidget(self)
        self.historyList.itemClicked.connect(self.load_history)

        # 设置 QListWidget 的样式
        self.historyList.setStyleSheet("""
            QListWidget {
                font-size: 16px;
                color: white;
                background-color: #353535;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #48576b;
            }
        """)

        # Add a button for creating a new conversation
        self.newBtn = QPushButton('New Conversation', self)
        self.newBtn.clicked.connect(self.new_conversation)

        # 创建一个垂直布局，包含历史记录和新建对话按钮
        vbox_left = QVBoxLayout()
        self.changeUrlBtn = QPushButton('切换通道', self)
        self.changeUrlBtn.clicked.connect(self.change_url)

        # Add the change URL button to the layout
        vbox_left.addWidget(self.changeUrlBtn)
        self.remainingCountsLabel = QLabel('Remaining counts: 99', self)
        self.update_remaining_counts()
        self.remainingCountsLabel.setStyleSheet('font-size:20px;color:green;')
        self.remainingCountsLabel.setAlignment(Qt.AlignCenter)
        vbox_left.addWidget(self.remainingCountsLabel)
        vbox_left.addWidget(self.historyList)
        vbox_left.addWidget(self.newBtn)

        # 创建一个垂直布局，包含其余部分
        vbox_right = QVBoxLayout()
        vbox_right.addWidget(self.cb)
        vbox_right.addWidget(self.te)
        vbox_right.addWidget(self.qle)
        vbox_right.addWidget(self.btn)

        # 创建一个水平布局，将历史记录放在左边，其余部分放在右边
        hbox = QHBoxLayout()
        hbox.addLayout(vbox_left, 1)
        hbox.addLayout(vbox_right, 4)

        self.setLayout(hbox)

        # Set dark theme
        self.set_dark_theme()

        self.setWindowTitle('小海Chat')
        self.setGeometry(300, 300, 300, 200)
        self.show()

    def setMarkdown(self, text):
        self.te.setMarkdown(text)

    def update_remaining_counts(self):
        # Read URL from txt file
        with open('url.txt', 'r') as f:
            url = f.read().strip()

        # Send a GET request to the URL
        response = requests.get(url.replace('php', 'txt'))
        if 'Not' in str(response.text):
            self.remainingCountsLabel.setText('Remaining counts: ' + str(8888))
        else:
            # Update the remaining counts label with the response
            self.remainingCountsLabel.setText('Remaining counts: ' + str(response.text))

    def change_url(self):
        # Prompt the user for a new URL
        url, ok = QInputDialog.getText(self, 'Enter new URL:', '请填入您购买的付费密钥，购买网址：shop.zhtec.xyz')
        if ok:
            # Write the new URL to the txt file
            with open('url.txt', 'w') as f:
                f.write(url)

    def load_conversation_history(self):
        # Check if the conversations directory exists
        if not os.path.exists('conversations'):
            os.makedirs('conversations')
        # Get a list of all conversation files
        files = os.listdir('conversations')
        # Add each conversation to the history list
        for file in files:
            if file.endswith('.txt'):
                self.historyList.addItem(file[:-4])  # Remove the .txt extension

    def query(self):
        model = self.cb.currentText()
        question = self.qle.toPlainText()
        # self.te.setEnabled(False)
        if question.strip() != "":
            # if self.messages:
            #     self.te.append("#---------------------------------------#")
            # self.te.append("Q: " + question + '\n\nA: ')

            self.messages.append({'role': 'user', 'content': question})
            self.thread = RequestThread(model, self.messages)
            self.thread.signal.connect(self.update_text)
            self.thread.start()
        self.qle.clear()


    def update_text(self, text):
        if text == 'end!!!':
            # self.te.setEnabled(True)
            self.update_remaining_counts()
        else:
            if self.messages[-1]['role'] == 'user':
                self.messages.append({'role': 'assistant', 'content': text})
            else:
                self.messages[-1]['content'] += text

            # Build a new Markdown string
            markdown = ""
            for message in self.messages:
                if message['role'] == 'user':
                    markdown += "Q: " + message['content'] + "\n\n\n\n"
                else:
                    markdown += "A: " + message['content'] + "\n\n"
                    markdown += "#---------------------------------------#\n\n"

            # Set the markdown
            self.setMarkdown(markdown)
            # Move the scrollbar to the bottom
            cursor = self.te.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.te.setTextCursor(cursor)

    def new_conversation(self):
        # Prompt the user for a conversation name
        name, ok = QInputDialog.getText(self, 'New Conversation', 'Enter conversation name:')
        if ok:
            # Save the current conversation to a txt file with the given name
            with open('conversations/' + name + '.txt', 'w') as f:
                conversation_str = '\n'.join(json.dumps(message) for message in self.messages)
                f.write(conversation_str)
            # Add the conversation name to the history list
            self.historyList.addItem(name)
            # Clear the conversation window
            self.te.clear()
            self.messages = []

    def load_history(self, item):
        self.te.clear()
        # Load a conversation from a txt file and display it in the conversation window
        with open('conversations/' + item.text() + '.txt', 'r') as f:
            self.messages = [json.loads(line) for line in f]
            # self.te.setText('\n'.join(message['content'] for message in self.messages))
            # Build a new Markdown string
            markdown = ""
            for message in self.messages:
                if message['role'] == 'user':
                    markdown += "Q: " + message['content'] + "\n\n\n\n"
                else:
                    markdown += "A: " + message['content'] + "\n\n"
                    markdown += "#---------------------------------------#\n\n"

            # Set the markdown
            self.setMarkdown(markdown)


    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))

        self.app.setPalette(dark_palette)

        self.app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a82da; 
            border: 1px solid white; 
        }
        QPushButton {
            color: white;
            background-color: #353535;
            font-size: 20px;
        }
        QPushButton:hover {
            background-color: #48576b;
        }
        QPushButton:pressed {
            background-color: #1d1d1d;
        }
        QTextEdit {
            color: white;
            background-color: #353535;
            font-size: 20px;
        }
        QLineEdit {
            color: white;
            background-color: #353535;
            font-size: 20px;
        }
        QComboBox {
            color: white;
            background-color: #353535;
            font-size: 20px;
        }
        """)


if __name__ == '__main__':
    # Check if url.txt exists, if not, create it and write the default url
    if not os.path.exists('url.txt'):
        with open('url.txt', 'w') as f:
            f.write('https://api.zhtec.xyz/xht/chatWith16k.php')
    app = QApplication(sys.argv)
    ex = MyApp(app)
    sys.exit(app.exec_())
