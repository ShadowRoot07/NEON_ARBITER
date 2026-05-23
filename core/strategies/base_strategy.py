from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """Clase abstracta para que todas las estrategias tengan la misma estructura."""

    @abstractmethod
    def analyze(self, buffer):
        """Debe retornar un diccionario con el contexto técnico analizado."""
        pass

    @abstractmethod
    def should_execute(self, analysis, climate_tuple, **kwargs):
        """
        Define el Gatillo Inteligente unificado. 
        Recibe el análisis técnico, la tupla de clima y kwargs dinámicos (muros, dominancia, etc.).
        Debe retornar una tupla: (str "BUY"/"SELL"/"HOLD", float confianza 0.0 a 1.0).
        """
        pass

