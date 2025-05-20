import sys
import os
import json
import urllib3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QMessageBox,
    QWidget, QVBoxLayout, QPlainTextEdit, QLabel, QPushButton, QTabWidget,
    QLineEdit, QCheckBox, QRadioButton, QButtonGroup, QFormLayout, QDialog,
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QGroupBox, QScrollArea, QComboBox,
    QMenu, QInputDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from core.importer import Importer
from core.executor import Executor
from core.environment import EnvironmentManager

# Desabilita avisos de SSL inseguros
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Ferramenta de Requisições HTTP')
        self.setGeometry(100, 100, 1200, 800)
        self.collections = []
        self.environments = EnvironmentManager()
        self.current_request_data = None
        self.request_mapping = {}  # Mapear IDs únicos para itens de requisição

        self._create_actions()
        self._create_menu_bar()
        self._setup_ui()

        # Carregar coleções e ambientes salvos
        self.load_collections()
        self.load_environments()
        self.update_environment_combo()
        self.update_edit_environments_menu()
        self.update_collections_view()

    def _create_actions(self):
        self.generate_pdf_action = QAction('Gerar Evidência em PDF', self)
        self.generate_pdf_action.triggered.connect(self.generate_evidence_pdf)
        self.new_collection_action = QAction('Nova Coleção', self)
        self.new_collection_action.triggered.connect(self.create_collection)
        self.new_collection_action.setToolTip('Criar uma nova coleção vazia')
    
        self.import_curl_action = QAction('Importar cURL', self)
        self.import_curl_action.triggered.connect(self.import_curl)
        self.import_curl_action.setToolTip('Importar requisição a partir de um comando cURL')

        self.import_collection_action = QAction('Importar Coleção', self)
        self.import_collection_action.triggered.connect(self.import_collection)
        self.import_collection_action.setToolTip('Importar uma coleção do Postman')
        self.import_collection_action.setStatusTip('Importar uma coleção do Postman')

        self.exit_action = QAction('Sair', self)
        self.exit_action.triggered.connect(self.close)
        self.exit_action.setToolTip('Sair da aplicação')
        self.exit_action.setStatusTip('Sair da aplicação')

        self.import_environment_action = QAction('Importar Ambiente', self)
        self.import_environment_action.triggered.connect(self.import_environment)
        self.import_environment_action.setToolTip('Importar um ambiente do Postman')
        self.import_environment_action.setStatusTip('Importar um ambiente do Postman')

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # Menu Arquivo
        file_menu = menu_bar.addMenu('Arquivo')
        file_menu.addAction(self.generate_pdf_action)
        file_menu.addAction(self.exit_action)

# menu coleção
        file_menu = menu_bar.addMenu('Coleção')
        file_menu.addAction(self.new_collection_action)
        file_menu.addAction(self.import_collection_action)

