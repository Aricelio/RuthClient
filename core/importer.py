import json
import shlex
import re # Para detecção de JS

class Importer:

    def _is_javascript_likely(self, script_code_str):
        """Heurística simples para detectar se um script é provavelmente JavaScript."""
        if not script_code_str or not script_code_str.strip():
            return False
        
        # Comentários comuns de JS
        if re.search(r"^\s*//", script_code_str, re.MULTILINE):
            return True
        if "/*" in script_code_str and "*/" in script_code_str: # Comentário de bloco JS
            return True
            
        # Palavras-chave comuns de JS e API pm do Postman
        js_keywords = [
            'var ', 'let ', 'const ', 'function ', '=>', 
            'pm.test(', 'pm.expect(', 'JSON.parse(', 'JSON.stringify(',
            'pm.response.to.have.status(', 'pm.response.json()', 'pm.sendRequest(',
            'console.log(' # console.log é comum, mas pode ser usado em Python no nosso pm
        ]
        for keyword in js_keywords:
            if keyword in script_code_str:
                return True
        return False

    def _handle_imported_script(self, script_exec_list):
        """
        Processa uma lista de linhas de script. Se parecer JS, comenta e adiciona aviso.
        Retorna a nova lista de linhas de script.
        """
        if not script_exec_list:
            return []

        # Junta as linhas para análise e depois separa novamente se precisar comentar
        full_script_content = "\n".join(script_exec_list)

        if self._is_javascript_likely(full_script_content):
            warning_message = [
                "# ATENÇÃO: O script original abaixo parece ser JavaScript e foi comentado.",
                "# Converta-o para Python para que possa ser executado nesta ferramenta."
            ]
            commented_script_lines = [f"# {line}" for line in full_script_content.splitlines()]
            return warning_message + ["# --- INÍCIO DO SCRIPT ORIGINAL JS ---"] + commented_script_lines + ["# --- FIM DO SCRIPT ORIGINAL JS ---"]
        else:
            # Se não parece JS, retorna como está (assume que é Python ou será tratado como tal)
            return script_exec_list


    def import_collection(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if not isinstance(data.get('info'), dict) or not isinstance(data.get('item'), list):
            raise ValueError("Arquivo de coleção não parece ter a estrutura Postman v2.x (info, item).")
            
        # Processar scripts em eventos
        def process_events_in_items(items_list_data):
            for item_dict in items_list_data:
                if 'event' in item_dict and isinstance(item_dict['event'], list):
                    for event_dict in item_dict['event']:
                        if 'script' in event_dict and isinstance(event_dict['script'], dict) and \
                           'exec' in event_dict['script'] and isinstance(event_dict['script']['exec'], list):
                            
                            original_exec_list = event_dict['script']['exec']
                            # Modifica a lista 'exec' no local com o script processado
                            event_dict['script']['exec'] = self._handle_imported_script(original_exec_list)
                
                # Se for uma pasta, processa recursivamente seus itens
                if 'item' in item_dict and isinstance(item_dict['item'], list):
                    process_events_in_items(item_dict['item'])
        
        process_events_in_items(data['item']) # Processa a lista principal de itens da coleção
        
        # Processar scripts no nível da coleção também, se houver
        if 'event' in data and isinstance(data['event'], list):
            for event_dict in data['event']:
                if 'script' in event_dict and isinstance(event_dict['script'], dict) and \
                   'exec' in event_dict['script'] and isinstance(event_dict['script']['exec'], list):
                    original_exec_list = event_dict['script']['exec']
                    event_dict['script']['exec'] = self._handle_imported_script(original_exec_list)
        
        return data

    # ... (seu método import_curl mantido como estava, pois o foco era na importação de coleção com scripts)
    def import_curl(self, curl_cmd):
        """
        Converte um comando cURL em um item de requisição compatível com a estrutura interna.
        Aceita comandos multilinha com '\' e quebra de linha.
        """
        # Limpa quebras de linha e barras de continuação
        cmd = curl_cmd.replace('\\\n', ' ').replace('\\\r\n', ' ')
        cmd = cmd.replace('\\', ' ') # Remove barras de escape simples (pode ser muito agressivo)
        
        tokens = []
        try:
            tokens = shlex.split(cmd)
        except ValueError as e:
            # shlex pode falhar com aspas não fechadas. Tenta uma divisão mais simples como fallback.
            print(f"shlex falhou ({e}), tentando divisão simples. O resultado pode ser impreciso.")
            tokens = cmd.split()


        method = 'GET'
        url = None
        headers = []
        body_data = {} # Usará a estrutura {'mode': 'raw', 'raw': '...'} ou similar
        auth = None # Para -u

        # Iterador para facilitar o consumo de tokens
        it = iter(tokens)
        for tok in it:
            if tok.lower() == 'curl': # Ignora o token 'curl'
                continue
            
            if tok in ('-X', '--request'):
                try: method = next(it).upper()
                except StopIteration: break
                continue
            
            if tok in ('-H', '--header'):
                try:
                    raw_hdr = next(it)
                    if ':' in raw_hdr:
                        key, val = raw_hdr.split(':', 1)
                        headers.append({'key': key.strip(), 'value': val.strip()})
                except StopIteration: break
                continue
            
            # Priorizar --data-raw se presente
            if tok == '--data-raw':
                try:
                    data_str = next(it)
                    body_data = {'mode': 'raw', 'raw': data_str}
                except StopIteration: break
                continue

            if tok in ('-d', '--data', '--data-binary'): # --data-binary também tratado como raw aqui
                try:
                    data_str = next(it)
                    if not body_data: 
                        body_data = {'mode': 'raw', 'raw': data_str}
                except StopIteration: break
                continue

            if tok in ('-F', '--form'):
                try:
                    form_str = next(it)
                    if '=' in form_str:
                        key, val = form_str.split('=', 1)
                        if body_data.get('mode') != 'formdata':
                            body_data = {'mode': 'formdata', 'formdata': []}
                        if val.startswith('@') and len(val) > 1: val = val[1:] 
                        body_data['formdata'].append({'key': key.strip(), 'value': val.strip(), 'type': 'text'})
                except StopIteration: break
                continue
            
            if tok in ('-u', '--user'): 
                try:
                    user_pass_str = next(it)
                    user, __, passwd = user_pass_str.partition(':')
                    auth = {
                        'type': 'basic',
                        'basic': [
                            {'key': 'username', 'value': user},
                            {'key': 'password', 'value': passwd}
                        ]
                    }
                except StopIteration: break
                continue
            
            if tok.startswith('-') and tok not in ('--compressed'): 
                try:
                    if tok not in ('-k', '--insecure', '--compressed', '-s', '--silent', '-S', '--show-error', '-L', '--location', '-i', '--include', '-I', '--head'): 
                        next(it) 
                except StopIteration:
                    pass 
                continue

            if not tok.startswith('-') and url is None:
                url = tok
                continue
        
        if url is None:
            if tokens and not tokens[-1].startswith('-') and not any(tokens[-2] == flag for flag in ['-X','-H','-d','--data','--data-raw','-F','-u']):
                 url = tokens[-1]
            else:
                raise ValueError('Não foi possível identificar a URL no comando cURL.')

        if body_data and method == 'GET':
            method = 'POST'

        request_details = {
            'method': method,
            'url': {'raw': url}, 
            'header': headers,
        }
        if body_data: 
            request_details['body'] = body_data
        if auth: 
            request_details['auth'] = auth
            
        request_item = {
            'name': f"cURL - {url.split('?')[0][:50]}...", 
            'request': request_details,
            'event': [] 
        }
        return request_item