from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """Clase abstracta para que todas las estrategias tengan la misma estructura."""
    
    @abstractmethod
    def analyze(self, buffer):
        """Debe retornar un diccionario con el contexto para la IA."""
        pass

    @abstractmethod
    def should_execute(self, signal, confidence):
        """Define los filtros de seguridad (ej. confianza > 0.7)."""
        pass