# Menu requisição
        file_menu = menu_bar.addMenu('Requisição')
        file_menu.addAction(self.import_curl_action)

        # Menu Variáveis
        variables_menu = menu_bar.addMenu('Variáveis')
        variables_menu.setAccessibleName('Menu Variáveis')

        # Import Environment Action
        variables_menu.addAction(self.import_environment_action)

        # Edit Environments Submenu
        self.edit_environments_menu = variables_menu.addMenu('Editar')
        self.update_edit_environments_menu()

    def update_edit_environments_menu(self):
        self.edit_environments_menu.clear()
        for env_name in self.environments.environments.keys():
            edit_action = QAction(env_name, self)
            edit_action.triggered.connect(lambda checked, name=env_name: self.edit_environment(name))
            self.edit_environments_menu.addAction(edit_action)

    def edit_environment(self, environment_name):
        # Cria uma janela de diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Editar Ambiente - {environment_name}')
        dialog.setModal(True)
        dialog.resize(400, 300)

        layout = QVBoxLayout(dialog)

        # TextEdit para as variáveis do ambiente
        env_text = QPlainTextEdit()
        env_text.setAccessibleName('Variáveis do Ambiente')
        env_text.setTabChangesFocus(True)
        layout.addWidget(env_text)

        # Carrega as variáveis atuais no TextEdit
        variables = self.environments.environments.get(environment_name, {})
        variables_text = '\n'.join(f'{k}={v}' for k, v in variables.items())
        env_text.setPlainText(variables_text)

        # Botão para salvar
        save_button = QPushButton('Salvar')
        save_button.setAccessibleName('Botão Salvar Ambiente')
        save_button.clicked.connect(lambda: self.save_environment_changes(environment_name, env_text.toPlainText(), dialog))
        layout.addWidget(save_button)

        dialog.exec_()

    def save_environment_changes(self, environment_name, variables_text, dialog):
        # Analisa as variáveis a partir do texto
        variables = {}
        for line in variables_text.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                variables[key.strip()] = value.strip()
        # Atualiza o ambiente
        self.environments.environments[environment_name] = variables
        # Salva os ambientes em arquivo
        self.save_environments()
        # Atualiza o combo box e o menu de edição
        self.update_environment_combo()
        self.update_edit_environments_menu()
        # Fecha o diálogo
        dialog.accept()
        QMessageBox.information(self, 'Sucesso', f'Ambiente "{environment_name}" atualizado com sucesso!')

    def _setup_ui(self):
        # Cria o widget principal e o layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()  # Usamos QHBoxLayout para colocar a árvore e os detalhes lado a lado

        # Área de seleção de requisições (Árvore)
        self.tree_widget = QTreeWidget()
        self.tree_widget.setAccessibleName('Árvore de Coleções e Requisições')
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemSelectionChanged.connect(self.on_tree_item_selected)
        self.tree_widget.setFocusPolicy(Qt.StrongFocus)  # Permitir foco via teclado

        # Habilitar menu de contexto personalizado
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.on_tree_item_context_menu)

        # Conectar o sinal de item ativado para expandir/contrair pastas
        self.tree_widget.itemActivated.connect(self.on_item_activated)

        # Instalar o filtro de eventos para capturar teclas
        self.tree_widget.installEventFilter(self)

        # Área de detalhes da requisição e resposta
        self.details_widget = QWidget()
        details_layout = QVBoxLayout()
        self.details_widget.setLayout(details_layout)

        # ComboBox para selecionar o ambiente ativo
        self.environment_combo = QComboBox()
        self.environment_combo.setAccessibleName('Selecionar Ambiente Ativo')
        self.environment_combo.addItem('Nenhum')  # Opção para nenhum ambiente
        self.environment_combo.currentIndexChanged.connect(self.on_environment_changed)
        details_layout.addWidget(QLabel('Ambiente Ativo:'))
        details_layout.addWidget(self.environment_combo)

        # Tabs para detalhes da requisição
        self.request_tabs = QTabWidget()
        self.request_tabs.setAccessibleName('Detalhes da Requisição')

        # Tab de Método HTTP
        method_tab = QWidget()
        method_layout = QVBoxLayout()

        # Grupo de RadioButtons para selecionar o método HTTP
        method_group_box = QGroupBox("Método HTTP:")
        method_group_box.setAccessibleName('Método HTTP da Requisição')
        method_type_layout = QVBoxLayout()
        self.method_type_group = QButtonGroup()

        # Definição dos RadioButtons para métodos HTTP
        self.radio_get = QRadioButton("GET")
        self.radio_get.setAccessibleName('Método GET')
        self.radio_post = QRadioButton("POST")
        self.radio_post.setAccessibleName('Método POST')
        self.radio_put = QRadioButton("PUT")
        self.radio_put.setAccessibleName('Método PUT')
        self.radio_delete = QRadioButton("DELETE")
        self.radio_delete.setAccessibleName('Método DELETE')
        self.radio_patch = QRadioButton("PATCH")
        self.radio_patch.setAccessibleName('Método PATCH')
        self.radio_options = QRadioButton("OPTIONS")
        self.radio_options.setAccessibleName('Método OPTIONS')
        self.radio_head = QRadioButton("HEAD")
        self.radio_head.setAccessibleName('Método HEAD')

        # Adicionar os RadioButtons ao grupo
        self.method_type_group.addButton(self.radio_get)
        self.method_type_group.addButton(self.radio_post)
        self.method_type_group.addButton(self.radio_put)
        self.method_type_group.addButton(self.radio_delete)
        self.method_type_group.addButton(self.radio_patch)
        self.method_type_group.addButton(self.radio_options)
        self.method_type_group.addButton(self.radio_head)

        # Adicionar os RadioButtons ao layout
        method_type_layout.addWidget(self.radio_get)
        method_type_layout.addWidget(self.radio_post)
        method_type_layout.addWidget(self.radio_put)
        method_type_layout.addWidget(self.radio_delete)
        method_type_layout.addWidget(self.radio_patch)
        method_type_layout.addWidget(self.radio_options)
        method_type_layout.addWidget(self.radio_head)
        method_group_box.setLayout(method_type_layout)

        # Conectar o sinal de mudança de seleção
        self.method_type_group.buttonClicked.connect(self.on_method_changed)

        method_layout.addWidget(method_group_box)
        method_tab.setLayout(method_layout)
        self.request_tabs.addTab(method_tab, 'Método')

        # Tab de URL
        url_tab = QWidget()
        url_layout = QVBoxLayout()
        self.url_line_edit = QLineEdit()
        self.url_line_edit.setAccessibleName('URL da Requisição')
        url_layout.addWidget(self.url_line_edit)
        url_tab.setLayout(url_layout)
        self.request_tabs.addTab(url_tab, 'URL')

        # Tab de Headers
        headers_tab = QWidget()
        headers_layout = QVBoxLayout()
        self.headers_text = QPlainTextEdit()
        self.headers_text.setAccessibleName('Headers da Requisição')
        self.headers_text.setTabChangesFocus(True)
        headers_layout.addWidget(self.headers_text)
        headers_tab.setLayout(headers_layout)
        self.request_tabs.addTab(headers_tab, 'Headers')

        # Tab de Autenticação (simplificado)
        auth_tab = QWidget()
        auth_layout = QVBoxLayout()
        self.auth_text = QPlainTextEdit()
        self.auth_text.setAccessibleName('Autenticação da Requisição')
        self.auth_text.setTabChangesFocus(True)
        auth_layout.addWidget(self.auth_text)
        auth_tab.setLayout(auth_layout)
        self.request_tabs.addTab(auth_tab, 'Autenticação')

        # Tab de Corpo (Body)
        body_tab = QWidget()
        body_layout = QVBoxLayout()
        body_form_layout = QFormLayout()

        # Grupo de RadioButtons para selecionar o tipo de corpo
        body_type_group_box = QGroupBox("Tipo de Corpo:")
        body_type_layout = QVBoxLayout()
        self.body_type_group = QButtonGroup()

        # Definição dos RadioButtons
        self.radio_raw_json = QRadioButton("Raw (JSON)")
        self.radio_raw_json.setAccessibleName('Corpo Raw JSON')
        self.radio_raw_xml = QRadioButton("Raw (XML)")
        self.radio_raw_xml.setAccessibleName('Corpo Raw XML')
        self.radio_raw_text = QRadioButton("Raw (Text)")
        self.radio_raw_text.setAccessibleName('Corpo Raw Text')
        self.radio_form_data = QRadioButton("Form Data")
        self.radio_form_data.setAccessibleName('Corpo Form Data')
        self.radio_urlencoded = QRadioButton("x-www-form-urlencoded")
        self.radio_urlencoded.setAccessibleName('Corpo x-www-form-urlencoded')

        # Adiciona os RadioButtons ao grupo
        self.body_type_group.addButton(self.radio_raw_json)
        self.body_type_group.addButton(self.radio_raw_xml)
        self.body_type_group.addButton(self.radio_raw_text)
        self.body_type_group.addButton(self.radio_form_data)
        self.body_type_group.addButton(self.radio_urlencoded)

        # Conecta o sinal de clique dos RadioButtons
        self.body_type_group.buttonClicked.connect(self.on_body_type_changed)

        # Adiciona os RadioButtons ao layout
        body_type_layout.addWidget(self.radio_raw_json)
        body_type_layout.addWidget(self.radio_raw_xml)
        body_type_layout.addWidget(self.radio_raw_text)
        body_type_layout.addWidget(self.radio_form_data)
        body_type_layout.addWidget(self.radio_urlencoded)
        body_type_group_box.setLayout(body_type_layout)

        # TextEdit para o conteúdo do corpo
        self.body_text = QPlainTextEdit()
        self.body_text.setAccessibleName('Corpo da Requisição')
        self.body_text.setTabChangesFocus(True)

        # Adicionar widgets ao layout
        body_layout.addWidget(body_type_group_box)
        body_layout.addWidget(self.body_text)
        body_tab.setLayout(body_layout)
        self.request_tabs.addTab(body_tab, 'Body')

        # Adiciona os widgets ao layout de detalhes
        details_layout.addWidget(QLabel("Requisição:"))
        details_layout.addWidget(self.request_tabs)

        # Botão para executar a requisição
        self.execute_button = QPushButton('Executar Requisição')
        self.execute_button.setAccessibleName('Botão Executar Requisição')
        self.execute_button.clicked.connect(self.execute_request)
        self.execute_button.setEnabled(False)
        details_layout.addWidget(self.execute_button)

        # Checkbox para desabilitar SSL
        self.disable_ssl_checkbox = QCheckBox('Desabilitar verificação SSL')
        self.disable_ssl_checkbox.setAccessibleName('Checkbox Desabilitar SSL')
        details_layout.addWidget(self.disable_ssl_checkbox)

        # Tabs para detalhes da resposta
        self.response_tabs = QTabWidget()
        self.response_tabs.setAccessibleName('Detalhes da Resposta')

        # Tab de Status Code
        status_code_tab = QWidget()
        status_code_layout = QVBoxLayout()
        self.status_code_text = QPlainTextEdit()
        self.status_code_text.setAccessibleName('Código de Status da Resposta')
        self.status_code_text.setReadOnly(True)
        status_code_layout.addWidget(self.status_code_text)
        status_code_tab.setLayout(status_code_layout)
        self.response_tabs.addTab(status_code_tab, 'Status Code')

        # Tab de Headers da Resposta
        response_headers_tab = QWidget()
        response_headers_layout = QVBoxLayout()
        self.response_headers_text = QPlainTextEdit()
        self.response_headers_text.setAccessibleName('Headers da Resposta')
        self.response_headers_text.setReadOnly(True)
        response_headers_layout.addWidget(self.response_headers_text)
        response_headers_tab.setLayout(response_headers_layout)
        self.response_tabs.addTab(response_headers_tab, 'Headers')

        # Tab de Body da Resposta
        response_body_tab = QWidget()
        response_body_layout = QVBoxLayout()
        self.response_body_text = QPlainTextEdit()
        self.response_body_text.setAccessibleName('Body da Resposta')
        self.response_body_text.setReadOnly(True)
        response_body_layout.addWidget(self.response_body_text)
        response_body_tab.setLayout(response_body_layout)
        self.response_tabs.addTab(response_body_tab, 'Body')

        # Adiciona a área de resposta ao layout
        details_layout.addWidget(QLabel("Resposta:"))
        details_layout.addWidget(self.response_tabs)

        # Adiciona o widget de seleção e o de detalhes ao layout principal
        main_layout.addWidget(self.tree_widget, 1)  # 1 para definir a proporção de redimensionamento
        main_layout.addWidget(self.details_widget, 3)  # 3 para definir a proporção de redimensionamento
        main_widget.setLayout(main_layout)

        self.setCentralWidget(main_widget)

    def on_method_changed(self, button):
        selected_method = button.text()
        print(f"Método HTTP selecionado: {selected_method}")
        # Atualiza o método na requisição atual, se houver
        if self.current_request_data:
            self.current_request_data['request']['method'] = selected_method

    def on_tree_item_selected(self):
        selected_items = self.tree_widget.selectedItems()
        if selected_items:
            current_item = selected_items[0]
            item_data = current_item.data(0, Qt.UserRole)
            if item_data and item_data.get('type') == 'request':
                request_id = item_data.get('id')
                self.display_request_details(request_id)
            else:
                self.clear_request_details()
        else:
            self.clear_request_details()

    def on_item_activated(self, item, column):
        item_type = item.data(0, Qt.UserRole).get('type')
        if item_type in ('collection', 'folder'):
            if item.isExpanded():
                self.tree_widget.collapseItem(item)
            else:
                self.tree_widget.expandItem(item)
        elif item_type == 'request':
            request_id = item.data(0, Qt.UserRole).get('id')
            self.display_request_details(request_id)

    def clear_request_details(self):
        self.current_request_data = None
        self.execute_button.setEnabled(False)
        self.url_line_edit.clear()
        self.headers_text.clear()
        self.auth_text.clear()
        self.body_text.clear()
        # Desmarca todos os RadioButtons de método
        self.method_type_group.setExclusive(False)
        for button in self.method_type_group.buttons():
            button.setChecked(False)
        self.method_type_group.setExclusive(True)
        # Desmarca todos os RadioButtons de corpo
        self.body_type_group.setExclusive(False)
        self.radio_raw_json.setChecked(False)
        self.radio_raw_xml.setChecked(False)
        self.radio_raw_text.setChecked(False)
        self.radio_form_data.setChecked(False)
        self.radio_urlencoded.setChecked(False)
        self.body_type_group.setExclusive(True)

    def on_body_type_changed(self, button):
        # Atualiza o cabeçalho Content-Type nos headers com base no RadioButton selecionado
        if button == self.radio_raw_json:
            content_type_value = 'application/json'
        elif button == self.radio_raw_xml:
            content_type_value = 'application/xml'
        elif button == self.radio_raw_text:
            content_type_value = 'text/plain'
        elif button == self.radio_form_data:
            content_type_value = 'multipart/form-data'
        elif button == self.radio_urlencoded:
            content_type_value = 'application/x-www-form-urlencoded'
        else:
            content_type_value = None

        # Obtém os headers atuais
        headers_text = self.headers_text.toPlainText()
        headers_lines = headers_text.strip().split('\n') if headers_text.strip() else []
        # Atualiza ou adiciona o cabeçalho Content-Type
        content_type_updated = False
        for i, line in enumerate(headers_lines):
            if ':' in line:
                key, value = line.split(':', 1)
                if key.strip().lower() == 'content-type':
                    # Atualiza esta linha
                    headers_lines[i] = f'Content-Type: {content_type_value}'
                    content_type_updated = True
                    break
        if not content_type_updated and content_type_value:
            # Adiciona o cabeçalho Content-Type
            headers_lines.append(f'Content-Type: {content_type_value}')
        # Atualiza o texto dos headers
        new_headers_text = '\n'.join(headers_lines)
        self.headers_text.setPlainText(new_headers_text)

    def on_environment_changed(self, index):
        # Ação ao mudar o ambiente ativo
        selected_env = self.environment_combo.currentText()
        print(f'Ambiente ativo selecionado: {selected_env}')

    def import_collection(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Importar Coleção", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if file_name:
            importer = Importer()
            try:
                collection = importer.import_collection(file_name)
                self.collections.append(collection)
                QMessageBox.information(self, "Sucesso", "Coleção importada com sucesso!")
                self.update_collections_view()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao importar a coleção:\n{e}")

    def import_curl(self):
        # 1) Solicita ao usuário o comando cURL
        dialog = QDialog(self)
        dialog.setWindowTitle('Importar cURL')
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel('Cole aqui o comando cURL:'))
        curl_edit = QPlainTextEdit()
        curl_edit.setTabChangesFocus(True)
        curl_edit.setPlaceholderText('Digite o comando cURL...')
        layout.addWidget(curl_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec_() != QDialog.Accepted:
            return

        curl_cmd = curl_edit.toPlainText().strip()
        if not curl_cmd:
            return

        # 2) Converte para objeto Postman-like
        try:
            importer = Importer()
            request_item = importer.import_curl(curl_cmd)
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao parsear cURL:\n{e}')
            return

        # 3) Pergunta onde salvar e qual nome dar
        save_dlg = QDialog(self)
        save_dlg.setWindowTitle('Salvar requisição importada')
        form = QFormLayout(save_dlg)

        combo = QComboBox()
        combo.addItems([c.get('info', {}).get('name', 'Sem Nome') for c in self.collections])
        form.addRow('Coleção:', combo)

        name_edit = QLineEdit(request_item.get('name', 'Nova Requisição'))
        form.addRow('Nome:', name_edit)

        save_btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        save_btns.accepted.connect(save_dlg.accept)
        save_btns.rejected.connect(save_dlg.reject)
        form.addRow(save_btns)

        if save_dlg.exec_() == QDialog.Accepted:
            idx = combo.currentIndex()
            collection = self.collections[idx]
            collection.setdefault('item', []).append(request_item)

            # Limpamos a seleção anterior para não sobrescrever nada
            self.current_request_data = None

            # Agora redesenha toda a árvore com o item recém-adicionado
            self.update_collections_view()

            QMessageBox.information(self, 'Sucesso', 'Requisição importada com sucesso!')

    def create_collection(self):
        name, ok = QInputDialog.getText(self, 'Nova Coleção', 'Nome da nova coleção:')
        if not ok or not name.strip():
            return
        new_coll = {'info': {'name': name.strip()}, 'item': []}
        self.collections.append(new_coll)
        self.update_collections_view()
        self.save_collections()
        QMessageBox.information(self, 'Sucesso', f'Coleção "{name}" criada.')

    def import_environment(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Importar Ambiente", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    environment_name = data.get('name', 'Sem Nome')
                    variables = {item['key']: item['value'] for item in data.get('values', [])}
                    self.environments.add_environment(environment_name, variables)
                    QMessageBox.information(self, "Sucesso", f"Ambiente '{environment_name}' importado com sucesso!")
                    self.update_environment_combo()
                    self.update_edit_environments_menu()
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao importar o ambiente:\n{e}")

    def update_environment_combo(self):
        current_env = self.environment_combo.currentText()
        self.environment_combo.blockSignals(True)  # Evita disparar o sinal
        self.environment_combo.clear()
        self.environment_combo.addItem('Nenhum')
        self.environment_combo.addItems(self.environments.environments.keys())
        # Restaura a seleção anterior, se possível
        index = self.environment_combo.findText(current_env)
        if index != -1:
            self.environment_combo.setCurrentIndex(index)
        self.environment_combo.blockSignals(False)

    def update_collections_view(self):
        self.tree_widget.clear()
        self.request_mapping = {}  # Limpar o mapeamento ao atualizar a árvore
        for idx, collection in enumerate(self.collections):
            collection_name = collection.get('info', {}).get('name', 'Sem Nome')
            formatted_collection_name = f'Coleção: {collection_name}'
            collection_item = QTreeWidgetItem([formatted_collection_name])
            collection_item.setData(0, Qt.UserRole, {
                'type': 'collection',
                'collection': collection,
                'path': [idx]
            })
            self.tree_widget.addTopLevelItem(collection_item)
            for item_idx, item in enumerate(collection.get('item', [])):
                self._add_request_items(collection_item, item, collection, [idx, 'item', item_idx])

    def _add_request_items(self, parent_item, item, collection, path):
        if 'item' in item:
            folder_name = item.get('name', 'Pasta')
            formatted_folder_name = f'Pasta: {folder_name}'
            folder_item = QTreeWidgetItem([formatted_folder_name])
            folder_item.setData(0, Qt.UserRole, {
                'type': 'folder',
                'collection': collection,
                'path': path  # Caminho completo
            })
            parent_item.addChild(folder_item)
            for idx, child_item in enumerate(item['item']):
                self._add_request_items(folder_item, child_item, collection, path + ['item', idx])
        else:
            request_name = item.get('name', 'Requisição')
            formatted_request_name = f'Requisição: {request_name}'
            request_item = QTreeWidgetItem([formatted_request_name])
            request_id = id(item)
            request_item.setData(0, Qt.UserRole, {
                'type': 'request',
                'id': request_id,
                'collection': collection,
                'path': path  # Caminho completo
            })
            self.request_mapping[request_id] = item
            parent_item.addChild(request_item)

    def display_request_details(self, request_id):
        if self.current_request_data:
            self.update_current_request_data_from_ui()

        self.current_request_data = self.request_mapping.get(request_id)
        if self.current_request_data:
            request = self.current_request_data.get('request', {})
            self.execute_button.setEnabled(True)

            # Exibir Método HTTP
            method = request.get('method', 'GET').upper()
            # Desmarca todos os RadioButtons
            self.method_type_group.setExclusive(False)
            for button in self.method_type_group.buttons():
                button.setChecked(False)
            # Marca o RadioButton correspondente ao método
            method_button_mapping = {
                'GET': self.radio_get,
                'POST': self.radio_post,
                'PUT': self.radio_put,
                'DELETE': self.radio_delete,
                'PATCH': self.radio_patch,
                'OPTIONS': self.radio_options,
                'HEAD': self.radio_head
            }
            if method in method_button_mapping:
                method_button_mapping[method].setChecked(True)
            self.method_type_group.setExclusive(True)

            # Exibir URL
            url = request.get('url', {})
            if isinstance(url, dict):
                raw_url = url.get('raw', '')
            else:
                raw_url = url
            self.url_line_edit.setText(raw_url)

            # Exibir Headers
            headers = request.get('header', [])
            headers_formatted = '\n'.join(f"{h.get('key', '')}: {h.get('value', '')}" for h in headers)
            self.headers_text.setPlainText(headers_formatted)

            # Exibir Autenticação (simplificado)
            auth = request.get('auth', {})
            if auth:
                auth_formatted = json.dumps(auth, indent=2)
            else:
                auth_formatted = ''
            self.auth_text.setPlainText(auth_formatted)

            # Exibir Corpo (Body)
            body = request.get('body', {})
            mode = body.get('mode', '')
            if mode == 'raw':
                self.body_text.setPlainText(body.get('raw', ''))
                # Definir o tipo de corpo de acordo com o Content-Type
                headers_dict = {h.get('key', '').lower(): h.get('value', '') for h in headers}
                content_type = headers_dict.get('content-type', '').lower()
                if content_type == 'application/json':
                    self.radio_raw_json.setChecked(True)
                elif content_type == 'application/xml':
                    self.radio_raw_xml.setChecked(True)
                elif content_type == 'text/plain':
                    self.radio_raw_text.setChecked(True)
                else:
                    self.radio_raw_text.setChecked(True)  # Padrão para texto
            elif mode == 'formdata':
                form_data = body.get('formdata', [])
                body_content = '\n'.join(f"{item['key']}={item['value']}" for item in form_data)
                self.body_text.setPlainText(body_content)
                self.radio_form_data.setChecked(True)
            elif mode == 'urlencoded':
                urlencoded_data = body.get('urlencoded', [])
                body_content = '\n'.join(f"{item['key']}={item['value']}" for item in urlencoded_data)
                self.body_text.setPlainText(body_content)
                self.radio_urlencoded.setChecked(True)
            else:
                self.body_text.setPlainText('')
                # Desmarca todos os RadioButtons
                self.body_type_group.setExclusive(False)
                self.radio_raw_json.setChecked(False)
                self.radio_raw_xml.setChecked(False)
                self.radio_raw_text.setChecked(False)
                self.radio_form_data.setChecked(False)
                self.radio_urlencoded.setChecked(False)
                self.body_type_group.setExclusive(True)
        else:
            self.clear_request_details()

    def update_current_request_data_from_ui(self):
        if self.current_request_data is None:
            return

        # Obter os dados editados pelo usuário
        request = {}

        # Método HTTP
        selected_method = None
        for button in self.method_type_group.buttons():
            if button.isChecked():
                selected_method = button.text().strip().upper()
                break
        request['method'] = selected_method if selected_method else 'GET'

        # URL
        url = self.url_line_edit.text().strip()
        request['url'] = url

        # Headers
        headers_text = self.headers_text.toPlainText().strip()
        headers = []
        headers_dict = {}
        if headers_text:
            for line in headers_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    headers.append({'key': key, 'value': value})
                    headers_dict[key.lower()] = value  # Usar lowercase para comparação
        request['header'] = headers

        # Corpo (Body)
        # Detectar qual RadioButton está selecionado
        selected_body_type = None
        for button in self.body_type_group.buttons():
            if button.isChecked():
                selected_body_type = button.text()
                break

        body = {}
        body_text = self.body_text.toPlainText()
        if body_text:
            if selected_body_type.startswith('Raw'):
                body = {'mode': 'raw', 'raw': body_text}
            elif selected_body_type == 'Form Data':
                form_data = []
                for line in body_text.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        form_data.append({'key': key.strip(), 'value': value.strip(), 'type': 'text'})
                body = {'mode': 'formdata', 'formdata': form_data}
            elif selected_body_type == 'x-www-form-urlencoded':
                urlencoded_data = []
                for line in body_text.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        urlencoded_data.append({'key': key.strip(), 'value': value.strip()})
                body = {'mode': 'urlencoded', 'urlencoded': urlencoded_data}
        request['body'] = body

        # O cabeçalho Content-Type é atualizado em on_body_type_changed
        # Portanto, não precisamos adicioná-lo aqui

        # Atualizar a requisição atual com os dados editados
        self.current_request_data['request'] = request

        # **Atualizar o nome da requisição**
        # Se houver um campo 'name' na requisição, preservamos ou atualizamos
        if 'name' in self.current_request_data:
            self.current_request_data['name'] = self.current_request_data.get('name', '')
        else:
            # Se não houver, adicionamos o campo 'name' com um valor padrão
            self.current_request_data['name'] = 'Requisição Sem Nome'

    def execute_request(self):
        if self.current_request_data:
            print("Executando a requisição...")
            self.update_current_request_data_from_ui()
            executor = Executor()

            # Obtém o ambiente selecionado
            selected_env = self.environment_combo.currentText()
            if selected_env == 'Nenhum':
                environment_name = None
            else:
                environment_name = selected_env

            # Aplica o ambiente se selecionado
            if environment_name:
                request_data = {'request': self.current_request_data['request']}
                request_data = self.environments.apply_environment(request_data, environment_name)
            else:
                request_data = self.current_request_data  # Usa a requisição atual sem ambiente

            try:
                # Imprime a requisição para depuração
                print("Requisição enviada:")
                print(json.dumps(request_data['request'], indent=2))

                # Obtém o valor do checkbox
                verify_ssl = not self.disable_ssl_checkbox.isChecked()
                response = executor.execute_request(request_data['request'], verify_ssl=verify_ssl)
                print(f"Resposta recebida com status: {response.status_code}")
                self.show_response(response)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao executar a requisição:\n{e}")
                print(f"Erro ao executar a requisição: {e}")

    def show_response(self, response):
        try:
            print("Exibindo a resposta...")
            print(f"Conteúdo da resposta:\n{response.text}")

            # Exibe o status code e a mensagem
            status_message = response.reason
            status_code_formatted = f"{response.status_code} {status_message}"
            self.status_code_text.setPlainText(status_code_formatted)

            # Exibe os headers
            headers_formatted = '\n'.join(f'{k}: {v}' for k, v in response.headers.items())
            self.response_headers_text.setPlainText(headers_formatted)

            # Exibe o corpo da resposta
            self.response_body_text.setPlainText(response.text)

            # Foca na aba de resposta
            self.response_tabs.setCurrentIndex(0)
        except Exception as e:
            print(f"Erro ao exibir a resposta: {e}")
            QMessageBox.critical(self, "Erro", f"Falha ao exibir a resposta:\n{e}")

    def closeEvent(self, event):
        if self.current_request_data:
            self.update_current_request_data_from_ui()
            # Não precisamos atualizar a coleção aqui, pois o objeto já está atualizado
        self.save_collections()
        self.save_environments()
        event.accept()  # Aceita o evento de fechamento

    def save_collections(self):
        data_dir = 'data'
        os.makedirs(data_dir, exist_ok=True)
        collections_file = os.path.join(data_dir, 'collections.json')
        try:
            with open(collections_file, 'w', encoding='utf-8') as f:
                json.dump(self.collections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Falha ao salvar as coleções:\n{e}")

    def load_collections(self):
        data_dir = 'data'
        collections_file = os.path.join(data_dir, 'collections.json')
        if os.path.exists(collections_file):
            try:
                with open(collections_file, 'r', encoding='utf-8') as f:
                    self.collections = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Aviso", f"Falha ao carregar as coleções:\n{e}")

    def save_environments(self):
        data_dir = 'data'
        os.makedirs(data_dir, exist_ok=True)
        environments_file = os.path.join(data_dir, 'environments.json')
        try:
            with open(environments_file, 'w', encoding='utf-8') as f:
                json.dump(self.environments.environments, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Falha ao salvar os ambientes:\n{e}")

    def load_environments(self):
        data_dir = 'data'
        environments_file = os.path.join(data_dir, 'environments.json')
        if os.path.exists(environments_file):
            try:
                with open(environments_file, 'r', encoding='utf-8') as f:
                    self.environments.environments = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Aviso", f"Falha ao carregar os ambientes:\n{e}")

    def eventFilter(self, source, event):
        if source == self.tree_widget and event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Menu, Qt.Key_F10) and event.modifiers() & Qt.ShiftModifier:
                selected_items = self.tree_widget.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    position = self.tree_widget.visualItemRect(item).center()
                    self.on_tree_item_context_menu(position)
                    return True
            elif event.key() == Qt.Key_Menu:
                selected_items = self.tree_widget.selectedItems()
                if selected_items:
                    item = selected_items[0]
                    position = self.tree_widget.visualItemRect(item).center()
                    self.on_tree_item_context_menu(position)
                    return True
        return super(MainWindow, self).eventFilter(source, event)

    def _rename_item(self, tree_item):
        data = tree_item.data(0, Qt.UserRole) or {}
        tipo = data.get('type')
        collection = data.get('collection')
        path = data.get('path')

        atual = tree_item.text(0).split(': ', 1)[1]

        novo, ok = QInputDialog.getText(
            self,
            'Renomear',
            f'Novo nome para {"pasta" if tipo=="folder" else "requisição"}:',
            text=atual
        )
        if not ok or not novo.strip():
            return

        # Atualiza diretamente o objeto original na coleção usando o caminho armazenado
        obj = self.collections
        for key in path[:-1]:
            obj = obj[key]

        final_key = path[-1]
        if isinstance(final_key, int):
            obj[final_key]['name'] = novo.strip()
        else:
            obj[final_key] = novo.strip()

        prefix = 'Pasta' if tipo == 'folder' else 'Requisição'
        tree_item.setText(0, f'{prefix}: {novo.strip()}')

        self.save_collections()
        QMessageBox.information(self, 'Sucesso', f'{prefix.capitalize()} renomeada para "{novo.strip()}"')

    def on_tree_item_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.UserRole) or {}
        tipo = data.get('type')
        menu = QMenu(self)

        if tipo == 'request':
            rename_act = QAction('Renomear', self)
            rename_act.triggered.connect(lambda _, it=item: self._rename_item(it))
            menu.addAction(rename_act)

            move_act = QAction('Mover para...', self)
            move_act.triggered.connect(lambda _, it=item: self._move_request(it))
            menu.addAction(move_act)

            del_act = QAction('Excluir Requisição', self)
            del_act.triggered.connect(lambda _, it=item: self._delete_item(it))
            menu.addAction(del_act)

        elif tipo == 'folder':
            rename_act = QAction('Renomear', self)
            rename_act.triggered.connect(lambda _, it=item: self._rename_item(it))
            menu.addAction(rename_act)

            del_act = QAction('Excluir Pasta', self)
            del_act.triggered.connect(lambda _, it=item: self._delete_item(it))
            menu.addAction(del_act)

        elif tipo == 'collection':
            new_folder_act = QAction('Nova Pasta', self)
            new_folder_act.triggered.connect(lambda _, it=item: self._new_folder(it))
            menu.addAction(new_folder_act)

            del_act = QAction('Excluir Coleção', self)
            del_act.triggered.connect(lambda _, it=item: self._delete_item(it))
            menu.addAction(del_act)

        menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    def _delete_item(self, tree_item):
        data = tree_item.data(0, Qt.UserRole)
        tipo = data.get('type')
        collection = data['collection']
        path = data['path']

        msg = {
            'collection': 'Deseja realmente excluir esta coleção?',
            'folder': 'Deseja realmente excluir esta pasta?',
            'request': 'Deseja realmente excluir esta requisição?'
        }.get(tipo, 'Deseja realmente excluir este item?')

        reply = QMessageBox.question(
            self, 'Excluir', msg,
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            if tipo == 'collection':
                self.collections.pop(path[0])
            else:
                parent = self.collections
                for key in path[:-2]:
                    parent = parent[key] if isinstance(key, int) else parent.get(key, {})
                parent_key = path[-2]
                index = path[-1]
                if isinstance(parent, dict) and parent_key in parent:
                    parent[parent_key].pop(index)
                elif isinstance(parent, list):
                    parent.pop(index)

            self.save_collections()
            self.update_collections_view()
            QMessageBox.information(self, 'Sucesso', f'{tipo.capitalize()} excluída com sucesso.')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao excluir item:\n{e}')

    def _new_folder(self, collection_item):
        data = collection_item.data(0, Qt.UserRole)
        path = data.get('path', [])

        nome, ok = QInputDialog.getText(
            self, 'Nova Pasta', 'Nome da nova pasta:'
        )
        if not ok or not nome.strip():
            return

        try:
            # Acessa corretamente a coleção no self.collections via path
            obj = self.collections
            for key in path:
                obj = obj[key] if isinstance(key, int) else obj.get(key, {})

            # Garante que existe a chave 'item' (lista de itens)
            obj.setdefault('item', []).append({'name': nome.strip(), 'item': []})

            self.save_collections()
            self.update_collections_view()
            QMessageBox.information(self, 'Sucesso', f'Pasta "{nome.strip()}" criada com sucesso.')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao criar a pasta:\n{e}')


    def _gerar_curl(self, method, url, headers, body):
        curl = f"curl -X {method.upper()} '{url}'"

        for h in headers:
            key = h.get('key', '')
            value = h.get('value', '')
            curl += f" -H '{key}: {value}'"

        if body:
            if isinstance(body, str):
                body_str = body.replace("'", "\\'")
            else:
                try:
                    body_str = json.dumps(body, ensure_ascii=False)
                except Exception:
                    body_str = str(body)
                body_str = body_str.replace("'", "\\'")
            curl += f" -d '{body_str}'"

        return curl

    def generate_evidence_pdf(self):
        if not self.current_request_data:
            QMessageBox.warning(self, "Aviso", "Nenhuma requisição selecionada.")
            return

        try:
            evid_dir = os.path.join(os.getcwd(), "evidência")
            os.makedirs(evid_dir, exist_ok=True)

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"evidencia_{now}.pdf"
            file_path = os.path.join(evid_dir, file_name)

            request = self.current_request_data.get('request', {})
            method = request.get('method', 'GET')
            url = request.get('url', '')
            if isinstance(url, dict):
                url = url.get('raw', '')

            headers = request.get('header', [])
            body = None
            if request.get('body', {}).get('mode') == 'raw':
                try:
                    body = json.loads(request['body'].get('raw', ''))
                except Exception:
                    body = request['body'].get('raw', '')

            curl_cmd = self._gerar_curl(method, url, headers, body)
            status_code = self.status_code_text.toPlainText().strip()
            response_body = self.response_body_text.toPlainText().strip()

            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 50, "Evidência de Requisição HTTP")

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 80, "cURL:")
            c.setFont("Helvetica", 10)
            for i, line in enumerate(curl_cmd.splitlines()):
                c.drawString(60, height - 100 - (i * 12), line)

            y = height - 120 - (len(curl_cmd.splitlines()) * 12)

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Status Code:")
            y -= 15
            c.setFont("Helvetica", 10)
            c.drawString(60, y, status_code)

            y -= 25
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Body:")
            y -= 15
            c.setFont("Helvetica", 10)
            for line in response_body.splitlines():
                if y < 50:
                    c.showPage()
                    y = height - 50
                c.drawString(60, y, line)
                y -= 12

            c.save()
            QMessageBox.information(self, "Sucesso", f"Evidência gerada em:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao gerar evidência:\n{e}")

    def _navigate_to_node(self, root_container, path_list):
        """
        Navega através de uma estrutura aninhada de dicionários e listas.

        Args:
            root_container: O dicionário ou lista raiz para iniciar a navegação
                          (pode ser self.collections ou um item específico da coleção).
            path_list: Uma lista de chaves de dicionário (str) e/ou índices de lista (int)
                       representando o caminho para o nó desejado.

        Returns:
            O nó de destino se encontrado, caso contrário None.
        """
        current_level = root_container
        if not path_list: # Se o caminho é vazio, retorna o próprio container raiz
            return root_container

        for key_or_index in path_list:
            if current_level is None:
                return None  # Não pode navegar mais se o nível atual é None

            if isinstance(key_or_index, str):  # Acessar chave de dicionário
                if isinstance(current_level, dict) and key_or_index in current_level:
                    current_level = current_level[key_or_index]
                else:
                    # Chave não encontrada ou o nível atual não é um dicionário como esperado
                    return None
            elif isinstance(key_or_index, int):  # Acessar índice de lista
                if isinstance(current_level, list) and 0 <= key_or_index < len(current_level):
                    current_level = current_level[key_or_index]
                else:
                    # Índice inválido, ou o nível atual não é uma lista como esperado, ou índice fora dos limites
                    return None
            else:
                # Tipo de passo no caminho é inválido (não é string nem inteiro)
                return None
        return current_level

    def _move_request(self, request_item_widget): # Renomeado para clareza (o argumento é o QTreeWidget)
        data = request_item_widget.data(0, Qt.UserRole)
        if not data or data.get('type') != 'request': # Segurança adicional
            QMessageBox.warning(self, "Atenção", "Item selecionado não é uma requisição válida.")
            return

        current_path_absolute = data['path']  # Path absoluto: [coll_idx, 'item', ..., req_idx]
        
        if not current_path_absolute or not isinstance(current_path_absolute, list) or len(current_path_absolute) < 3:
             QMessageBox.critical(self, "Erro Interno", "Path da requisição inválido.")
             return

        collection_idx = current_path_absolute[0]
        
        try:
            # Garante que collection_idx é um índice válido para self.collections
            if not (isinstance(collection_idx, int) and 0 <= collection_idx < len(self.collections)):
                raise IndexError("Índice da coleção inválido no path da requisição.")
            collection_dict = self.collections[collection_idx] # Acessando o dicionário da coleção corretamente
        except IndexError as e:
            QMessageBox.critical(self, "Erro Interno", f"Não foi possível acessar a coleção: {e}")
            return


        # 1. Reunir todas as pastas e a raiz da coleção como possíveis destinos
        possible_destinations = []  # Lista de tuplas: (path_relativo_a_colecao, nome_exibicao_destino)

        collection_name_info = collection_dict.get('info', {}).get('name', f'Coleção ID {collection_idx}')
        possible_destinations.append(([], f"Raiz da Coleção: {collection_name_info}"))

        def find_folder_destinations_recursive(current_parent_dict, path_to_current_parent_in_collection):
            if 'item' in current_parent_dict and isinstance(current_parent_dict['item'], list):
                for index, child_item in enumerate(current_parent_dict['item']):
                    if isinstance(child_item, dict) and 'name' in child_item and 'item' in child_item:
                        path_to_child_folder_in_collection = path_to_current_parent_in_collection + ['item', index]
                        possible_destinations.append((path_to_child_folder_in_collection, f"Pasta: {child_item['name']}"))
                        find_folder_destinations_recursive(child_item, path_to_child_folder_in_collection)

        find_folder_destinations_recursive(collection_dict, [])

        # 2. Excluir o contêiner (pasta/raiz) atual da requisição das opções de destino
        path_of_request_parent_dict_in_collection = current_path_absolute[1:-2]

        valid_destinations = [
            (path, name)
            for path, name in possible_destinations
            if path != path_of_request_parent_dict_in_collection
        ]

        if not valid_destinations:
            QMessageBox.warning(self, "Sem Destinos", "Nenhum outro local disponível para mover esta requisição.")
            return

        destination_display_names = [name for _, name in valid_destinations]
        selected_display_name, ok = QInputDialog.getItem(
            self, "Mover Requisição Para...", "Selecione o novo local:",
            destination_display_names, 0, False
        )
        if not ok or not selected_display_name:
            return

        # 3. Encontrar o path relativo ao destino selecionado
        try:
            selected_destination_index = destination_display_names.index(selected_display_name)
            target_parent_dict_path_in_collection = valid_destinations[selected_destination_index][0]
        except ValueError:
            QMessageBox.critical(self, "Erro Interno", "Local de destino selecionado inválido.")
            return

        # 4. Remover a requisição do local original
        request_data_to_move = None
        try:
            source_parent_list_path_absolute = current_path_absolute[:-1]
            source_request_index = current_path_absolute[-1]

            parent_list_obj = self._navigate_to_node(self.collections, source_parent_list_path_absolute)

            if parent_list_obj is None or not isinstance(parent_list_obj, list):
                raise ValueError(f"Falha: contêiner de origem não é uma lista válida (path: {source_parent_list_path_absolute}).")

            if 0 <= source_request_index < len(parent_list_obj):
                request_data_to_move = parent_list_obj.pop(source_request_index)
            else:
                raise IndexError(f"Índice da requisição ({source_request_index}) inválido para a lista de origem.")
            
            if request_data_to_move is None:
                raise ValueError("Dados da requisição não puderam ser obtidos para movimentação.")

        except Exception as e:
            QMessageBox.critical(self, "Erro na Remoção", f"Falha ao remover requisição do local original:\n{e}")
            return

        # 5. Adicionar a requisição no dicionário/lista de destino
        try:
            target_parent_obj = self._navigate_to_node(collection_dict, target_parent_dict_path_in_collection)

            if target_parent_obj is None or not isinstance(target_parent_obj, dict):
                raise ValueError(f"Destino não é um dicionário válido (path relativo: {target_parent_dict_path_in_collection}).")

            target_item_list = target_parent_obj.setdefault('item', [])
            if not isinstance(target_item_list, list):
                 target_parent_obj['item'] = []
                 target_item_list = target_parent_obj['item']

            target_item_list.append(request_data_to_move)

        except Exception as e:
            QMessageBox.critical(self, "Erro na Adição", f"Falha ao adicionar requisição ao novo local:\n{e}\nTentando reverter remoção.")
            try:
                parent_list_obj_for_revert = self._navigate_to_node(self.collections, source_parent_list_path_absolute)
                if parent_list_obj_for_revert is not None and isinstance(parent_list_obj_for_revert, list):
                    parent_list_obj_for_revert.insert(source_request_index, request_data_to_move)
                    QMessageBox.information(self, "Reversão", "A remoção da requisição foi revertida.")
                else:
                    QMessageBox.warning(self, "Falha na Reversão", "Não foi possível reverter a remoção automaticamente.")
            except Exception as revert_e:
                 QMessageBox.warning(self, "Falha na Reversão", f"Erro ao tentar reverter: {revert_e}")
            
            self.update_collections_view()
            return

        # 6. Persistir e atualizar UI
        self.save_collections()
        self.update_collections_view()
        QMessageBox.information(
            self, "Sucesso",
            f"Requisição movida para “{selected_display_name}”."
        )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())