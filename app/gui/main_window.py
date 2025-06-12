import sys
import os

# Add the 'app' directory (parent of 'gui') to sys.path
# to allow imports like 'from core.module import ...'
# This ensures that modules within the 'app' directory, like 'core', can be found.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import urllib3
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMessageBox, QTreeWidgetItem, QMenu, QInputDialog
from PyQt5.QtCore import Qt
from core.executor import Executor
from core.environment import EnvironmentManager
from data.collection import CollectionRepository
from data.environment import EnvironmentRepository
from gui.main.configuration import Configuration
from gui.main.environment import Environment
from gui.main.curl import Curl

# Desabilita avisos de SSL inseguros
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class MainWindow(QMainWindow):

    # Função principal para executar a aplicação
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Ferramenta de Requisições HTTP')
        self.setGeometry(100, 100, 1200, 800)

        Configuration.set_icon(self, os)

        self.collections = []
        self.environments = EnvironmentManager()
        self.current_request_data = None
        self.request_mapping = {}  # Mapear IDs únicos para itens de requisição

        # Setup UI
        Configuration._setup_ui(self)
        Configuration._create_actions(self)
        Configuration._create_menu_bar(self)

        # Load collections and environments
        CollectionRepository.load(self, os)
        EnvironmentRepository.load(self, os)
        
        # Now update the UI components that depend on loaded data
        Environment.update_environment_combo(self)
        Environment.update_edit_environments_menu(self)
        self.update_collections_view()  

    # Função para lidar com a mudança do método HTTP selecionado
    def on_method_changed(self, button):
        selected_method = button.text()
        print(f"Método HTTP selecionado: {selected_method}")

        # Atualiza o método na requisição atual, se houver
        if self.current_request_data:
            self.current_request_data['request']['method'] = selected_method

    # Função para lidar com a seleção de um item na árvore de coleções/requisições
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

    # Função para lidar com a ativação de um item na árvore (duplo clique ou Enter)
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

    # Função para limpar os detalhes da requisição exibidos na interface
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

    # Função para lidar com a mudança do tipo de corpo da requisição
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

    # Função para lidar com a mudança do ambiente ativo
    def on_environment_changed(self, index):
        # Ação ao mudar o ambiente ativo
        selected_env = self.environment_combo.currentText()
        print(f'Ambiente ativo selecionado: {selected_env}')

    # Função para atualizar a exibição das coleções na árvore
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

    # Função auxiliar para adicionar itens de requisição (ou pastas) à árvore
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

    # Função para exibir os detalhes de uma requisição selecionada
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

    # Função para atualizar os dados da requisição atual a partir da interface
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

    # Função para executar a requisição HTTP
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

    # Função para exibir a resposta da requisição
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

    # Função para lidar com o evento de fechamento da janela
    def closeEvent(self, event):
        
        if self.current_request_data:
            self.update_current_request_data_from_ui()
        
        CollectionRepository.save(self, os)
        EnvironmentRepository.save(self, os)
        event.accept()  # Aceita o evento de fechamento    

    # Função para copiar o comando cURL de uma requisição
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

    # Função para renomear um item (pasta ou requisição) na árvore
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

        CollectionRepository.save(self, os)
        QMessageBox.information(self, 'Sucesso', f'{prefix.capitalize()} renomeada para "{novo.strip()}"')

    # Função para exibir o menu de contexto ao clicar com o botão direito na árvore
    def on_tree_item_context_menu(self, position):
        item = self.tree_widget.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.UserRole) or {}
        type = data.get('type')
        menu = QMenu(self)

        if type == 'request':
            rename_act = QAction('Renomear', self)
            rename_act.triggered.connect(lambda _, it=item: self._rename_item(it))
            menu.addAction(rename_act)

            copy_curl_action = QAction('Copiar cURL', self)
            copy_curl_action.triggered.connect(lambda _, it=item: Curl.copy_curl_from_request(self, it))
            menu.addAction(copy_curl_action)

            move_act = QAction('Mover para...', self)
            move_act.triggered.connect(lambda _, it=item: self._move_request(it))
            menu.addAction(move_act)

            del_act = QAction('Excluir Requisição', self)
            del_act.triggered.connect(lambda _, it=item: self._delete_item(it))
            menu.addAction(del_act)

        elif type == 'folder':
            rename_act = QAction('Renomear', self)
            rename_act.triggered.connect(lambda _, it=item: self._rename_item(it))
            menu.addAction(rename_act)

            del_act = QAction('Excluir Pasta', self)
            del_act.triggered.connect(lambda _, it=item: self._delete_item(it))
            menu.addAction(del_act)

        elif type == 'collection':
            new_folder_act = QAction('Nova Pasta', self)
            new_folder_act.triggered.connect(lambda _, it=item: self._new_folder(it))
            menu.addAction(new_folder_act)

            del_act = QAction('Excluir Coleção', self)
            del_act.triggered.connect(lambda _, it=item: self._delete_item(it))
            menu.addAction(del_act)

        menu.exec_(self.tree_widget.viewport().mapToGlobal(position))

    # Função para excluir um item (coleção, pasta ou requisição)
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

            CollectionRepository.save(self, os)
            self.update_collections_view()
            QMessageBox.information(self, 'Sucesso', f'{tipo.capitalize()} excluída com sucesso.')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Erro ao excluir item:\n{e}')

    # Função para criar uma nova pasta (subcoleção) dentro de uma coleção
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

            CollectionRepository.save(self, os)
            self.update_collections_view()
            QMessageBox.information(self, 'Sucesso', f'Pasta "{nome.strip()}" criada com sucesso.')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', f'Falha ao criar a pasta:\n{e}')

    # Função para navegar através de uma estrutura aninhada de dicionários e listas para encontrar um nó específico.
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

    # Função para mover uma requisição para outra pasta dentro da mesma coleção
    def _move_request(self, request_item_widget): # Renomeado para clareza (o argumento é o QTreeWidget)
        data = request_item_widget.data(0, Qt.UserRole)
        
        if not data or data.get('type') != 'request':
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
        CollectionRepository.save(self, os)
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