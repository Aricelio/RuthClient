class EnvironmentManager:
    def __init__(self):
        self.environments = {}

    def add_environment(self, name, variables):
        self.environments[name] = variables

    def remove_environment(self, name):
        if name in self.environments:
            del self.environments[name]

    def get_environment(self, name):
        return self.environments.get(name, {})

    def apply_environment(self, request_data, environment_name):
        environment = self.get_environment(environment_name)
        if not environment:
            return request_data  # Nenhum environment para aplicar

        def replace_variables(value):
            if isinstance(value, str):
                for key, val in environment.items():
                    placeholder = f'{{{{{key}}}}}'
                    value = value.replace(placeholder, val)
            elif isinstance(value, dict):
                for k, v in value.items():
                    value[k] = replace_variables(v)
            elif isinstance(value, list):
                value = [replace_variables(item) for item in value]
            return value

        # Obter a requisição do request_data
        request = request_data.get('request', {})

        # Substituir variáveis na URL
        request['url'] = replace_variables(request.get('url', ''))

        # Substituir variáveis nos headers
        if 'header' in request:
            request['header'] = replace_variables(request['header'])

        # Substituir variáveis nos parâmetros (params)
        if 'params' in request:
            request['params'] = replace_variables(request['params'])

        # Substituir variáveis no corpo da requisição
        if 'body' in request:
            request['body'] = replace_variables(request['body'])

        # Atualizar o request_data com a requisição modificada
        request_data['request'] = request

        return request_data
