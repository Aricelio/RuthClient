import json
from PyQt5.QtWidgets import QMessageBox

# Classe CollectionEntity
# Responsável por carregar e gerenciar as coleções de arquivos
class CollectionRepository:

    # Função para carregar as coleções de arquivo
    def load(self, os):
        data_dir = 'data'
        collections_file = os.path.join(data_dir, 'collections.json')
        if os.path.exists(collections_file):
            try:
                with open(collections_file, 'r', encoding='utf-8') as f:
                    self.collections = json.load(f)
            except Exception as e:
                QMessageBox.warning(self, "Aviso", f"Falha ao carregar as coleções:\n{e}")

    # Função para salvar as coleções em arquivo
    def save(self, os):
        data_dir = 'data'
        os.makedirs(data_dir, exist_ok=True)
        collections_file = os.path.join(data_dir, 'collections.json')
        try:
            with open(collections_file, 'w', encoding='utf-8') as f:
                json.dump(self.collections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Aviso", f"Falha ao salvar as coleções:\n{e}")