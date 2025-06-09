# core/environment.py (VERSÃO FINAL COM SUAS FUNÇÕES MANTIDAS E CORREÇÕES APLICADAS)

import json
import re

class EnvironmentManager:
    def __init__(self):
        self.environments = {}  # Estrutura: {"env_name": {"var1": "val1", "var2": "val2"}}

    # --- SUAS FUNÇÕES ORIGINAIS (MANTIDAS, POIS ESTÃO CORRETAS) ---
    def add_environment(self, name, variables):
        self.environments[name] = variables

    def remove_environment(self, name):
        if name in self.environments:
            del self.environments[name]

    def get_environment(self, name):
        return self.environments.get(name, {})

    def get_variable(self, env_name, key):
        env = self.get_environment(env_name)
        return env.get(key)

    def set_variable(self, env_name, key, value):
        if env_name and env_name in self.environments:
            self.environments[env_name][key] = str(value)
            return True
        elif env_name and env_name not in self.environments:
            self.environments[env_name] = {key: str(value)}
            return True
        return False

    def unset_variable(self, env_name, key):
        if env_name and env_name in self.environments and key in self.environments[env_name]:
            del self.environments[env_name][key]
            return True
        return False

    def clear_environment(self, env_name):
        if env_name and env_name in self.environments:
            self.environments[env_name].clear()
            return True
        return False
    # --- FIM DAS SUAS FUNÇÕES ORIGINAIS ---


    # ### FUNÇÃO 1: CORRIGIDA E MELHORADA ###
    def _substitute_variables_in_string(self, text_string, env_vars_dict):
        """
        Substitui variáveis como {{var}} em uma string.
        Esta versão melhorada faz múltiplas passadas para resolver variáveis aninhadas
        (ex: uma variável cujo valor contém outra variável).
        """
        if not isinstance(text_string, str) or '{{' not in text_string:
            return text_string

        # Função interna para o regex encontrar e substituir
        def replace_match(match):
            var_name = match.group(1).strip()
            # Retorna o valor da variável ou o placeholder original se não for encontrada
            return str(env_vars_dict.get(var_name, match.group(0)))

        # Faz até 10 passadas para resolver placeholders aninhados.
        # Isso evita loops infinitos e resolve casos como {{url}}/{{path}}.
        for _ in range(10):
            new_text_string = re.sub(r"\{\{([^{}]+?)\}\}", replace_match, text_string)
            if new_text_string == text_string:
                # Se não houver mais substituições, o trabalho está feito.
                return new_text_string
            text_string = new_text_string
            
        return text_string # Retorna o resultado após o limite de passadas


    # ### FUNÇÃO 2: CORRIGIDA E MELHORADA ###
    def apply_environment(self, request_details_dict, environment_name):
        """
        Aplica variáveis de um ambiente a um dicionário de requisição de forma recursiva.
        Esta versão é genérica e funciona para qualquer estrutura de dados.
        """
        environment_vars = self.get_environment(environment_name)
        if not environment_vars:
            return request_details_dict

        def recursive_replace(data_structure):
            """Função interna que navega e substitui valores em qualquer estrutura."""
            if isinstance(data_structure, str):
                # Se o item for uma string, aplica a substituição
                return self._substitute_variables_in_string(data_structure, environment_vars)
            
            if isinstance(data_structure, dict):
                # Se for um dicionário, chama a função para cada um de seus valores
                for key in list(data_structure.keys()):
                    data_structure[key] = recursive_replace(data_structure[key])
                return data_structure

            if isinstance(data_structure, list):
                # Se for uma lista, chama a função para cada item da lista
                for i, item in enumerate(data_structure):
                    data_structure[i] = recursive_replace(item)
                return data_structure
            
            # Se não for string, dict ou list (ex: número, booleano), retorna como está
            return data_structure

        # Inicia o processo de substituição recursiva no dicionário de requisição inteiro.
        # Não precisa mais de uma cópia, pois o Executor já faz isso.
        return recursive_replace(request_details_dict)