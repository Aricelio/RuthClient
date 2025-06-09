# core/executor.py

import requests
import json
import traceback
import copy
import base64
from types import SimpleNamespace

# ### NOVOS IMPORTS E CONFIGURAÇÃO DE CERTIFICADO ###
# Tenta importar a biblioteca para certificados do Windows.
try:
    import certifi_win32
except ImportError:
    certifi_win32 = None

# Importa as funções de script que você já tinha.
from .script_utils import encrypt_password_cryptojs, decrypt_password_cryptojs, generate_random_string

# ### ATIVAÇÃO DO PATCH DE CERTIFICADOS ###
# Se a biblioteca foi encontrada, ela é ativada uma única vez quando o módulo é carregado.
# Isso "conserta" a biblioteca 'requests' para todas as chamadas futuras nesta sessão.
if certifi_win32:
    try:
        certifi_win32.patch()
        print("[Executor] Patch de certificados do Windows ativado para toda a aplicação.")
    except Exception as e:
        print(f"[Executor] AVISO: Falha ao ativar o patch de certificados do Windows: {e}")

# --- Classes de Acesso para a API 'pm' ---
class PMEnvironmentAccessor:
    def __init__(self, environment_manager_ref, env_name_str):
        self.env_manager = environment_manager_ref
        self.env_name = env_name_str

    def get(self, key_str):
        if self.env_name:
            return self.env_manager.get_variable(self.env_name, key_str)
        print(f"[Script PM Env] Tentativa de get('{key_str}') sem ambiente selecionado.")
        return None

    def set(self, key_str, value_any):
        if self.env_name:
            print(f"[Script PM Env] Setando '{key_str}' para '{value_any}' no ambiente '{self.env_name}'")
            self.env_manager.set_variable(self.env_name, key_str, value_any)
        else:
            print(f"[Script PM Env] Falha ao setar '{key_str}': Nenhum ambiente selecionado.")
            
    def unset(self, key_str):
        if self.env_name:
            print(f"[Script PM Env] Removendo '{key_str}' do ambiente '{self.env_name}'")
            self.env_manager.unset_variable(self.env_name, key_str)
        else:
            print(f"[Script PM Env] Falha ao remover '{key_str}': Nenhum ambiente selecionado.")

    def clear(self):
        if self.env_name:
            print(f"[Script PM Env] Limpando ambiente '{self.env_name}'")
            self.env_manager.clear_environment(self.env_name)
        else:
            print(f"[Script PM Env] Falha ao limpar: Nenhum ambiente selecionado.")

class PMRequestAccessor:
    def __init__(self, request_dict_being_processed_ref):
        self._processed_request_dict = request_dict_being_processed_ref 

    @property
    def url(self):
        url_data = self._processed_request_dict.get('url', {})
        if isinstance(url_data, dict):
            return url_data.get('raw', '')
        return str(url_data)

    @url.setter
    def url(self, value_str):
        if not isinstance(self._processed_request_dict.get('url'), dict):
            self._processed_request_dict['url'] = {}
        self._processed_request_dict['url']['raw'] = str(value_str)
        print(f"[Script PM Req] URL definida para: {str(value_str)}")

    @property
    def headers(self):
        if 'header' not in self._processed_request_dict or not isinstance(self._processed_request_dict['header'], list):
            self._processed_request_dict['header'] = []
        return PMHeadersListAccessor(self._processed_request_dict['header'])

    @property
    def method(self):
        return self._processed_request_dict.get('method', 'GET')

    @method.setter
    def method(self, value_str):
        self._processed_request_dict['method'] = str(value_str).upper()
        print(f"[Script PM Req] Método definido para: {self._processed_request_dict['method']}")
    
    @property
    def body(self):
        if 'body' not in self._processed_request_dict or not isinstance(self._processed_request_dict['body'], dict):
            self._processed_request_dict['body'] = {}
        return PMBodyAccessor(self._processed_request_dict['body'])

