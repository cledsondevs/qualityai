import xml.etree.ElementTree as ET
import json
import re

class UIParser:
    """Consome XML bruto do Appium e gera uma representação mínima e semântica."""

    def __init__(self):
        # Atributos que realmente importam para identificar elementos e interagir
        self.essential_attrs = ["resource-id", "content-desc", "text", "checkable", "scrollable"]
        # Classes comuns que queremos mapear para tipos amigáveis
        self.class_map = {
            "android.widget.EditText": "input",
            "android.widget.Button": "button",
            "android.widget.ImageButton": "button",
            "android.widget.TextView": "text",
            "android.view.ViewGroup": "container",
            "android.widget.CheckBox": "checkbox",
            "android.widget.Switch": "switch"
        }

    def parse_to_json(self, xml_source: str) -> str:
        """Converte XML filtrado para JSON string compacta."""
        try:
            root = ET.fromstring(xml_source)
            elements = self._extract_interactive_elements(root)
            return json.dumps(elements, ensure_ascii=False, separators=(',', ':'))
        except Exception as e:
            return json.dumps({"error": f"Failed to parse XML: {str(e)}"})

    def _extract_interactive_elements(self, node):
        interactive_elements = []
        
        # Atributos de interação
        is_clickable = node.get("clickable") == "true"
        is_long_clickable = node.get("long-clickable") == "true"
        is_scrollable = node.get("scrollable") == "true"
        has_text = bool(node.get("text"))
        has_desc = bool(node.get("content-desc"))
        
        # Se o elemento for interativo ou contiver informação legível
        if is_clickable or is_long_clickable or is_scrollable or has_text or has_desc:
            el_data = {}
            
            # Mapeia tipo
            node_class = node.get("class", "")
            el_data["type"] = self.class_map.get(node_class, "element")
            
            # Adiciona apenas atributos existentes e não vazios
            for attr in self.essential_attrs:
                val = node.get(attr)
                if val and val != "false":
                    # Limpa resource-id para ficar mais curto (remove o pacote)
                    if attr == "resource-id":
                        val = val.split("/")[-1]
                    el_data[attr] = val
            
            # Se não sobrou nada útil além do tipo, ignora se não for clicável
            if len(el_data) <= 1 and not is_clickable:
                pass
            else:
                interactive_elements.append(el_data)

        # Recursão para filhos
        for child in node:
            interactive_elements.extend(self._extract_interactive_elements(child))
            
        return interactive_elements

# Instância global sugerida para o core
ui_parser = UIParser()
