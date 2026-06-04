from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """Clase abstracta para que todas las estrategias tengan la misma estructura."""

    @abstractmethod
    def analyze(self, buffer, *args, **kwargs):
        """Retorna el análisis técnico/contextual del mercado."""
        pass

    @abstractmethod
    def should_execute(self, analysis, climate, *args, **kwargs):
        """Define las reglas y filtros de seguridad para disparar órdenes."""
        pass
