from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

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
        self.import_environment_action.triggered.connect(self.import_environment)
        self.import_environment_action.setToolTip('Importar um ambiente do Postman')
        self.import_environment_action.setStatusTip('Importar um ambiente do Postman')