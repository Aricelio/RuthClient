import json
from PyQt5.QtWidgets import QMessageBox

# Classe para armazenar os ambientes
class EnvironmentRepository:

    # Função para carregar os ambientes de arquivo
    def load(self, os):
        data_dir = 'data'
        environments_file = os.path.join(data_dir, 'environments.json')
        if os.path.exists(environments_file):
            try:
                with open(environments_file, 'r', encoding='utf-8') as f:
                    self.environments.environments = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Aviso", f"Falha ao carregar os ambientes:\n{e}")

    # Função para salvar os ambientes em arquivo
    def save(self, os):
        data_dir = 'data'
        os.makedirs(data_dir, exist_ok=True)
        environments_file = os.path.join(data_dir, 'environments.json')
        try:
            with open(environments_file, 'w', encoding='utf-8') as f:
                json.dump(self.environments.environments, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Falha ao salvar os ambientes:\n{e}")