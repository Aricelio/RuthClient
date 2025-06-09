import sys
import os
import json
import urllib3
import uuid
import traceback
import shlex  # ### NOVO ### Importe o shlex para escapar argumentos do shell

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog, QMessageBox,
    QWidget, QVBoxLayout, QPlainTextEdit, QLabel, QPushButton, QTabWidget,
    QLineEdit, QCheckBox, QRadioButton, QButtonGroup, QFormLayout, QDialog,
    QTreeWidget, QTreeWidgetItem, QHBoxLayout, QGroupBox, QScrollArea, QComboBox,
    QMenu, QInputDialog, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QKeyEvent, QTextCursor

# Ajuste os imports do 'core' se a sua estrutura de pastas for diferente.
# Exemplo: se 'gui' e 'core' são subpastas de um projeto principal:
# from ..core.importer import Importer
# from ..core.executor import Executor
# from ..core.environment import EnvironmentManager
# Se 'main_window.py' está na raiz e 'core' é uma subpasta:
from core.importer import Importer
from core.executor import Executor
from core.environment import EnvironmentManager


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AccessiblePlainTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabChangesFocus(True)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Tab and not event.modifiers():
            if self.window():
                current_focus_widget = QApplication.focusWidget()
                if current_focus_widget:
                    next_widget = current_focus_widget.nextInFocusChain()
                    if next_widget:
                        next_widget.setFocus(Qt.TabFocusReason) # Especifica a razão do foco
                    else:
                        self.window().focusNextChild()
                else:
                    self.window().focusNextChild()
            event.accept()
            return
        elif event.key() == Qt.Key_Tab and event.modifiers() & Qt.ShiftModifier:
            if self.window():
                current_focus_widget = QApplication.focusWidget()
                if current_focus_widget:
                    previous_widget = current_focus_widget.previousInFocusChain()
                    if previous_widget:
                        previous_widget.setFocus(Qt.BacktabFocusReason) # Especifica a razão do foco
                    else:
                        self.window().focusPreviousChild()
                else:
                    self.window().focusPreviousChild()
            event.accept()
            return
        super().keyPressEvent(event)