class PMHeadersListAccessor:
    def __init__(self, headers_list_ref):
        self._headers_list = headers_list_ref

    def add(self, header_obj_or_key, value_str=None):
        if isinstance(header_obj_or_key, dict) and 'key' in header_obj_or_key:
            key, val = header_obj_or_key['key'], header_obj_or_key.get('value', '')
        elif isinstance(header_obj_or_key, str) and value_str is not None:
            key, val = header_obj_or_key, value_str
        else:
            print("[Script PM Req Headers] Formato inválido para adicionar header.")
            return
            
        self._headers_list[:] = [h for h in self._headers_list if h.get('key','').lower() != key.lower()]
        self._headers_list.append({'key': key, 'value': str(val)})
        print(f"[Script PM Req Headers] Header adicionado/atualizado: {key}")

    def get(self, key_str):
        for h_obj in reversed(self._headers_list):
            if h_obj.get('key','').lower() == key_str.lower():
                return h_obj.get('value')
        return None

    def remove(self, key_str):
        original_len = len(self._headers_list)
        self._headers_list[:] = [h_obj for h_obj in self._headers_list if h_obj.get('key','').lower() != key_str.lower()]
        if len(self._headers_list) < original_len:
            print(f"[Script PM Req Headers] Header(s) removido(s) com chave: {key_str}")
    
    def all(self):
        return self._headers_list

class PMBodyAccessor:
    def __init__(self, body_dict_ref):
        self._body_dict = body_dict_ref

    @property
    def mode(self):
        return self._body_dict.get('mode')

    @mode.setter
    def mode(self, value_str):
        self._body_dict['mode'] = str(value_str)
        print(f"[Script PM Req Body] Modo definido para: {str(value_str)}")

    @property
    def raw(self):
        return self._body_dict.get('raw', '') if self.mode == 'raw' else ''

    @raw.setter
    def raw(self, value_str):
        self._body_dict['mode'] = 'raw'
        self._body_dict['raw'] = str(value_str)
        print(f"[Script PM Req Body] Raw content definido.")

    @property
    def formdata(self):
        if self.mode != 'formdata':
            self._body_dict.pop('raw', None)
            self._body_dict.pop('urlencoded', None)
        self._body_dict['mode'] = 'formdata'
        if 'formdata' not in self._body_dict or not isinstance(self._body_dict['formdata'], list):
            self._body_dict['formdata'] = []
        return KeyValueListAccessor(self._body_dict['formdata'])

class KeyValueListAccessor:
    def __init__(self, list_ref):
        self._list = list_ref

    def add(self, item_obj_or_key, value_str=None, item_type_str='text'):
        if isinstance(item_obj_or_key, dict) and 'key' in item_obj_or_key:
            key, val, item_type = item_obj_or_key['key'], item_obj_or_key.get('value', ''), item_obj_or_key.get('type', item_type_str)
        elif isinstance(item_obj_or_key, str) and value_str is not None:
            key, val, item_type = item_obj_or_key, value_str, item_type_str
        else:
            return
        new_item = {'key': key, 'value': str(val), 'type': item_type}
        self._list.append(new_item)

    def all(self):
        return self._list

class PMResponseAccessor:
    def __init__(self, actual_requests_response_obj):
        self._actual_response = actual_requests_response_obj

    @property
    def code(self):
        return self._actual_response.status_code

    def text(self):
        return self._actual_response.text

    def json(self):
        try:
            return self._actual_response.json()
        except (json.JSONDecodeError, requests.exceptions.JSONDecodeError):
            print("[Script PM Res] Conteúdo da resposta não é JSON válido.")
            return None

    @property
    def headers(self):
        return self._actual_response.headers

    @property
    def responseTime(self):
        return self._actual_response.elapsed.total_seconds() * 1000 if self._actual_response.elapsed else 0

