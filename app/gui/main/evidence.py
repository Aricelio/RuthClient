import os
import json
from PyQt5.QtWidgets import QMessageBox
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph

class Evidence:

    # Função para gerar um PDF com evidências da requisição
    def generate_pdf_evidence(self):
        if not self.current_request_data:
            QMessageBox.warning(self, "Aviso", "Nenhuma requisição selecionada.")
            return

        try:
            evid_dir = os.path.join(os.getcwd(), "evidência")
            os.makedirs(evid_dir, exist_ok=True)

            now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_name = f"evidencia_{now}.pdf"
            file_path = os.path.join(evid_dir, file_name)

            # Constantes e Estilos
            left_margin = 50
            right_margin = 50
            top_margin = 50
            bottom_margin = 50
            text_start_x = 60

            c = canvas.Canvas(file_path, pagesize=A4)
            width, height = A4
            available_width = width - text_start_x - right_margin

            styles = getSampleStyleSheet()
            para_style = styles['Normal']
            para_style.fontName = 'Helvetica'
            para_style.fontSize = 10
            para_style.leading = 12

            request = self.current_request_data.get('request', {})
            method = request.get('method', 'GET')
            url = request.get('url', '')
            if isinstance(url, dict):
                url = url.get('raw', '')

            headers = request.get('header', [])
            body_content_from_request = None
            if request.get('body', {}).get('mode') == 'raw':
                try:
                    # Tenta carregar como JSON para formatação, mas usa o raw string se falhar
                    raw_body_text = request['body'].get('raw', '')
                    parsed_json = json.loads(raw_body_text)
                    body_content_from_request = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                except Exception:
                    body_content_from_request = request['body'].get('raw', '')


            curl_cmd = self._generate_curl(method, url, headers, body_content_from_request) # Passa o body formatado ou raw
            status_code = self.status_code_text.toPlainText().strip()
            response_body = self.response_body_text.toPlainText().strip() # Este é o que será renderizado com Paragraph

            # Posição Inicial Y
            current_y = height - top_margin

            # Título do PDF
            c.setFont("Helvetica-Bold", 14)
            c.drawString(left_margin, current_y, "Evidência de Requisição HTTP")
            current_y -= 30 # Espaço após o título principal

            c.setFont("Helvetica-Bold", 12)
            if current_y - 14 < bottom_margin: # 14 é uma altura aproximada para o título
                c.showPage()
                current_y = height - top_margin
                c.setFont("Helvetica-Bold", 14) # Redefine a fonte do título principal se houver quebra
                c.drawString(left_margin, current_y, "Evidência de Requisição HTTP")
                current_y -= 30
            c.setFont("Helvetica-Bold", 12) # Garante a fonte do título da seção
            c.drawString(left_margin, current_y, "cURL:")
            current_y -= 20 # Espaço antes do conteúdo do curl

            curl_paragraph = Paragraph(curl_cmd, para_style)
            p_w, p_h = curl_paragraph.wrapOn(c, available_width, height) # height aqui é um limite máximo grande

            if current_y - p_h < bottom_margin:
                c.showPage()
                current_y = height - top_margin
                # Se o título do cURL foi para a nova página, redesenhe-o
                c.setFont("Helvetica-Bold", 12)
                c.drawString(left_margin, current_y, "cURL:") # Redesenha o título se necessário
                current_y -= 20
            
            curl_paragraph.drawOn(c, text_start_x, current_y - p_h)
            current_y -= (p_h + 20) # Espaço após o curl

            # Renderização do Status Code
            if current_y - 12 - 15 - 12 < bottom_margin: # Alturas aproximadas para título e valor
                c.showPage()
                current_y = height - top_margin
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(left_margin, current_y, "Status Code:")
            current_y -= 15
            c.setFont("Helvetica", 10)
            c.drawString(text_start_x, current_y, status_code)
            current_y -= 25 # Espaço após status code

            # Renderização do Body (response_body)
            if current_y - 12 < bottom_margin: # Altura aproximada para o título
                c.showPage()
                current_y = height - top_margin
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(left_margin, current_y, "Body:")
            current_y -= 15 # Espaço antes do conteúdo do body

            if response_body: # Apenas processar se houver corpo de resposta
                # Escapar entidades HTML para evitar problemas com caracteres como <, >, &
                from xml.sax.saxutils import escape
                escaped_response_body = escape(response_body)
                # Substituir novas linhas por <br/> para que o Paragraph as interprete corretamente
                formatted_response_body_for_paragraph = escaped_response_body.replace('\\n', '<br/>').replace('\\r\\n', '<br/>').replace('\\r', '<br/>')


                body_paragraph = Paragraph(formatted_response_body_for_paragraph, para_style)
                
                # Obter a altura total que o parágrafo ocuparia se não houvesse restrição de altura da página
                _, total_h = body_paragraph.wrapOn(c, available_width, height) 

                # Se o parágrafo inteiro couber no espaço restante da página atual
                if current_y - total_h >= bottom_margin:
                    body_paragraph.drawOn(c, text_start_x, current_y - total_h)
                    current_y -= total_h
                else:
                    # O parágrafo não cabe inteiro, precisa ser dividido
                    remaining_paragraph_obj = body_paragraph
                    
                    while remaining_paragraph_obj:
                        # Calcula o espaço vertical disponível na página atual (ou nova página)
                        space_on_page = current_y - bottom_margin
                        if space_on_page <= para_style.leading: # Não há espaço nem para uma linha
                            c.showPage()
                            current_y = height - top_margin
                            space_on_page = current_y - bottom_margin

                        # Tenta dividir o parágrafo restante para caber no espaço disponível
                        try:
                            parts = remaining_paragraph_obj.split(available_width, space_on_page)
                        except Exception: 
                            parts = [] 

                        if parts and len(parts) > 0:
                            part_to_draw = parts[0]
                            _, part_h = part_to_draw.wrapOn(c, available_width, space_on_page)
                            
                            part_to_draw.drawOn(c, text_start_x, current_y - part_h)
                            current_y -= part_h

                            if len(parts) > 1:
                                remaining_text_parts = []
                                for p_idx in range(1, len(parts)):
                                    if hasattr(parts[p_idx], 'text'):
                                        remaining_text_parts.append(parts[p_idx].text)
                                    elif isinstance(parts[p_idx], str):
                                        remaining_text_parts.append(parts[p_idx])
                                
                                remaining_text = "".join(remaining_text_parts)

                                if remaining_text.strip(): # Verifica se há texto útil
                                    remaining_paragraph_obj = Paragraph(remaining_text, para_style)
                                else:
                                    remaining_paragraph_obj = None 
                                
                                if remaining_paragraph_obj: 
                                    c.showPage()
                                    current_y = height - top_margin
                            else:
                                remaining_paragraph_obj = None
                        else:
                            if remaining_paragraph_obj: 
                                 _, h_rem = remaining_paragraph_obj.wrapOn(c, available_width, space_on_page)
                                 if h_rem <= space_on_page : 
                                    remaining_paragraph_obj.drawOn(c, text_start_x, current_y - h_rem)
                                    current_y -= h_rem
                            remaining_paragraph_obj = None 
            
            c.save()
            QMessageBox.information(self, "Sucesso", f"Evidência gerada em:\\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao gerar evidência:\\n{e}")