# main_window.py

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Ferramenta de Requisições HTTP')
        self.setGeometry(100, 100, 1450, 950) # Levemente maior
        self.collections = []
        self.environments = EnvironmentManager()
        self.current_request_data = None
        self.request_mapping = {}
        self.item_path_map = {}
        self._create_actions()
        self._create_menu_bar()
        self._setup_ui()

        # Adiciona o menu de contexto ao QTreeWidget
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.on_tree_item_context_menu)


        self.load_collections()
        self.load_environments()
        self.update_environment_combo()
        self.update_edit_environments_menu()
        self.update_collections_view()
        
        self.tree_widget.setFocus()

    def _create_actions(self):
        self.generate_pdf_action = QAction('Gerar Evidência em PDF...', self) # "..." indica diálogo
        self.generate_pdf_action.triggered.connect(self.generate_evidence_pdf)
        self.generate_pdf_action.setToolTip("Gera um relatório PDF da requisição e resposta atuais.")
        self.generate_pdf_action.setStatusTip("Gerar PDF da evidência da requisição atual.")

        self.new_collection_action = QAction('Nova Coleção...', self)
        self.new_collection_action.triggered.connect(lambda: self.create_collection())
        self.new_collection_action.setToolTip('Criar uma nova coleção vazia para organizar requisições.')
        self.new_collection_action.setStatusTip('Criar uma nova coleção.')

        self.import_curl_action = QAction('Importar cURL...', self)
        self.import_curl_action.triggered.connect(self.import_curl)
        self.import_curl_action.setToolTip('Importar uma requisição a partir de um comando cURL copiado.')
        self.import_curl_action.setStatusTip('Importar requisição de cURL.')

        self.import_collection_action = QAction('Importar Coleção...', self)
        self.import_collection_action.triggered.connect(self.import_collection)
        self.import_collection_action.setToolTip('Importar uma coleção de requisições de um arquivo JSON (formato Postman).')
        self.import_collection_action.setStatusTip('Importar coleção de arquivo Postman.')

        self.exit_action = QAction('Sair', self)
        self.exit_action.triggered.connect(self.close)
        self.exit_action.setToolTip("Fechar a aplicação.")
        self.exit_action.setStatusTip("Sair da Ferramenta de Requisições HTTP.")

        self.import_environment_action = QAction('Importar Ambiente...', self)
        self.import_environment_action.triggered.connect(self.import_environment)
        self.import_environment_action.setToolTip('Importar variáveis de ambiente de um arquivo JSON (formato Postman).')
        self.import_environment_action.setStatusTip('Importar ambiente de arquivo Postman.')

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        self.statusBar() # Necessário para setStatusTip funcionar

        file_menu = menu_bar.addMenu('&Arquivo')
        file_menu.setAccessibleName("Menu Arquivo")
        file_menu.addAction(self.generate_pdf_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        collection_menu = menu_bar.addMenu('&Coleção')
        collection_menu.setAccessibleName("Menu Coleção")
        collection_menu.addAction(self.new_collection_action)
        collection_menu.addAction(self.import_collection_action)

        request_menu = menu_bar.addMenu('&Requisição')
        request_menu.setAccessibleName("Menu Requisição")
        request_menu.addAction(self.import_curl_action)

        variables_menu = menu_bar.addMenu('&Variáveis')
        variables_menu.setAccessibleName("Menu Variáveis")
        variables_menu.addAction(self.import_environment_action)
        self.edit_environments_menu = variables_menu.addMenu('&Editar Ambiente')
        self.edit_environments_menu.setAccessibleName("Submenu Editar Ambiente")
        self.update_edit_environments_menu()

    def update_environment_combo(self):
        """Atualiza o QComboBox de ambientes com os ambientes carregados."""
        current_env_text = self.environment_combo.currentText()
        self.environment_combo.blockSignals(True)
        self.environment_combo.clear()
        self.environment_combo.addItem("Nenhum")
        
        env_names = sorted(list(self.environments.environments.keys()))
        if env_names:
            self.environment_combo.addItems(env_names)
        
        # Tenta restaurar a seleção anterior
        index_to_select = self.environment_combo.findText(current_env_text)
        if index_to_select != -1:
            self.environment_combo.setCurrentIndex(index_to_select)
        else:
            if self.environment_combo.count() > 0:
                self.environment_combo.setCurrentIndex(0) # Seleciona "Nenhum" ou o primeiro se "Nenhum" não estiver
                
        self.environment_combo.blockSignals(False)
        print(f"ComboBox de ambiente atualizado. Selecionado: {self.environment_combo.currentText()}")

    def update_edit_environments_menu(self):
        self.edit_environments_menu.clear()
        if not self.environments.environments:
            no_env_action = QAction("Nenhum ambiente para editar", self)
            no_env_action.setEnabled(False)
            self.edit_environments_menu.addAction(no_env_action)
            return

        for env_name in sorted(list(self.environments.environments.keys())):
            edit_action = QAction(env_name, self)
            edit_action.setToolTip(f"Editar as variáveis do ambiente {env_name}")
            edit_action.setStatusTip(f"Abrir diálogo para editar o ambiente {env_name}.")
            edit_action.triggered.connect(lambda checked, name=env_name: self.edit_environment(name))
            self.edit_environments_menu.addAction(edit_action)

    def edit_environment(self, environment_name):
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Editar Ambiente: {environment_name}')
        dialog.setModal(True)
        dialog.resize(450, 350)
        
        main_layout = QVBoxLayout(dialog)
        
        info_label = QLabel(f"Modifique as variáveis para o ambiente '{environment_name}'.\nUse o formato: chave=valor (uma variável por linha).")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        env_text_edit = QPlainTextEdit()
        env_text_edit.setAccessibleName(f'Variáveis do ambiente {environment_name}')
        env_text_edit.setTabChangesFocus(True)
        
        current_variables = self.environments.environments.get(environment_name, {})
        variables_display_text = '\n'.join(f'{k}={v}' for k, v in current_variables.items())
        env_text_edit.setPlainText(variables_display_text)
        main_layout.addWidget(env_text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = button_box.button(QDialogButtonBox.Save)
        if save_button:
            save_button.setText("Salvar")
            save_button.setAccessibleName(f"Salvar ambiente {environment_name}")
        
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        if cancel_button:
            cancel_button.setText("Cancelar")
            cancel_button.setAccessibleName(f"Cancelar edição do ambiente {environment_name}")

        button_box.accepted.connect(lambda: self.save_environment_changes(environment_name, env_text_edit.toPlainText(), dialog))
        button_box.rejected.connect(dialog.reject)
        main_layout.addWidget(button_box)
        
        dialog.exec_()

    def save_environment_changes(self, environment_name_str, variables_text_str, dialog_ref):
        new_variables_dict = {}
        for line_str in variables_text_str.strip().split('\n'):
            if '=' in line_str:
                key_str, value_str = line_str.split('=', 1)
                key_stripped = key_str.strip()
                if key_stripped: # Adiciona apenas se a chave não for vazia
                    new_variables_dict[key_stripped] = value_str.strip()
        
        self.environments.environments[environment_name_str] = new_variables_dict
        self.save_environments()
        
        self.update_environment_combo()
        self.update_edit_environments_menu()
        
        dialog_ref.accept()
        QMessageBox.information(self, 'Ambiente Atualizado', f'O ambiente "{environment_name_str}" foi atualizado com sucesso!')

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)
        left_panel_layout.setContentsMargins(0,0,0,0)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setAccessibleName("Navegação de Coleções")
        self.tree_widget.setHeaderHidden(True)
        self.tree_widget.itemSelectionChanged.connect(self.on_tree_item_selected)
        # Removida a conexão duplicada de customContextMenuRequested, já que é conectada em __init__
        self.tree_widget.itemActivated.connect(self.on_item_activated)
        self.tree_widget.installEventFilter(self)
        left_panel_layout.addWidget(self.tree_widget)

        self.details_widget = QWidget()
        details_layout = QVBoxLayout(self.details_widget)

        env_group = QGroupBox("Ambiente")
        env_group.setAccessibleName("Configuração de Ambiente")
        env_form_layout = QFormLayout(env_group)
        
        label_active_env = QLabel('&Ativo:')
        self.environment_combo = QComboBox()
        self.environment_combo.setAccessibleName("Ambiente ativo")
        self.environment_combo.setToolTip("Selecione o ambiente a ser usado.")
        self.environment_combo.addItem('Nenhum')
        label_active_env.setBuddy(self.environment_combo)
        self.environment_combo.currentIndexChanged.connect(self.on_environment_changed)
        env_form_layout.addRow(label_active_env, self.environment_combo)
        details_layout.addWidget(env_group)

        self.request_tabs = QTabWidget()
        self.request_tabs.setAccessibleName("Detalhes da Requisição")

        method_tab = QWidget()
        # method_tab.setAccessibleName("Método HTTP") # O GroupBox abaixo é mais específico
        method_layout = QVBoxLayout(method_tab)
        method_group_box = QGroupBox("Método HTTP")
        method_group_box.setAccessibleName("Seleção do Método HTTP")
        method_type_layout = QVBoxLayout(method_group_box)
        self.method_type_group = QButtonGroup(self)
        methods_list = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]
        self.method_radios = {}
        for method_name_str in methods_list:
            radio_btn = QRadioButton(method_name_str)
            radio_btn.setAccessibleName(f"Método {method_name_str}")
            self.method_radios[method_name_str] = radio_btn
            self.method_type_group.addButton(radio_btn)
            method_type_layout.addWidget(radio_btn)
        self.method_type_group.buttonClicked.connect(self.on_method_changed)
        method_layout.addWidget(method_group_box)
        method_layout.addStretch()
        self.request_tabs.addTab(method_tab, '&Método')

        url_tab = QWidget()
        # url_tab.setAccessibleName("URL") # O QLineEdit abaixo é mais específico
        url_layout = QFormLayout(url_tab)
        label_url = QLabel("&URL:")
        self.url_line_edit = QLineEdit()
        self.url_line_edit.setAccessibleName("URL da Requisição")
        self.url_line_edit.setToolTip("Digite a URL completa.")
        label_url.setBuddy(self.url_line_edit)
        url_layout.addRow(label_url, self.url_line_edit)
        self.request_tabs.addTab(url_tab, 'U&RL')

        headers_tab = QWidget()
        # headers_tab.setAccessibleName("Cabeçalhos") # O QPlainTextEdit abaixo é mais específico
        headers_layout = QVBoxLayout(headers_tab)
        label_headers = QLabel("&Cabeçalhos (chave: valor):")
        self.headers_text = QPlainTextEdit()
        self.headers_text.setTabChangesFocus(True)
        self.headers_text.setAccessibleName("Cabeçalhos da Requisição")
        self.headers_text.setToolTip("Insira os cabeçalhos HTTP, um por linha.")
        label_headers.setBuddy(self.headers_text)
        headers_layout.addWidget(label_headers)
        headers_layout.addWidget(self.headers_text)
        self.request_tabs.addTab(headers_tab, '&Headers')
        
        auth_tab = QWidget()
        # auth_tab.setAccessibleName("Autenticação") # O QPlainTextEdit abaixo é mais específico
        auth_layout = QVBoxLayout(auth_tab)
        label_auth = QLabel("A&utenticação (JSON):")
        self.auth_text = QPlainTextEdit()
        self.auth_text.setTabChangesFocus(True)
        self.auth_text.setAccessibleName("Configuração de Autenticação")
        self.auth_text.setToolTip("Insira configuração de autenticação (JSON).")
        label_auth.setBuddy(self.auth_text)
        auth_layout.addWidget(label_auth)
        auth_layout.addWidget(self.auth_text)
        self.request_tabs.addTab(auth_tab, 'A&utenticação')

        body_tab = QWidget()
        # body_tab.setAccessibleName("Corpo da Requisição") # O GroupBox e QPlainTextEdit são mais específicos
        body_layout = QVBoxLayout(body_tab)
        body_type_group_box = QGroupBox("Tipo de Corpo")
        body_type_group_box.setAccessibleName("Seleção do Tipo de Corpo")
        body_type_grid_layout = QHBoxLayout(body_type_group_box)
        self.body_type_group = QButtonGroup(self)
        body_types_list = ["Raw (JSON)", "Raw (XML)", "Raw (Text)", "Form Data", "x-www-form-urlencoded", "Nenhum"]
        self.body_type_radios = {}
        for btype_str in body_types_list:
            radio_btn = QRadioButton(btype_str)
            radio_btn.setAccessibleName(f"Tipo de corpo {btype_str}")
            self.body_type_radios[btype_str] = radio_btn
            self.body_type_group.addButton(radio_btn)
            body_type_grid_layout.addWidget(radio_btn)
        body_type_grid_layout.addStretch()
        self.body_type_group.buttonClicked.connect(self.on_body_type_changed)
        body_layout.addWidget(body_type_group_box)
        
        label_body_content = QLabel("Conteúdo do &Corpo:")
        self.body_text = QPlainTextEdit()
        self.body_text.setTabChangesFocus(True)
        self.body_text.setAccessibleName("Conteúdo do Corpo da Requisição")
        self.body_text.setToolTip("Insira o conteúdo do corpo.")
        label_body_content.setBuddy(self.body_text)
        body_layout.addWidget(label_body_content)
        body_layout.addWidget(self.body_text)
        self.request_tabs.addTab(body_tab, '&Corpo')

        scripts_tab = QWidget()
        # scripts_tab.setAccessibleName("Scripts") # Os GroupBoxes abaixo são mais específicos
        scripts_layout = QVBoxLayout(scripts_tab)
        
        pre_request_group = QGroupBox("Pré-Requisição (Python)")
        pre_request_group.setAccessibleName("Script de Pré-Requisição")
        pre_request_layout = QVBoxLayout(pre_request_group)
        self.pre_request_script_text = AccessiblePlainTextEdit()
        self.pre_request_script_text.setPlaceholderText("# Script ANTES da requisição.")
        self.pre_request_script_text.setAccessibleName("Editor Script de Pré-Requisição")
        self.pre_request_script_text.setToolTip("Script Python executado antes do envio.")
        pre_request_layout.addWidget(self.pre_request_script_text)
        scripts_layout.addWidget(pre_request_group)
        
        test_script_group = QGroupBox("Teste (Python)")
        test_script_group.setAccessibleName("Script de Teste")
        test_script_layout = QVBoxLayout(test_script_group)
        self.test_script_text = AccessiblePlainTextEdit()
        self.test_script_text.setPlaceholderText("# Script APÓS a resposta.")
        self.test_script_text.setAccessibleName("Editor Script de Teste")
        self.test_script_text.setToolTip("Script Python executado após a resposta.")
        test_script_layout.addWidget(self.test_script_text)
        scripts_layout.addWidget(test_script_group)
        self.request_tabs.addTab(scripts_tab, '&Scripts')

        details_layout.addWidget(self.request_tabs)

        execution_controls_widget = QWidget()
        execution_controls_layout = QHBoxLayout(execution_controls_widget)
        execution_controls_layout.setContentsMargins(0,5,0,0)
        
        self.execute_button = QPushButton('&Executar Requisição')
        self.execute_button.setAccessibleName("Executar Requisição")
        self.execute_button.setToolTip("Envia a requisição HTTP.")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.execute_request)
        execution_controls_layout.addWidget(self.execute_button)
        
        self.disable_ssl_checkbox = QCheckBox('Desabilitar &verificação SSL')
        self.disable_ssl_checkbox.setAccessibleName("Desabilitar verificação SSL")
        self.disable_ssl_checkbox.setToolTip("Ignorar erros de certificado SSL.")
        execution_controls_layout.addWidget(self.disable_ssl_checkbox)
        execution_controls_layout.addStretch()
        details_layout.addWidget(execution_controls_widget)

        self.response_tabs = QTabWidget()
        self.response_tabs.setAccessibleName("Detalhes da Resposta")
        
        status_code_tab_resp = QWidget()
        # status_code_tab_resp.setAccessibleName("Status Resposta") # O QPlainTextEdit abaixo é mais específico
        status_code_layout_resp = QVBoxLayout(status_code_tab_resp)
        self.status_code_text = QPlainTextEdit()
        self.status_code_text.setReadOnly(True)
        self.status_code_text.setAccessibleName("Status, Tempo e Tamanho da Resposta")
        status_code_layout_resp.addWidget(self.status_code_text)
        self.response_tabs.addTab(status_code_tab_resp, 'Statu&s')
        
        response_headers_tab = QWidget()
        # response_headers_tab.setAccessibleName("Cabeçalhos Resposta") # O QPlainTextEdit abaixo é mais específico
        response_headers_layout = QVBoxLayout(response_headers_tab)
        label_resp_headers = QLabel("Cabeçalhos da Resposta:")
        self.response_headers_text = QPlainTextEdit()
        self.response_headers_text.setReadOnly(True)
        self.response_headers_text.setAccessibleName("Cabeçalhos da Resposta")
        label_resp_headers.setBuddy(self.response_headers_text)
        response_headers_layout.addWidget(label_resp_headers)
        response_headers_layout.addWidget(self.response_headers_text)
        self.response_tabs.addTab(response_headers_tab, 'Heade&rs (Resposta)')
        
        response_body_tab = QWidget()
        response_body_layout = QVBoxLayout(response_body_tab)
        label_resp_body = QLabel("Corpo da Resposta:")
        self.response_body_text = QPlainTextEdit()
        self.response_body_text.setReadOnly(True)
        self.response_body_text.setAccessibleName("Corpo da Resposta")
        label_resp_body.setBuddy(self.response_body_text)
        response_body_layout.addWidget(label_resp_body)
        response_body_layout.addWidget(self.response_body_text)
        self.response_tabs.addTab(response_body_tab, 'Co&rpo (Resposta)')

        details_layout.addWidget(self.response_tabs)
        main_layout.addWidget(left_panel_widget, 1)
        main_layout.addWidget(self.details_widget, 3)

    def update_collections_view(self):
        self.tree_widget.clear()
        self.request_mapping.clear()
        self.item_path_map.clear() # Limpa o mapa a cada atualização

        if not self.collections:
            placeholder_item = QTreeWidgetItem(["Nenhuma coleção carregada."])
            placeholder_item.setData(0, Qt.UserRole, {'type': 'placeholder'})
            placeholder_item.setDisabled(True)
            self.tree_widget.addTopLevelItem(placeholder_item)
            return

        for coll_idx, collection_data_dict in enumerate(self.collections):
            collection_info_dict = collection_data_dict.get('info', {})
            collection_name_str = collection_info_dict.get('name', f'Coleção Sem Nome {coll_idx + 1}')
            
            collection_tree_item = QTreeWidgetItem([f"Coleção: {collection_name_str}"])
            collection_tree_item.setToolTip(0, f"Coleção de requisições: {collection_name_str}")
            
            path = [coll_idx]
            self.item_path_map[tuple(path)] = collection_tree_item

            collection_tree_item.setData(0, Qt.UserRole, {
                'type': 'collection',
                'id': collection_info_dict.get('_postman_id', str(id(collection_data_dict))),
                'path': path,
                'object_ref': collection_data_dict
            })
            self.tree_widget.addTopLevelItem(collection_tree_item)

            items_in_collection_list = collection_data_dict.get('item', [])
            for item_idx, item_data_dict_in_coll in enumerate(items_in_collection_list):
                self._add_tree_items_recursive(collection_tree_item, item_data_dict_in_coll, path + ['item', item_idx])
        
    def _add_tree_items_recursive(self, parent_tree_item_widget, current_item_data_dict, current_path_list):
        item_name_str = current_item_data_dict.get('name', 'Item Sem Nome')
        
        if 'item' in current_item_data_dict and isinstance(current_item_data_dict['item'], list): # É uma pasta
            folder_tree_item = QTreeWidgetItem([f"Pasta: {item_name_str}"])
            folder_tree_item.setToolTip(0, f"Pasta de requisições: {item_name_str}")
            
            self.item_path_map[tuple(current_path_list)] = folder_tree_item

            folder_tree_item.setData(0, Qt.UserRole, {
                'type': 'folder',
                'id': current_item_data_dict.get('_postman_id', str(id(current_item_data_dict))),
                'path': current_path_list,
                'object_ref': current_item_data_dict
            })
            parent_tree_item_widget.addChild(folder_tree_item)
            
            sub_items_list = current_item_data_dict.get('item', [])
            for sub_item_idx, sub_item_data_dict in enumerate(sub_items_list):
                self._add_tree_items_recursive(folder_tree_item, sub_item_data_dict, current_path_list + ['item', sub_item_idx])
        
        elif 'request' in current_item_data_dict: # É uma requisição
            request_tree_item = QTreeWidgetItem([f"Requisição: {item_name_str}"])
            request_tree_item.setToolTip(0, f"Requisição HTTP: {item_name_str}")
            
            self.item_path_map[tuple(current_path_list)] = request_tree_item

            request_py_id = current_item_data_dict.get('_postman_id')
            if not request_py_id:
                request_obj_inside_item = current_item_data_dict.get('request')
                if request_obj_inside_item:
                    request_py_id = str(id(request_obj_inside_item))
                else:
                    request_py_id = str(id(current_item_data_dict))

            request_tree_item.setData(0, Qt.UserRole, {
                'type': 'request',
                'id': request_py_id, 
                'path': current_path_list,
                'object_ref': current_item_data_dict 
            })
            self.request_mapping[request_py_id] = current_item_data_dict 
            parent_tree_item_widget.addChild(request_tree_item)
        else:
            unknown_item_tree = QTreeWidgetItem([f"[Desconhecido] {item_name_str}"])
            unknown_item_tree.setDisabled(True)
            parent_tree_item_widget.addChild(unknown_item_tree)

    # =========================================================================
    # MÉTODOS DE PERSISTÊNCIA (load/save collections/environments)
    # =========================================================================
    def _get_data_path(self, filename_str): 
        data_dir_str = 'data' 
        try:
            os.makedirs(data_dir_str, exist_ok=True) 
        except OSError as e:
            print(f"Aviso: Não foi possível criar o diretório de dados '{data_dir_str}': {e}")
            return os.path.join(os.getcwd(), filename_str)
        return os.path.join(data_dir_str, filename_str)

    def save_collections(self):
        try:
            collections_file_path = self._get_data_path('collections.json')
            with open(collections_file_path, 'w', encoding='utf-8') as f_out:
                json.dump(self.collections, f_out, indent=2, ensure_ascii=False)
            print(f"Coleções salvas em: {collections_file_path}")
        except Exception as e:
            print(f"Erro crítico ao salvar coleções: {e}")
            QMessageBox.warning(self, "Erro ao Salvar Coleções", f"Não foi possível salvar as coleções:\n{type(e).__name__}: {e}")

    def load_collections(self): 
        collections_file_path = self._get_data_path('collections.json')
        if os.path.exists(collections_file_path):
            try:
                with open(collections_file_path, 'r', encoding='utf-8') as f_in:
                    loaded_collections = json.load(f_in)
                    if isinstance(loaded_collections, list): 
                        self.collections = loaded_collections
                        print(f"Coleções carregadas de: {collections_file_path}")
                    else:
                        print(f"Arquivo {collections_file_path} não contém uma lista válida. Iniciando com lista vazia.")
                        self.collections = []
            except json.JSONDecodeError as jde:
                print(f"Erro ao decodificar JSON de {collections_file_path}: {jde}. Iniciando com lista vazia.")
                self.collections = []
                QMessageBox.warning(self, "Erro ao Carregar Coleções", f"Arquivo de coleções corrompido: {collections_file_path}\nUm novo arquivo será criado.")
            except Exception as e:
                print(f"Erro crítico ao carregar coleções: {e}")
                self.collections = [] 
                QMessageBox.warning(self, "Erro ao Carregar Coleções", f"Falha ao carregar coleções: {e}")
        else:
            print(f"Arquivo de coleções {collections_file_path} não encontrado. Iniciando com lista vazia.")
            self.collections = []

    def save_environments(self):
        try:
            environments_file_path = self._get_data_path('environments.json')
            with open(environments_file_path, 'w', encoding='utf-8') as f_out:
                json.dump(self.environments.environments, f_out, indent=2, ensure_ascii=False)
            print(f"Ambientes salvos em: {environments_file_path}")
        except Exception as e:
            print(f"Erro crítico ao salvar ambientes: {e}")
            QMessageBox.warning(self, "Erro ao Salvar Ambientes", f"Não foi possível salvar os ambientes:\n{type(e).__name__}: {e}")

    def load_environments(self):
        environments_file_path = self._get_data_path('environments.json')
        if os.path.exists(environments_file_path):
            try:
                with open(environments_file_path, 'r', encoding='utf-8') as f_in:
                    loaded_environments = json.load(f_in)
                    if isinstance(loaded_environments, dict): 
                        self.environments.environments = loaded_environments
                        print(f"Ambientes carregados de: {environments_file_path}")
                    else:
                        print(f"Arquivo {environments_file_path} não contém um dicionário válido. Iniciando com dict vazio.")
                        self.environments.environments = {}
            except json.JSONDecodeError as jde:
                print(f"Erro ao decodificar JSON de {environments_file_path}: {jde}. Iniciando com dict vazio.")
                self.environments.environments = {}
                QMessageBox.warning(self, "Erro ao Carregar Ambientes", f"Arquivo de ambientes corrompido: {environments_file_path}\nUm novo arquivo será criado.")
            except Exception as e:
                print(f"Erro crítico ao carregar ambientes: {e}")
                self.environments.environments = {} 
        else:
            print(f"Arquivo de ambientes {environments_file_path} não encontrado. Iniciando com dict vazio.")
            self.environments.environments = {}

    # --- Demais métodos da classe MainWindow ---
    def create_collection(self, prompt_name_str="Nova Coleção"):
        dialog = QDialog(self)
        dialog.setWindowTitle(str(prompt_name_str)) 
        dialog.setModal(True)
        dialog.resize(350, 150)

        layout = QVBoxLayout(dialog)
        
        label_name = QLabel("Nome da nova coleção:")
        name_edit = QLineEdit()
        name_edit.setAccessibleName("Nome da nova coleção")
        name_edit.setToolTip("Digite um nome descritivo para a nova coleção.")
        label_name.setBuddy(name_edit) 
        
        form_layout = QFormLayout() 
        form_layout.addRow(label_name, name_edit)
        layout.addLayout(form_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        if ok_button:
            ok_button.setText("Criar") 
            ok_button.setAccessibleName("Botão Criar")
        
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        if cancel_button:
            cancel_button.setText("Cancelar")
            cancel_button.setAccessibleName("Botão Cancelar")

        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        name_edit.setFocus()

        if dialog.exec_() == QDialog.Accepted:
            coll_name_input_str = name_edit.text().strip()
            if coll_name_input_str:
                new_collection_name_stripped = coll_name_input_str
                new_collection_data_dict = {
                    'info': {
                        'name': new_collection_name_stripped,
                        '_postman_id': str(uuid.uuid4()), 
                        'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
                    }, 
                    'item': [],  
                    'event': []  
                }
                self.collections.append(new_collection_data_dict)
                self.update_collections_view() 
                self.save_collections() 
                QMessageBox.information(self, 'Coleção Criada', 
                                        f'A coleção "{new_collection_name_stripped}" foi criada com sucesso.')
                return True 
            else: 
                QMessageBox.warning(self, "Nome Inválido", 
                                    "O nome da coleção não pode ser vazio.")
                return False
        return False 

    def on_method_changed(self, clicked_radio_button):
        print(f"Método HTTP selecionado na UI: {clicked_radio_button.text()}")

    def on_tree_item_selected(self):
        selected_tree_items_list = self.tree_widget.selectedItems()
        if selected_tree_items_list:
            current_tree_item_widget = selected_tree_items_list[0]
            item_role_data_dict = current_tree_item_widget.data(0, Qt.UserRole)
            
            if item_role_data_dict and item_role_data_dict.get('type') == 'request':
                request_py_id = item_role_data_dict.get('id')
                self.display_request_details(request_py_id) 
            else: 
                self.clear_request_details() 
        else: 
            self.clear_request_details()

    def on_item_activated(self, activated_tree_item_widget, column_index_int):
        item_role_data_dict = activated_tree_item_widget.data(0, Qt.UserRole)
        item_type_str = item_role_data_dict.get('type')
        
        if item_type_str in ('collection', 'folder'):
            activated_tree_item_widget.setExpanded(not activated_tree_item_widget.isExpanded())
        elif item_type_str == 'request':
            request_py_id = item_role_data_dict.get('id')
            self.display_request_details(request_py_id)
            self.execute_button.setFocus()

    def clear_request_details(self):
        self.current_request_data = None 
        self.execute_button.setEnabled(False)
        self.url_line_edit.clear()
        self.url_line_edit.setStatusTip("")
        self.headers_text.clear()
        self.auth_text.clear()
        self.body_text.clear()
        self.pre_request_script_text.clear()
        self.test_script_text.clear()

        self.method_type_group.setExclusive(False) 
        for radio_btn in self.method_radios.values(): radio_btn.setChecked(False)
        self.method_type_group.setExclusive(True) 

        self.body_type_group.setExclusive(False)
        for radio_btn in self.body_type_radios.values(): radio_btn.setChecked(False)
        self.body_type_group.setExclusive(True)

        self.status_code_text.clear()
        self.response_headers_text.clear()
        self.response_body_text.clear()
        
        if self.request_tabs.count() > 0: 
            self.request_tabs.setCurrentIndex(0) 
        self.tree_widget.setFocus()

    def on_body_type_changed(self, clicked_radio_button):
        content_type_to_set = None
        selected_body_type_text = clicked_radio_button.text()

        if selected_body_type_text == "Raw (JSON)": content_type_to_set = 'application/json; charset=utf-8'
        elif selected_body_type_text == "Raw (XML)": content_type_to_set = 'application/xml; charset=utf-8'
        elif selected_body_type_text == "Raw (Text)": content_type_to_set = 'text/plain; charset=utf-8'
        elif selected_body_type_text == "Form Data": content_type_to_set = None 
        elif selected_body_type_text == "x-www-form-urlencoded": content_type_to_set = 'application/x-www-form-urlencoded; charset=utf-8'
        elif selected_body_type_text == "Nenhum": content_type_to_set = None 

        current_headers_str = self.headers_text.toPlainText()
        headers_lines_list = current_headers_str.strip().split('\n') if current_headers_str.strip() else []
        new_headers_lines_list = []
        content_type_header_was_updated = False

        for line_str in headers_lines_list:
            if ':' in line_str:
                key_str, value_str = line_str.split(':', 1)
                if key_str.strip().lower() == 'content-type': 
                    if content_type_to_set: 
                        new_headers_lines_list.append(f'Content-Type: {content_type_to_set}')
                        content_type_header_was_updated = True
                else: 
                    new_headers_lines_list.append(line_str)
            else: 
                new_headers_lines_list.append(line_str)

        if not content_type_header_was_updated and content_type_to_set:
            new_headers_lines_list.append(f'Content-Type: {content_type_to_set}')
        
        self.headers_text.setPlainText('\n'.join(new_headers_lines_list))

    def on_environment_changed(self, selected_index_int):
        selected_env_name_str = self.environment_combo.itemText(selected_index_int) 
        print(f'Ambiente ativo na UI mudou para: {selected_env_name_str}')

    def import_collection(self):
        options = QFileDialog.Options()
        start_dir = self._get_data_path("") 
        if not os.path.exists(start_dir): start_dir = os.path.expanduser("~") 

        file_name_str, _ = QFileDialog.getOpenFileName(
            self, 
            "Importar Coleção de Requisições (Postman JSON)", 
            start_dir, 
            "Arquivos JSON (*.json);;Todos os Arquivos (*)", 
            options=options
        )
        if file_name_str:
            importer = Importer() 
            try:
                imported_collection_data_dict = importer.import_collection(file_name_str)
                self.collections.append(imported_collection_data_dict)
                
                imported_coll_name = imported_collection_data_dict.get('info',{}).get('name', 'Coleção Importada')
                QMessageBox.information(self, "Importação Concluída", 
                                        f"A coleção '{imported_coll_name}' foi importada com sucesso!")
                self.update_collections_view() 
                self.save_collections() 
            except Exception as e:
                QMessageBox.critical(self, "Erro na Importação da Coleção", 
                                     f"Ocorreu um erro ao tentar importar o arquivo da coleção:\n{type(e).__name__}: {e}")
                traceback.print_exc()

# Mantenha todos os outros métodos como estão.
# Apenas este método precisa ser substituído.

    def import_curl(self):
        # ### INÍCIO DA MODIFICAÇÃO ###
        # Substituímos o QInputDialog por um QDialog customizado
        # para usar o seu AccessiblePlainTextEdit e corrigir a navegação com Tab.
        dialog = QDialog(self)
        dialog.setWindowTitle('Importar Comando cURL')
        dialog.setModal(True)
        dialog.resize(500, 300) # Tamanho inicial um pouco maior

        layout = QVBoxLayout(dialog)
        
        label = QLabel('Cole o comando cURL completo aqui:')
        layout.addWidget(label)

        # Usamos a sua classe customizada que já lida com a navegação por Tab!
        curl_text_edit = AccessiblePlainTextEdit()
        curl_text_edit.setAccessibleName("Campo de texto para comando cURL")
        label.setBuddy(curl_text_edit)
        layout.addWidget(curl_text_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = button_box.button(QDialogButtonBox.Ok)
        if ok_button:
            ok_button.setText("Importar")
        cancel_button = button_box.button(QDialogButtonBox.Cancel)
        if cancel_button:
            cancel_button.setText("Cancelar")
            
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        curl_text_edit.setFocus()

        # Executa o diálogo e espera pelo resultado
        if not dialog.exec_() == QDialog.Accepted:
            return # Usuário cancelou
            
        curl_cmd_str = curl_text_edit.toPlainText().strip()
        if not curl_cmd_str:
            return # Texto vazio

        # ### FIM DA MODIFICAÇÃO ###
        # O restante da lógica permanece exatamente o mesmo.
        
        importer = Importer()
        try:
            imported_request_item_data = importer.import_curl(curl_cmd_str)
        except Exception as e:
            QMessageBox.critical(self, 'Erro ao Parsear cURL', 
                                 f'Falha ao interpretar o comando cURL fornecido:\n{type(e).__name__}: {e}')
            return

        if not self.collections:
            reply = QMessageBox.question(self, "Nenhuma Coleção Existente",
                                         "Não há coleções para adicionar a requisição importada. Deseja criar uma nova coleção agora?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                if not self.create_collection(prompt_name_str="Criar Coleção para Requisição cURL"):
                    QMessageBox.warning(self, "Importação Cancelada", 
                                        "A importação do cURL foi cancelada pois nenhuma coleção foi selecionada ou criada.")
                    return
            else: 
                QMessageBox.information(self, "Importação Cancelada", "A requisição cURL não foi importada.")
                return
        
        collection_names_list = [c.get('info', {}).get('name', f'Coleção Sem Nome {i+1}') for i, c in enumerate(self.collections)]
        
        chosen_collection_name_str, ok_bool = QInputDialog.getItem(
            self, 
            "Selecionar Coleção de Destino", 
            "Escolha a coleção onde a requisição cURL será salva:", 
            collection_names_list, 
            0, 
            False, 
            flags=Qt.WindowSystemMenuHint | Qt.WindowTitleHint 
        )
        
        if ok_bool and chosen_collection_name_str:
            chosen_collection_index = -1
            for idx, name in enumerate(collection_names_list):
                if name == chosen_collection_name_str:
                    chosen_collection_index = idx
                    break
            
            if chosen_collection_index != -1:
                self.collections[chosen_collection_index].setdefault('item', []).append(imported_request_item_data)
                self.update_collections_view() 
                self.save_collections() 
                QMessageBox.information(self, 'cURL Importado com Sucesso', 
                                        f"A requisição do cURL foi importada para a coleção '{chosen_collection_name_str}'.")
            else: 
                QMessageBox.warning(self, "Erro Interno", "Não foi possível encontrar a coleção selecionada.")
        else: 
            QMessageBox.information(self, "Importação Cancelada", "A requisição cURL não foi salva em nenhuma coleção.")

    def import_environment(self):
        options = QFileDialog.Options()
        start_dir = self._get_data_path("") 
        if not os.path.exists(start_dir): start_dir = os.path.expanduser("~")

        file_name_str, _ = QFileDialog.getOpenFileName(
            self, 
            "Importar Arquivo de Ambiente (Postman JSON)", 
            start_dir, 
            "Arquivos JSON (*.json);;Todos os Arquivos (*)", 
            options=options
        )
        if file_name_str:
            try:
                with open(file_name_str, 'r', encoding='utf-8') as file_in:
                    env_data_dict = json.load(file_in)
                
                environment_name_str = env_data_dict.get('name', f'AmbienteImportado_{uuid.uuid4().hex[:6]}')
                
                variables_dict_to_add = {
                    item_dict['key']: item_dict['value'] 
                    for item_dict in env_data_dict.get('values', []) 
                    if item_dict.get('enabled', True) and 'key' in item_dict and 'value' in item_dict
                }
                
                self.environments.add_environment(environment_name_str, variables_dict_to_add)
                QMessageBox.information(self, "Ambiente Importado", 
                                        f"O ambiente '{environment_name_str}' foi importado com sucesso!")
                self.update_environment_combo() 
                self.update_edit_environments_menu() 
                self.save_environments() 
            except Exception as e:
                QMessageBox.critical(self, "Erro na Importação de Ambiente", 
                                     f"Ocorreu um erro ao tentar importar o arquivo de ambiente:\n{type(e).__name__}: {e}")
                traceback.print_exc()

    def display_request_details(self, request_id_from_tree_item_data):
        if self.current_request_data: 
            self.update_current_request_data_from_ui()

        self.current_request_data = self.request_mapping.get(request_id_from_tree_item_data)

        if self.current_request_data:
            self.execute_button.setEnabled(True)
            request_details_dict = self.current_request_data.get('request', {}) 

            method_str = request_details_dict.get('method', 'GET').upper()
            self.method_type_group.setExclusive(False) 
            for m_name, radio_btn in self.method_radios.items():
                radio_btn.setChecked(m_name == method_str)
            self.method_type_group.setExclusive(True) 

            url_data_obj = request_details_dict.get('url', {}) 
            raw_url_str = url_data_obj.get('raw', '') if isinstance(url_data_obj, dict) else str(url_data_obj)
            self.url_line_edit.setText(raw_url_str)
            self.url_line_edit.setStatusTip(f"URL: {raw_url_str}" if raw_url_str else "URL da requisição não definida.")

            headers_list_of_dicts = request_details_dict.get('header', [])
            headers_display_str = '\n'.join(
                f"{h.get('key','')}: {h.get('value','')}" for h in headers_list_of_dicts
            )
            self.headers_text.setPlainText(headers_display_str)
            
            auth_data_dict = request_details_dict.get('auth') 
            auth_display_str = json.dumps(auth_data_dict, indent=2, ensure_ascii=False) if auth_data_dict else ""
            self.auth_text.setPlainText(auth_display_str)

            body_config_dict = request_details_dict.get('body', {})
            body_mode_str = body_config_dict.get('mode')
            body_content_display_str = ""
            
            self.body_type_group.setExclusive(False) 
            for radio_btn in self.body_type_radios.values(): radio_btn.setChecked(False)

            selected_radio_text_for_body = "Nenhum" 
            if body_mode_str == 'raw':
                body_content_display_str = body_config_dict.get('raw', '')
                current_content_type = ""
                for h_obj in headers_list_of_dicts: 
                    if h_obj.get('key','').lower() == 'content-type':
                        current_content_type = h_obj.get('value','').lower()
                        break
                if 'json' in current_content_type: selected_radio_text_for_body = "Raw (JSON)"
                elif 'xml' in current_content_type: selected_radio_text_for_body = "Raw (XML)"
                else: selected_radio_text_for_body = "Raw (Text)" 
            
            elif body_mode_str == 'formdata':
                selected_radio_text_for_body = "Form Data"
                formdata_list = body_config_dict.get('formdata',[])
                body_content_display_str = '\n'.join(
                    f"{fd_item.get('key','')}= {fd_item.get('value','')}" for fd_item in formdata_list
                )
            elif body_mode_str == 'urlencoded':
                selected_radio_text_for_body = "x-www-form-urlencoded"
                urlencoded_list = body_config_dict.get('urlencoded',[])
                body_content_display_str = '\n'.join(
                    f"{ue_item.get('key','')}= {ue_item.get('value','')}" for ue_item in urlencoded_list
                )
            
            if selected_radio_text_for_body in self.body_type_radios: 
                self.body_type_radios[selected_radio_text_for_body].setChecked(True)
            else: 
                self.body_type_radios["Nenhum"].setChecked(True)

            self.body_text.setPlainText(body_content_display_str)
            self.body_type_group.setExclusive(True) 

            events_list_of_dicts = self.current_request_data.get('event', [])
            self.pre_request_script_text.clear()
            self.test_script_text.clear()
            for event_item_dict in events_list_of_dicts:
                script_exec_list = event_item_dict.get('script', {}).get('exec', [])
                script_display_content_str = "\n".join(script_exec_list) 
                
                if event_item_dict.get('listen') == 'prerequest':
                    self.pre_request_script_text.setPlainText(script_display_content_str)
                elif event_item_dict.get('listen') == 'test':
                    self.test_script_text.setPlainText(script_display_content_str)
        else: 
            self.clear_request_details()

    def update_current_request_data_from_ui(self):
        if not self.current_request_data:
            return

        request_details_dict = self.current_request_data.setdefault('request', {})

        checked_method_radio_btn = self.method_type_group.checkedButton()
        request_details_dict['method'] = checked_method_radio_btn.text() if checked_method_radio_btn else "GET"

        url_input_str = self.url_line_edit.text().strip()
        request_details_dict['url'] = {'raw': url_input_str} 

        headers_list_of_dicts = []
        headers_input_str = self.headers_text.toPlainText().strip()
        if headers_input_str: 
            for line_str in headers_input_str.split('\n'):
                if ':' in line_str: 
                    key_str, val_str = line_str.split(':', 1)
                    headers_list_of_dicts.append({'key': key_str.strip(), 'value': val_str.strip()})
        request_details_dict['header'] = headers_list_of_dicts
        
        auth_input_str = self.auth_text.toPlainText().strip()
        if auth_input_str:
            try:
                request_details_dict['auth'] = json.loads(auth_input_str) 
            except json.JSONDecodeError:
                print(f"Aviso: Conteúdo de autenticação não é JSON válido: {auth_input_str}")
                request_details_dict.pop('auth', None) 
        else: 
            request_details_dict.pop('auth', None)

        body_config_to_save = {} 
        checked_body_radio_btn = self.body_type_group.checkedButton()
        body_content_input_str = self.body_text.toPlainText() 

        if checked_body_radio_btn:
            radio_btn_text = checked_body_radio_btn.text()
            if radio_btn_text in ["Raw (JSON)", "Raw (XML)", "Raw (Text)"]:
                body_config_to_save['mode'] = 'raw'
                body_config_to_save['raw'] = body_content_input_str
            elif radio_btn_text == "Form Data":
                body_config_to_save['mode'] = 'formdata'
                formdata_list = []
                if body_content_input_str.strip(): 
                    for line_str in body_content_input_str.strip().split('\n'):
                        if '=' in line_str:
                            key_str, val_str = line_str.split('=', 1)
                            formdata_list.append({'key': key_str.strip(), 'value': val_str.strip(), 'type': 'text'})
                body_config_to_save['formdata'] = formdata_list
            elif radio_btn_text == "x-www-form-urlencoded":
                body_config_to_save['mode'] = 'urlencoded'
                urlencoded_list = []
                if body_content_input_str.strip(): 
                    for line_str in body_content_input_str.strip().split('\n'):
                        if '=' in line_str:
                            key_str, val_str = line_str.split('=', 1)
                            urlencoded_list.append({'key': key_str.strip(), 'value': val_str.strip()})
                body_config_to_save['urlencoded'] = urlencoded_list
            elif radio_btn_text == "Nenhum":
                body_config_to_save['mode'] = 'none' 

        request_details_dict['body'] = body_config_to_save

        events_list_to_save = []
        pre_request_script_str = self.pre_request_script_text.toPlainText() 
        if pre_request_script_str.strip(): 
            events_list_to_save.append({
                "listen": "prerequest", 
                "script": {"type": "text/python", "exec": [pre_request_script_str]}
            })
        
        test_script_str = self.test_script_text.toPlainText()
        if test_script_str.strip():
            events_list_to_save.append({
                "listen": "test", 
                "script": {"type": "text/python", "exec": [test_script_str]}
            })
        self.current_request_data['event'] = events_list_to_save

    def execute_request(self):
        if not self.current_request_data:
            QMessageBox.warning(self, "Atenção", "Nenhuma requisição selecionada para executar.")
            return

        self.update_current_request_data_from_ui() 
        
        self.status_code_text.clear()
        self.response_headers_text.clear()
        self.response_body_text.clear()

        executor = Executor(self.environments) 
        
        selected_env_name_str = self.environment_combo.currentText()
        if selected_env_name_str == 'Nenhum': 
            selected_env_name_str = None
            
        verify_ssl_bool = not self.disable_ssl_checkbox.isChecked()

        try:
            response_obj_from_requests = executor.execute_request_with_scripts(
                self.current_request_data, 
                selected_env_name_str, 
                verify_ssl_bool
            )
            self.show_response(response_obj_from_requests) 
            
            self.update_environment_combo() 
            self.update_edit_environments_menu()

        except Exception as e: 
            self.status_code_text.setPlainText(f"Erro na Execução: {type(e).__name__}")
            self.response_body_text.setPlainText(f"Detalhes do Erro:\n{str(e)}\n\nConsulte o console da aplicação para o traceback completo.")
            QMessageBox.critical(self, "Erro na Execução da Requisição", 
                                 f"Falha ao executar requisição ou scripts Python:\n{type(e).__name__}: {e}")
            traceback.print_exc() 

    def show_response(self, response_obj): 
        try:
            response_size_bytes = len(response_obj.content) if response_obj and hasattr(response_obj, 'content') else 0
            response_size_kb = response_size_bytes / 1024
            
            status_line = f"Status: {response_obj.status_code} {response_obj.reason}"
            if hasattr(response_obj, 'elapsed') and response_obj.elapsed:
                status_line += f"  |  Tempo: {response_obj.elapsed.total_seconds() * 1000:.0f} ms"
            status_line += f"  |  Tamanho: {response_size_kb:.2f} KB"

            self.status_code_text.setPlainText(status_line)
            
            headers_str = '\n'.join(f"{k}: {v}" for k, v in response_obj.headers.items())
            self.response_headers_text.setPlainText(headers_str)
            
            try:
                content_type = response_obj.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    try:
                        json_data = response_obj.json() 
                        self.response_body_text.setPlainText(json.dumps(json_data, indent=2, ensure_ascii=False))
                    except json.JSONDecodeError: # Removido requests.exceptions.JSONDecodeError
                        self.response_body_text.setPlainText(response_obj.text + "\n\n(Aviso: Resposta indica JSON, mas falhou ao decodificar)")
                elif 'text/html' in content_type or 'application/xml' in content_type or 'text/plain' in content_type:
                    self.response_body_text.setPlainText(response_obj.text)
                else: 
                    if response_size_bytes > 0 and response_size_bytes < 1024 * 1024: 
                        try:
                            self.response_body_text.setPlainText(response_obj.text)
                        except Exception:
                            self.response_body_text.setPlainText(f"(Conteúdo binário ou não decodificável de {response_size_kb:.2f} KB)")
                    elif response_size_bytes > 0 :
                        self.response_body_text.setPlainText(f"(Conteúdo binário de {response_size_kb:.2f} KB. Visualização não disponível)")
                    else:
                        self.response_body_text.setPlainText("(Resposta sem corpo ou corpo vazio)")

            except Exception as display_err: 
                self.response_body_text.setPlainText(f"Erro ao processar corpo da resposta: {display_err}\n\nRaw text (se disponível):\n{response_obj.text[:1000]}") 
            
            self.response_tabs.setCurrentIndex(0) 
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Exibir Resposta", 
                                 f"Ocorreu um erro ao tentar exibir a resposta:\n{str(e)}")
            traceback.print_exc()

    # ### MODIFICADO ### - Atualizado para incluir a opção "Copiar como cURL"
    def on_tree_item_context_menu(self, global_position_to_show_menu: QPoint):
        tree_item_widget_at_pos = self.tree_widget.itemAt(self.tree_widget.viewport().mapFromGlobal(global_position_to_show_menu))
        
        if not tree_item_widget_at_pos:
            return

        item_role_data = tree_item_widget_at_pos.data(0, Qt.UserRole)
        if not item_role_data: 
            return
            
        item_type_str = item_role_data.get('type')
        # Limpa o prefixo para obter o nome real
        item_name_str = tree_item_widget_at_pos.text(0)
        if ': ' in item_name_str:
            item_name_str = item_name_str.split(': ', 1)[1]

        context_menu = QMenu(self)
        context_menu.setAccessibleName(f"Menu de contexto para {item_type_str} {item_name_str}")
        context_menu.setTitle(f"Opções para {item_type_str} '{item_name_str}'")

        if item_type_str in ['request', 'folder', 'collection']:
            rename_action = QAction(f'Renomear {item_type_str.capitalize()}...', self) 
            rename_action.setToolTip(f"Altera o nome de '{item_name_str}'.")
            rename_action.triggered.connect(lambda checked, iw=tree_item_widget_at_pos: self._rename_item(iw))
            context_menu.addAction(rename_action)
        
        if item_type_str == 'request':
            context_menu.addSeparator()
            copy_curl_action = QAction(f'Copiar como cURL', self)
            copy_curl_action.setToolTip(f"Copia o comando cURL para esta requisição para a área de transferência.")
            # Conecta a nova ação ao novo método handler
            copy_curl_action.triggered.connect(lambda checked, iw=tree_item_widget_at_pos: self._copy_curl_for_item(iw))
            context_menu.addAction(copy_curl_action)

        if item_type_str == 'collection' or item_type_str == 'folder':
            context_menu.addSeparator()
            new_folder_action = QAction(f'Nova Pasta aqui...', self)
            new_folder_action.setToolTip(f"Criar uma nova pasta dentro de '{item_name_str}'.")
            new_folder_action.triggered.connect(lambda checked, iw=tree_item_widget_at_pos: self._new_folder_or_request(iw, 'folder'))
            context_menu.addAction(new_folder_action)
            
            new_request_action = QAction(f'Nova Requisição aqui...', self)
            new_request_action.setToolTip(f"Criar uma nova requisição dentro de '{item_name_str}'.")
            new_request_action.triggered.connect(lambda checked, iw=tree_item_widget_at_pos: self._new_folder_or_request(iw, 'request'))
            context_menu.addAction(new_request_action)

        if item_type_str in ['request', 'folder', 'collection']:
            # Adiciona separador apenas se já houver ações e a última não for separador
            actions = context_menu.actions()
            if actions and not actions[-1].isSeparator():
                context_menu.addSeparator() 
            delete_action = QAction(f'Excluir {item_type_str.capitalize()} "{item_name_str}"', self)
            delete_action.setToolTip(f"Remove '{item_name_str}' permanentemente.")
            delete_action.triggered.connect(lambda checked, iw=tree_item_widget_at_pos: self._delete_item(iw))
            context_menu.addAction(delete_action)
        
        if context_menu.actions(): 
            context_menu.exec_(global_position_to_show_menu)
            
    ### NOVO ### - Função para gerar o comando cURL a partir dos dados da requisição
    def _generate_curl_command(self, request_item_data):
        """Gera uma string de comando cURL a partir de um dicionário de requisição."""
        if not request_item_data or 'request' not in request_item_data:
            return "# Requisição inválida"

        request = request_item_data['request']
        parts = ['curl']

        # URL
        url_data = request.get('url', {})
        url = url_data.get('raw', '') if isinstance(url_data, dict) else str(url_data)
        if url:
            parts.append(shlex.quote(url))

        # Método
        method = request.get('method', 'GET').upper()
        if method != 'GET':
            parts.append(f'-X {method}')

        # Headers
        for header in request.get('header', []):
            parts.append(f"-H {shlex.quote(f'{header.get("key")}: {header.get("value")}')}")

        # Body
        body_config = request.get('body', {})
        body_mode = body_config.get('mode')

        if body_mode == 'raw':
            raw_data = body_config.get('raw', '')
            if raw_data:
                parts.append(f"--data-raw {shlex.quote(raw_data)}")
        
        elif body_mode == 'urlencoded':
            urlencoded_params = body_config.get('urlencoded', [])
            if urlencoded_params:
                data_str = '&'.join([f"{item.get('key')}={item.get('value')}" for item in urlencoded_params])
                parts.append(f"--data {shlex.quote(data_str)}")

        elif body_mode == 'formdata':
             for item in body_config.get('formdata', []):
                parts.append(f"-F {shlex.quote(f'{item.get("key")}={item.get("value")}')}")
        
        # Auth (apenas basic implementado como exemplo)
        auth = request.get('auth')
        if auth and auth.get('type') == 'basic':
            user = ''
            password = ''
            for item in auth.get('basic', []):
                if item.get('key') == 'username':
                    user = item.get('value', '')
                elif item.get('key') == 'password':
                    password = item.get('value', '')
            parts.append(f"-u {shlex.quote(f'{user}:{password}')}")

        # Adiciona '--compressed' para simular o comportamento padrão de muitos clientes
        parts.append('--compressed')
        
        # Junta tudo com quebras de linha para melhor legibilidade
        return ' \\\n  '.join(parts)

    ### NOVO ### - Função para copiar o cURL para a área de transferência
    def _copy_curl_for_item(self, tree_item_widget):
        """Pega os dados do item, gera o cURL e o copia."""
        item_data = tree_item_widget.data(0, Qt.UserRole)
        if not item_data or 'object_ref' not in item_data:
            QMessageBox.warning(self, "Erro", "Não foi possível obter os dados da requisição.")
            return

        # Busca os dados mais recentes da UI antes de gerar o cURL
        self.update_current_request_data_from_ui()

        # Usa o 'object_ref' que é a referência direta ao dicionário na estrutura de dados
        request_item_object = item_data['object_ref']
        
        # Gera o comando
        curl_command = self._generate_curl_command(request_item_object)

        # Copia para a área de transferência
        clipboard = QApplication.clipboard()
        clipboard.setText(curl_command)

        # Notifica o usuário
        self.statusBar().showMessage("Comando cURL copiado para a área de transferência!", 4000) # Mostra por 4 segundos
        QMessageBox.information(self, "Copiado!", "O comando cURL foi copiado para a sua área de transferência.")


    def _new_folder_or_request(self, parent_tree_item_widget, type_to_create_str):
        parent_item_role_data = parent_tree_item_widget.data(0, Qt.UserRole)
        parent_item_path = parent_item_role_data.get('path')
        parent_item_object_in_collection = self._get_item_from_path(parent_item_path)

        if not parent_item_object_in_collection or \
           not (parent_item_role_data.get('type') == 'collection' or \
                (parent_item_role_data.get('type') == 'folder' and 'item' in parent_item_object_in_collection)):
            if parent_item_role_data.get('type') == 'collection' and 'item' not in parent_item_object_in_collection:
                parent_item_object_in_collection['item'] = [] 
            else: 
                QMessageBox.warning(self, "Operação Inválida", 
                                    f"Não é possível adicionar um(a) '{type_to_create_str}' dentro de um item do tipo '{parent_item_role_data.get('type')}'.")
                return

        name_prompt_str = f"Digite o nome para o novo {type_to_create_str.lower()}:"
        dialog_title_str = f"Criar Novo(a) {type_to_create_str.capitalize()}"
        
        new_item_name_str, ok_bool = QInputDialog.getText(
            self, dialog_title_str, name_prompt_str, flags=Qt.WindowSystemMenuHint | Qt.WindowTitleHint
        )
        
        if ok_bool and new_item_name_str.strip():
            new_item_name_stripped = new_item_name_str.strip()
            new_item_data_dict = {'name': new_item_name_stripped}
            if type_to_create_str == 'folder':
                new_item_data_dict['item'] = [] 
            else: 
                new_item_data_dict['request'] = {
                    'method': 'GET', 'url': {'raw': ''}, 'header': [], 'body': {'mode':'none'}
                }
                new_item_data_dict['event'] = [] 
            
            parent_item_object_in_collection.setdefault('item', []).append(new_item_data_dict)
            
            # --- LÓGICA CORRIGIDA ---
            self.update_collections_view() 
            
            new_parent_widget = self.item_path_map.get(tuple(parent_item_path))

            if new_parent_widget:
                new_parent_widget.setExpanded(True)
            
            new_item_index = len(parent_item_object_in_collection['item']) - 1
            new_item_path = parent_item_path + ['item', new_item_index]
            newly_created_widget = self.item_path_map.get(tuple(new_item_path))
            if newly_created_widget:
                self.tree_widget.setCurrentItem(newly_created_widget)
            
            self.save_collections() 
            QMessageBox.information(self, "Item Criado", 
                                    f"{type_to_create_str.capitalize()} '{new_item_name_stripped}' criado(a) com sucesso.")
        elif ok_bool and not new_item_name_str.strip():
            QMessageBox.warning(self, "Nome Inválido", f"O nome para o novo {type_to_create_str} não pode ser vazio.")

    def _delete_item(self, tree_item_widget_to_delete):
        item_role_data = tree_item_widget_to_delete.data(0, Qt.UserRole)
        item_path_list = item_role_data.get('path')
        item_type_str = item_role_data.get('type')
        item_name_str = tree_item_widget_to_delete.text(0) 

        confirm_reply = QMessageBox.question(
            self, 
            f'Confirmar Exclusão de {item_type_str.capitalize()}', 
            f"Tem certeza que deseja excluir o item '{item_name_str}' ({item_type_str})?\n"
            f"Esta ação não pode ser desfeita. Se for uma coleção ou pasta, todo o seu conteúdo também será excluído.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No 
        )
        
        if confirm_reply == QMessageBox.No:
            return 

        item_successfully_removed_from_data = False
        py_id_of_item_to_delete = item_role_data.get('id')

        if len(item_path_list) == 1 and item_type_str == 'collection': 
            collection_index_to_remove = item_path_list[0]
            obj_to_delete = self.collections[collection_index_to_remove]
            if self.current_request_data is obj_to_delete:
                self.clear_request_details() 
            
            del self.collections[collection_index_to_remove]
            item_successfully_removed_from_data = True
        
        elif len(item_path_list) > 1: 
            parent_list_path = item_path_list[:-1] 
            item_index_in_parent_list = item_path_list[-1]
            parent_list_object = self._get_item_from_path(parent_list_path)
            
            if parent_list_object and isinstance(parent_list_object, list) and \
               0 <= item_index_in_parent_list < len(parent_list_object):
                
                item_object_to_delete = parent_list_object[item_index_in_parent_list]
                if self.current_request_data is item_object_to_delete:
                    self.clear_request_details()
                
                del parent_list_object[item_index_in_parent_list]
                item_successfully_removed_from_data = True
            else:
                QMessageBox.warning(self, "Erro Interno ao Excluir", "Não foi possível encontrar o item pai nos dados para realizar a exclusão.")
        
        if item_successfully_removed_from_data:
            if py_id_of_item_to_delete in self.request_mapping:
                del self.request_mapping[py_id_of_item_to_delete]

            self.update_collections_view() 
            self.save_collections() 
            QMessageBox.information(self, "Item Excluído", f"{item_type_str.capitalize()} '{item_name_str}' foi excluído(a).")
            
    def _rename_item(self, item_widget):
        item_data = item_widget.data(0, Qt.UserRole)
        item_path = item_data.get('path')
        item_obj = self._get_item_from_path(item_path)

        if not item_obj:
            QMessageBox.warning(self, "Erro", "Não foi possível encontrar o item para renomear.")
            return

        current_name = item_obj.get('name', '')
        item_type = item_data.get('type', 'item')

        new_name, ok = QInputDialog.getText(self, f"Renomear {item_type.capitalize()}", "Novo nome:", text=current_name)

        if ok and new_name.strip():
            item_obj['name'] = new_name.strip()
            self.update_collections_view()
            self.save_collections()
        elif ok:
            QMessageBox.warning(self, "Nome Inválido", "O nome não pode ser vazio.")

    def generate_evidence_pdf(self):
        if not self.current_request_data or 'request' not in self.current_request_data:
            QMessageBox.warning(self, "Aviso para Gerar PDF", 
                                "Nenhuma requisição está selecionada ou os dados da requisição estão incompletos para gerar o PDF.")
            return
        
        req_details = self.current_request_data['request']
        req_name = self.current_request_data.get('name', 'Requisição Sem Nome')
        method = req_details.get('method', 'N/A')
        url_data = req_details.get('url', {})
        url = url_data.get('raw', 'N/A') if isinstance(url_data, dict) else str(url_data)
        
        status_resp = self.status_code_text.toPlainText()
        headers_resp = self.response_headers_text.toPlainText()
        body_resp = self.response_body_text.toPlainText()
        
        file_dialog = QFileDialog(self)
        file_dialog.setAcceptMode(QFileDialog.AcceptSave)
        file_dialog.setNameFilter("Arquivos PDF (*.pdf)")
        file_dialog.setDefaultSuffix("pdf")
        file_dialog.setWindowTitle("Salvar Evidência em PDF")
        
        default_filename = f"evidencia_{req_name.replace(' ', '_').replace('/','-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # ### CORREÇÃO 1: Usar caminho absoluto para evitar o aviso no Windows ###
        data_dir = os.path.abspath(self._get_data_path("")) 
        file_dialog.setDirectory(data_dir) 
        file_dialog.selectFile(default_filename)

        if file_dialog.exec_():
            save_path = file_dialog.selectedFiles()[0]
            try:
                c = canvas.Canvas(save_path, pagesize=A4)
                styles = getSampleStyleSheet()
                style_normal = styles['Normal']
                style_heading = styles['h2']
                style_subheading = styles['h3']
                width, height = A4
                margin = 40

                # ### MELHORIA: Estilo de código com quebra de linha forçada para palavras longas ###
                from reportlab.lib.styles import ParagraphStyle
                style_code_wrap = ParagraphStyle(
                    name='CodeWrap',
                    parent=styles['Code'],
                    wordWrap='CJK'  # Permite quebrar linhas em qualquer lugar de uma palavra longa
                )

                current_y = height - margin

                def add_paragraph_with_break_check(text_content, style_obj, max_width_val, spacing_after=10):
                    nonlocal current_y
                    # Escapa caracteres HTML para evitar erros de formatação no Paragraph
                    from html import escape
                    escaped_text = escape(text_content)
                    
                    # Usa a tag <pre> para preservar espaços em branco em estilos de código
                    if style_obj.name in ('Code', 'CodeWrap'):
                        p = Paragraph(f'<pre>{escaped_text}</pre>', style_obj)
                    else:
                        p = Paragraph(escaped_text.replace('\n', '<br/>\n'), style_obj)
                    
                    p_w, p_h = p.wrapOn(c, max_width_val, height) 
                    if current_y - p_h < margin: 
                        c.showPage()
                        current_y = height - margin
                        c.setFont("Helvetica", 8)
                        c.drawString(margin, margin - 20, f"Página {c.getPageNumber()} - Continuação Evidência: {req_name}")

                    p.drawOn(c, margin, current_y - p_h)
                    current_y -= (p_h + spacing_after)

                # --- Geração do Conteúdo do PDF (usando o novo estilo) ---
                add_paragraph_with_break_check(f"Evidência da Requisição: {req_name}", style_heading, width - 2 * margin, 5)
                add_paragraph_with_break_check(f"Data de Geração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", style_normal, width - 2 * margin, 20)
                
                current_y -= 15
                c.line(margin, current_y, width - margin, current_y)
                current_y -= 20

                add_paragraph_with_break_check(f"Detalhes da Requisição", style_subheading, width - 2 * margin, 5)
                add_paragraph_with_break_check(f"Método: {method}", style_normal, width - 2 * margin)
                add_paragraph_with_break_check(f"URL: {url}", style_code_wrap, width - 2 * margin) # Usando o novo estilo
                
                req_headers_str = "\n".join([f"{h.get('key')}: {h.get('value')}" for h in req_details.get('header', [])])
                if req_headers_str:
                    add_paragraph_with_break_check(f"Cabeçalhos da Requisição:\n{req_headers_str}", style_code_wrap, width - 2 * margin)

                # ... (Lógica para corpo da requisição) ...
                req_body_conf = req_details.get('body', {})
                req_body_mode = req_body_conf.get('mode', 'none')
                req_body_content = ""
                if req_body_mode == 'raw': req_body_content = req_body_conf.get('raw', '')
                elif req_body_mode == 'formdata': req_body_content = "\n".join([f"{fd.get('key')}: {fd.get('value')}" for fd in req_body_conf.get('formdata', [])])
                elif req_body_mode == 'urlencoded': req_body_content = "\n".join([f"{ue.get('key')}: {ue.get('value')}" for ue in req_body_conf.get('urlencoded', [])])
                
                if req_body_content:
                    add_paragraph_with_break_check(f"Corpo da Requisição ({req_body_mode}):", style_normal, width - 2*margin, 5)
                    add_paragraph_with_break_check(req_body_content, style_code_wrap, width - 2 * margin)


                current_y -= 10
                c.line(margin, current_y, width - margin, current_y)
                current_y -= 15
                add_paragraph_with_break_check(f"Detalhes da Resposta", style_subheading, width - 2 * margin, 5)
                add_paragraph_with_break_check(f"{status_resp}", style_normal, width - 2 * margin)
                if headers_resp.strip():
                    add_paragraph_with_break_check(f"Cabeçalhos da Resposta:", style_normal, width - 2 * margin, 5)
                    add_paragraph_with_break_check(headers_resp, style_code_wrap, width - 2 * margin)
                if body_resp.strip():
                    add_paragraph_with_break_check(f"Corpo da Resposta:", style_normal, width - 2*margin, 5)
                    add_paragraph_with_break_check(body_resp, style_code_wrap, width - 2 * margin)

                c.save()
                QMessageBox.information(self, "PDF Gerado com Sucesso", f"O arquivo de evidência foi salvo em:\n{save_path}")
            except Exception as pdf_err:
                QMessageBox.critical(self, "Erro ao Gerar PDF", f"Não foi possível gerar o arquivo PDF:\n{type(pdf_err).__name__}: {pdf_err}")
                traceback.print_exc()
        else:
            QMessageBox.information(self, "Geração de PDF Cancelada", "A geração do arquivo PDF foi cancelada pelo usuário.")

    def closeEvent(self, event_close): 
        if self.current_request_data:
            self.update_current_request_data_from_ui()
        
        self.save_collections()
        self.save_environments()
        event_close.accept()

    def eventFilter(self, source_obj, event_obj: QKeyEvent): 
        if source_obj == self.tree_widget and event_obj.type() == QKeyEvent.KeyPress:
            if event_obj.key() == Qt.Key_Menu or \
               (event_obj.key() == Qt.Key_F10 and event_obj.modifiers() & Qt.ShiftModifier):
                
                selected_tree_items = self.tree_widget.selectedItems()
                if selected_tree_items:
                    tree_item_widget = selected_tree_items[0]
                    item_visual_rect = self.tree_widget.visualItemRect(tree_item_widget)
                    
                    viewport_pos = item_visual_rect.center()
                    if not self.tree_widget.viewport().rect().contains(viewport_pos):
                        viewport_pos = item_visual_rect.topLeft()
                        viewport_pos.setY(viewport_pos.y() + tree_item_widget.font(0).pointSize()) 
                    
                    global_pos_for_menu = self.tree_widget.viewport().mapToGlobal(viewport_pos)
                    
                    self.on_tree_item_context_menu(global_pos_for_menu) 
                    return True 
        return super().eventFilter(source_obj, event_obj) 

    def _get_item_from_path(self, path_list_keys_indices): # Restaurado
        current_level_data = self.collections 
        try:
            for step_key_or_index in path_list_keys_indices:
                current_level_data = current_level_data[step_key_or_index]
            return current_level_data 
        except (IndexError, KeyError, TypeError) as e:
            print(f"Erro ao navegar pelo caminho {path_list_keys_indices}: {e}")
            return None

    def _move_request(self, request_item_widget): # Restaurado (placeholder, precisa de implementação)
        QMessageBox.information(self, "Mover Requisição", "Funcionalidade de mover requisição ainda não implementada.")
        data = request_item_widget.data(0, Qt.UserRole)
        if not data or data.get('type') != 'request':
            QMessageBox.warning(self, "Atenção", "Item selecionado não é uma requisição válida.")
            return
        # Lógica para mover a requisição (complexa, envolve reestruturar self.collections)
        print(f"Mover requisição: {data.get('id')}")
        # Você precisará:
        # 1. Obter o objeto da requisição usando data['path'] ou data['id'] (via self.request_mapping).
        # 2. Remover a requisição de sua lista 'item' atual.
        # 3. Apresentar um diálogo para o usuário escolher a nova coleção/pasta de destino.
        # 4. Adicionar a requisição à lista 'item' do destino.
        # 5. Chamar self.update_collections_view() e self.save_collections().


# --- Ponto de Entrada ---
if __name__ == '__main__':
    QApplication.setApplicationName("Ferramenta de Requisições HTTP")
    QApplication.setApplicationVersion("1.2.5") # Atualizado

    app = QApplication(sys.argv)
    
    main_window = MainWindow()
    main_window.showMaximized() 
    sys.exit(app.exec_())