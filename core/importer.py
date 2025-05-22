import json
import shlex
from urllib.parse import urlparse

class Importer:
    def import_collection(self, file_path):
        """
        Importa um arquivo JSON de coleção (Postman v2.x) e retorna o dicionário correspondente.
        """
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data

    def import_curl(self, curl_cmd):
        """
        Converte um comando cURL em um item de requisição compatível com a estrutura interna.
        Aceita comandos multilinha com '\' e quebra de linha.
        """
        # Limpa quebras de linha e barras de continuação
        cmd = curl_cmd.replace('\\\n', ' ').replace('\\\r\n', ' ')
        cmd = cmd.replace('\\', ' ')
        # Tokeniza o comando
        tokens = shlex.split(cmd)
        method = 'GET'
        url = None
        headers = []
        body = {}

        it = iter(tokens)
        for tok in it:
            if tok.lower() == 'curl':
                continue
            # Método explícito
            if tok in ('-X', '--request'):
                try:
                    method = next(it).upper()
                except StopIteration:
                    break
                continue
            # Headers
            if tok in ('-H', '--header'):
                try:
                    raw_hdr = next(it)
                    if ':' in raw_hdr:
                        key, val = raw_hdr.split(':', 1)
                        headers.append({'key': key.strip(), 'value': val.strip()})
                except StopIteration:
                    break
                continue
            # Dados raw
            if tok in ('-d', '--data', '--data-raw', '--data-binary'):
                try:
                    data_str = next(it)
                    body = {'mode': 'raw', 'raw': data_str}
                except StopIteration:
                    break
                continue
            # Form data
            if tok in ('-F', '--form'):
                try:
                    form_str = next(it)
                    if '=' in form_str:
                        key, val = form_str.split('=', 1)
                        if body.get('mode') != 'formdata':
                            body = {'mode': 'formdata', 'formdata': []}
                        body['formdata'].append({'key': key.strip(), 'value': val.strip(), 'type': 'text'})
                except StopIteration:
                    break
                continue
            # Autenticação básica
            if tok in ('-u', '--user'):
                try:
                    creds = next(it)
                    headers.append({'key': 'Authorization', 'value': f'Basic {creds}'})
                except StopIteration:
                    break
                continue
            # Ignorar SSL inseguro
            if tok in ('-k', '--insecure'):
                continue
            # URL de destino (primeiro token sem prefixo '-')
            if not tok.startswith('-') and url is None:
                url = tok
                continue
            # Outros flags são ignorados

        if url is None:
            raise ValueError('Não foi possível identificar a URL no comando cURL.')

        # Se há body e método não explicitado, usar POST
        if body and method == 'GET':
            method = 'POST'

        request_item = {
            'name': url,
            'request': {
                'method': method,
                'url': url,
                'header': headers,
                'body': body
            }
        }
        return request_item
