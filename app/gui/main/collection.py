import os
from core.importer import Importer
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from data.collection import CollectionRepository

class Collection:

    # Função para importar uma coleção do Postman
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

    # Função para criar uma nova coleção vazia
    def create_collection(self):
        name, ok = QInputDialog.getText(self, 'Nova Coleção', 'Nome da nova coleção:')

        if not ok or not name.strip():
            return
        
        new_coll = {'info': {'name': name.strip()}, 'item': []}
        self.collections.append(new_coll)
        self.update_collections_view()

        CollectionRepository.save(self, os)
        
        QMessageBox.information(self, 'Sucesso', f'Coleção "{name}" criada.')