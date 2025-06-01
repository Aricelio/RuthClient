import requests
import json

class Executor:
    def execute_request(self, request, verify_ssl=True):
        method = request.get('method', 'GET').upper()
        url = request.get('url', '')
        headers = {header['key']: header['value'] for header in request.get('header', [])}
        data = None
        json_data = None
        files = None

        # Verifica o Content-Type
        content_type = headers.get('Content-Type', '').lower()

        # Verifica se há um corpo na requisição
        if 'body' in request:
            body = request['body']
            mode = body.get('mode')
            if mode == 'raw':
                data = body.get('raw', '')
                if content_type == 'application/json':
                    # Enviar o JSON usando o parâmetro 'json'
                    try:
                        json_data = json.loads(data)
                        data = None  # Não enviar 'data' se usar 'json'
                    except json.JSONDecodeError:
                        raise ValueError("O corpo da requisição contém JSON inválido.")
                else:
                    # Para outros tipos de 'raw', enviar como texto
                    data = data.encode('utf-8')
            elif mode == 'formdata':
                # Enviar como multipart/form-data
                formdata = body.get('formdata', [])
                files = {}
                for item in formdata:
                    key = item.get('key')
                    value = item.get('value')
                    if key:
                        files[key] = (None, value)
            elif mode == 'urlencoded':
                # Enviar como application/x-www-form-urlencoded
                data = {item.get('key'): item.get('value') for item in body.get('urlencoded', [])}
            else:
                # Outros modos não implementados
                pass

        # Executa a requisição com a opção de verificação SSL
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            json=json_data,
            files=files,
            verify=verify_ssl
        )

        return response
