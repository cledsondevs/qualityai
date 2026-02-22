import hashlib
import json

class UIHasher:
    """Gera identificadores únicos (hashes) para estados de tela baseados na UI minificada."""

    def calculate_hash(self, minified_ui_json: str) -> str:
        """
        Gera um hash SHA-256 da string JSON da UI.
        Útil para detectar se a tela mudou ou se estamos presos na mesma view.
        """
        try:
            # Normalizamos o JSON antes do hash para garantir determinismo
            data = json.loads(minified_ui_json)
            normalized = json.dumps(data, sort_keys=True)
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        except:
            # Fallback seguro caso o JSON falhe
            return hashlib.sha256(minified_ui_json.encode('utf-8')).hexdigest()

    def has_changed(self, old_hash: str, new_hash: str) -> bool:
        """Compara dois hashes de tela."""
        return old_hash != new_hash

# Instância global
ui_hasher = UIHasher()