# --- Classe Executor Principal ---
class Executor:
    def __init__(self, environment_manager_instance):
        self.environment_manager = environment_manager_instance
        self.last_script_error_traceback = None
        self.session = self._create_requests_session()

    def _create_requests_session(self):
        session = requests.Session()
        session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        session.trust_env = True
        return session

    def _create_pm_scripting_context(self, processed_request_item_data_ref, current_env_name_str, actual_requests_response_obj=None):
        request_dict_ref = processed_request_item_data_ref.get('request', {})
        pm_api_object = SimpleNamespace()
        pm_api_object.environment = PMEnvironmentAccessor(self.environment_manager, current_env_name_str)
        pm_api_object.collectionVariables = pm_api_object.environment
        pm_api_object.request = PMRequestAccessor(request_dict_ref)
        pm_api_object.crypto = SimpleNamespace(
            encryptAESToString=encrypt_password_cryptojs,
            decryptAESToString=decrypt_password_cryptojs
        )
        pm_api_object.variables = SimpleNamespace(
            replaceIn=lambda s: self.environment_manager.substitute_variables_in_string(s, current_env_name_str) if current_env_name_str else s,
            get=lambda k: self.environment_manager.get_variable(current_env_name_str, k) if current_env_name_str else None,
            set=lambda k, v: self.environment_manager.set_variable(current_env_name_str, k, v) if current_env_name_str else None,
            unset=lambda k: self.environment_manager.unset_variable(current_env_name_str, k) if current_env_name_str else None,
            clear=lambda: self.environment_manager.clear_environment(current_env_name_str) if current_env_name_str else None
        )
        pm_api_object.globals = pm_api_object.environment
        pm_api_object.iterationData = SimpleNamespace(get=lambda k: None, toObject=lambda: {})
        pm_api_object.info = SimpleNamespace(
            eventName=None,
            iteration=0,
            iterationCount=0,
            requestId=processed_request_item_data_ref.get('id', None) or processed_request_item_data_ref.get('name', None),
            requestName=processed_request_item_data_ref.get('name', None)
        )
        pm_api_object.utils = SimpleNamespace(
            randomStr=generate_random_string
        )

        if actual_requests_response_obj:
            pm_api_object.response = PMResponseAccessor(actual_requests_response_obj)

        script_execution_globals = {
            'pm': pm_api_object,
            'console': SimpleNamespace(log=lambda *args: print("[Script Console]", *args)),
            'AssertionError': AssertionError,
            'json': json,
            'base64': __import__('base64'),
            'hashlib': __import__('hashlib'),
            '_': SimpleNamespace(get=lambda obj, path, default=None: obj.get(path, default))
        }
        return script_execution_globals

    def _run_script_safely(self, script_code_str, script_execution_globals_ref, event_name_for_pm_info=None):
        self.last_script_error_traceback = None
        if not script_code_str or not script_code_str.strip():
            return
        
        if event_name_for_pm_info and hasattr(script_execution_globals_ref.get('pm'), 'info'):
            script_execution_globals_ref['pm'].info.eventName = event_name_for_pm_info
            
        try:
            exec(script_code_str, script_execution_globals_ref, {})
        except Exception as e:
            self.last_script_error_traceback = traceback.format_exc()
            print(f"!!! [Script {event_name_for_pm_info or ''}] Erro: {e}")
            traceback.print_exc()
            raise Exception(f"Erro na execução do script Python ({event_name_for_pm_info or ''}): {type(e).__name__} - {e}") from e

    def execute_request_with_scripts(self, original_request_item_data, current_env_name, verify_ssl=True):
        processed_request_data = copy.deepcopy(original_request_item_data)
        script_context = self._create_pm_scripting_context(processed_request_data, current_env_name)

        # Executa pre-request script
        for event in original_request_item_data.get('event', []):
            if event.get('listen') == 'prerequest':
                script_code = "\n".join(event.get('script', {}).get('exec', []))
                if script_code.strip():
                    print(f"\n--- Executando Pre-request Script (Ambiente: {current_env_name or 'Nenhum'}) ---")
                    self._run_script_safely(script_code, script_context, 'prerequest')
                    print("--- Fim Pre-request Script ---\n")
                break
        
        # Aplica variáveis após o pre-request
        final_request_details = processed_request_data.get('request', {})
        if current_env_name:
            final_request_details = self.environment_manager.apply_environment(final_request_details, current_env_name)
        
        # Prepara dados para a requisição
        http_method = final_request_details.get('method', 'GET').upper()
        final_url = final_request_details.get('url', {}).get('raw', '')
        final_headers = {h['key']: h['value'] for h in final_request_details.get('header', []) if h.get('key')}
        
        # Processa o helper de Autenticação
        auth_config = final_request_details.get('auth')
        if auth_config:
            print("--- Processando Helper de Autenticação ---")
            auth_type = auth_config.get('type')
            if auth_type == 'bearer':
                token = auth_config.get('bearer', [{}])[0].get('value', '')
                if token:
                    final_headers['Authorization'] = f"Bearer {token}"
                    print("  -> 'Bearer Token' aplicado ao header Authorization.")
            elif auth_type == 'basic':
                user = next((item['value'] for item in auth_config.get('basic', []) if item.get('key') == 'username'), '')
                pwd = next((item['value'] for item in auth_config.get('basic', []) if item.get('key') == 'password'), '')
                creds = base64.b64encode(f"{user}:{pwd}".encode('utf-8')).decode('utf-8')
                final_headers['Authorization'] = f"Basic {creds}"
                print("  -> 'Basic Auth' aplicado ao header Authorization.")
                
        # Prepara o corpo da requisição
        body_config = final_request_details.get('body', {})
        body_mode = body_config.get('mode')
        data_param, json_param, files_param = None, None, None
        
        if http_method not in ['GET', 'HEAD', 'DELETE']:
            if body_mode == 'raw':
                content_type = {k.lower(): v for k, v in final_headers.items()}.get('content-type', '')
                raw_body = body_config.get('raw', '')
                if 'application/json' in content_type:
                    try:
                        json_param = json.loads(raw_body)
                    except json.JSONDecodeError:
                        data_param = raw_body.encode('utf-8')
                else:
                    data_param = raw_body.encode('utf-8')
            elif body_mode == 'formdata':
                files_param = {item.get('key'): (None, str(item.get('value', ''))) for item in body_config.get('formdata', []) if item.get('key')}
            elif body_mode == 'urlencoded':
                data_param = {item.get('key'): str(item.get('value', '')) for item in body_config.get('urlencoded', []) if item.get('key')}

        # Configura a verificação SSL na sessão
        self.session.verify = verify_ssl
        
        # Imprime detalhes finais para depuração
        print("\n" + "="*20 + " DETALHES FINAIS DA REQUISIÇÃO PARA ENVIO " + "="*20)
        print(f"Método: {http_method}\nURL: {final_url}\nHeaders: {json.dumps(final_headers, indent=2)}")
        print("="*70 + "\n")
        
        # Executa a requisição
        try:
            response = self.session.request(
                method=http_method, url=final_url, headers=final_headers,
                data=data_param, json=json_param, files=files_param, timeout=30
            )
        except requests.exceptions.RequestException as e:
            class MockErrorResponse:
                def __init__(self, error):
                    self.status_code, self.reason, self.text, self.headers, self.elapsed = 0, type(error).__name__, str(error), {}, None
                def json(self): return {'error': self.text, 'message': str(self)}
            response = MockErrorResponse(e)

        # Executa o script de teste
        script_context['pm'].response = PMResponseAccessor(response)
        for event in original_request_item_data.get('event', []):
            if event.get('listen') == 'test':
                script_code = "\n".join(event.get('script', {}).get('exec', []))
                if script_code.strip():
                    print("\n--- Executando Test Script ---")
                    try: 
                        self._run_script_safely(script_code, script_context, 'test')
                    except Exception as e_test: 
                        print(f"!!! Erro no Test Script: {e_test}")
                    print("--- Fim Test Script ---\n")
                break
                
        return response