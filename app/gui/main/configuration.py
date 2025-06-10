from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QMessageBox,
    QWidget, QVBoxLayout, QPlainTextEdit, QLabel, QPushButton, QTabWidget,
    QLineEdit, QCheckBox, QRadioButton, QButtonGroup, QFormLayout, QDialog,
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QGroupBox, QScrollArea, QComboBox,
    QMenu, QInputDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt
import os
import json
from gui.main.environment import Environment

class Configuration:

    # Função para configurar o ícone da janela principal
    def set_icon(self, os):
        icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'icons', 'ruth.ico')
        self.setWindowIcon(QIcon(icon_path))

    # Função para criar a barra de menu
    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        # Menu Arquivo
        file_menu = menu_bar.addMenu('Arquivo')
        file_menu.addAction(self.generate_pdf_action)
        file_menu.addAction(self.exit_action)

        # Menu coleção
        file_menu = menu_bar.addMenu('Coleção')
        file_menu.addAction(self.new_collection_action)
        file_menu.addAction(self.import_collection_action)

        # Menu requisição
        file_menu = menu_bar.addMenu('Requisição')
        file_menu.addAction(self.import_curl_action)

        # Menu Ambientes
        environments_menu = menu_bar.addMenu('Ambientes')
        environments_menu.setAccessibleName('Menu Ambientes')

        # Import Environment Action
        environments_menu.addAction(self.import_environment_action)

        # Edit Environments Submenu
        self.edit_environments_menu = environments_menu.addMenu('Editar')
        self.update_edit_environments_menu()
  
    # Função para criar os actions
    def _create_actions(self):
        self.generate_pdf_action = QAction('Gerar Evidência em PDF', self)
        self.generate_pdf_action.triggered.connect(self.generate_pdf_evidence)

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
        self.import_environment_action.triggered.connect(lambda: Environment.import_environment(self))
        self.import_environment_action.setToolTip('Importar um ambiente do Postman')
        self.import_environment_action.setStatusTip('Importar um ambiente do Postman')

    # Função para configurar a interface gráfica principal da janela
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