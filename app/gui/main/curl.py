from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox, QMessageBox, QComboBox, QFormLayout, QLineEdit
from PyQt5.QtCore import Qt
from core.importer import Importer
import json

class Curl:
    
    # Função para importar uma requisição a partir de um comando cURL
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

            # Adicionar verificação para o índice da coleção
            if not self.collections:
                QMessageBox.warning(self, 'Nenhuma Coleção', 'Não há coleções disponíveis para adicionar a requisição.')
                return
            if idx < 0 or idx >= len(self.collections):
                QMessageBox.critical(self, 'Erro de Índice', f'Índice de coleção inválido: {idx}')
                return

            collection = self.collections[idx]
            collection.setdefault('item', []).append(request_item)

            # Limpamos a seleção anterior para não sobrescrever nada
            self.current_request_data = None

            # Agora redesenha toda a árvore com o item recém-adicionado
            self.update_collections_view()

            QMessageBox.information(self, 'Sucesso', 'Requisição importada com sucesso!')

    # Função para copiar o comando cURL de uma requisição para a área de transferência
    def copy_curl_from_request(self, tree_item):
        try:
            data = tree_item.data(0, Qt.UserRole)
            if not data or data.get('type') != 'request':
                QMessageBox.warning(self, "Erro", "Item selecionado não é uma requisição válida.")
                return

            request_id = data.get('id')
            if not request_id:
                QMessageBox.warning(self, "Erro", "ID da requisição não encontrado no item da árvore.")
                return
            
            request_data_dict_from_mapping = self.request_mapping.get(request_id)

            # Determinar a fonte correta dos dados da requisição
            request_data_dict_to_use = None
            is_current_request = bool(self.current_request_data and request_data_dict_from_mapping is self.current_request_data)

            if is_current_request:
                # A requisição selecionada é a que está ativa na UI.
                # Garante que os dados da UI sejam salvos no objeto current_request_data.
                self.update_current_request_data_from_ui() # Salva edições da UI
                request_data_dict_to_use = self.current_request_data # Usar os dados atualizados da UI
            else:
                # A requisição selecionada NÃO é a que está ativa na UI.
                # Usar os dados armazenados no request_mapping.
                request_data_dict_to_use = request_data_dict_from_mapping

            if not request_data_dict_to_use:
                QMessageBox.warning(self, "Erro", f"Dados da requisição com ID {request_id} não encontrados.")
                return

            request_details = request_data_dict_to_use.get('request', {})
            method = request_details.get('method', 'GET')
            
            url_data = request_details.get('url', {})
            if isinstance(url_data, dict):
                url_str = url_data.get('raw', '')
            else:
                url_str = str(url_data)

            headers = request_details.get('header', [])
            body_data_from_dict = request_details.get('body', {})
            
            body = ''
            if is_current_request:
                # Se é a requisição atual (e já foi atualizada da UI), o corpo vem do self.body_text
                # Isso garante que o cURL reflita o que está visível e editável na aba Body
                body = self.body_text.toPlainText()
            else:
                # Para requisições não ativas na UI, usar os dados do dicionário
                mode = body_data_from_dict.get('mode')
                if mode == 'raw':
                    body = body_data_from_dict.get('raw', '')
                elif body_data_from_dict:
                    # Para outros modos como formdata, urlencoded, o _gerar_curl atual usa -d.
                    # Uma representação ideal exigiria modificar _gerar_curl para usar -F etc.
                    # Por ora, passamos o conteúdo 'raw' se disponível, ou uma serialização JSON/string.
                    # Uma string vazia ou JSON do dict podem ser mais seguros para _gerar_curl como está.
                    try:
                        body = json.dumps(body_data_from_dict.get(mode))
                    except TypeError:
                        body = str(body_data_from_dict.get(mode))
                    # corpo_preparado = body_data_from_dict.get('raw', '')
            
            # Gerar o comando cURL
            string_do_curl_gerada = Curl._generate_curl(self, method, url_str, headers, body)

            # Copiar para a área de transferência
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(string_do_curl_gerada)
                QMessageBox.information(self, "Sucesso", "Comando cURL copiado para a área de transferência!")
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível acessar a área de transferência.")

        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao gerar ou copiar cURL: {str(e)}")

    # Função para gerar um comando cURL a partir dos dados da requisição
    def _generate_curl(self, method, url, headers, body):
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