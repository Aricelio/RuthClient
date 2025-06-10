import os
import json
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QMessageBox, QFileDialog
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

    # Função para importar um ambiente do Postman
    def import_environment(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Importar Ambiente", "", "JSON Files (*.json);;All Files (*)", options=options
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    env_data = json.load(f)
                
                # Verifica se é um arquivo de ambiente do Postman
                if 'name' in env_data and 'values' in env_data:
                    env_name = env_data['name']
                    variables = {}
                    
                    # Extrai as variáveis do arquivo
                    for val in env_data['values']:
                        if 'key' in val and 'value' in val and val.get('enabled', True):
                            variables[val['key']] = val['value']
                    
                    # Adiciona o ambiente ao gerenciador
                    self.environments.environments[env_name] = variables
                    
                    # Atualiza o combo box e salva em arquivo
                    self.update_environment_combo()
                    self.update_edit_environments_menu()
                    EnvironmentRepository.save(self, os)
                    
                    QMessageBox.information(self, "Sucesso", f"Ambiente '{env_name}' importado com sucesso!")
                else:
                    QMessageBox.critical(self, "Erro", "O arquivo não parece ser um ambiente válido do Postman.")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha ao importar o ambiente:\n{e}")

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