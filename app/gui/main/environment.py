import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QMessageBox
from data.environment import EnvironmentRepository

class Environment:

    # Função para exibir o diálogo de edição de um ambiente específico
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
        save_button.clicked.connect(lambda: Environment.save_environment_changes(self, environment_name, env_text.toPlainText(), dialog))
        layout.addWidget(save_button)

        dialog.exec_()

    # Função para salvar as alterações feitas em um ambiente
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
        EnvironmentRepository.save(self, os)
        
        # Atualiza o combo box e o menu de edição
        self.update_environment_combo()
        self.update_edit_environments_menu()
        
        # Fecha o diálogo
        dialog.accept()
        QMessageBox.information(self, 'Sucesso', f'Ambiente "{environment_name}" atualizado com sucesso!')    