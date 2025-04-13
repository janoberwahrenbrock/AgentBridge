from typing import Dict, Type
from pydantic import BaseModel
from mediator import Mediator

class AgentSends:
    """
    Diese Klasse verwaltet mehrere Mediator-Objekte für unterschiedliche Pydantic-Modelle.
    
    - add(model: Type[BaseModel]):
      Erzeugt ein Mediator-Objekt für den angegebenen Pydantic-Modelltyp und speichert dieses intern
      unter dem Schlüssel model.__name__.
      
    - agentSends(message: BaseModel):
      Nimmt eine konkrete Instanz eines Pydantic-Modells entgegen, ermittelt anhand des Namens des Modells 
      das zugehörige Mediator-Objekt und ruft dessen Funktion deliver_message(message) auf, um 
      die Nachricht zu übermitteln.
      
    - receiveFromAgent(model: Type[BaseModel]):
      Sucht nach dem Mediator-Objekt, das für den angegebenen Modelltyp verwaltet wird, ruft register_listener()
      auf, wartet bis das zugehörige Future erfüllt ist, und gibt dann die zugestellte Nachricht (eine Instanz des
      entsprechenden Pydantic-Modells) zurück.
    """
    def __init__(self):
        # Internes Dictionary, das die Mediator-Objekte speichert:
        # Schlüssel: Name des Modells (str) / Wert: Mediator-Objekt
        self.mediators: Dict[str, Mediator] = {}

    def add(self, model: Type[BaseModel]):
        """
        Erzeugt ein Mediator-Objekt für den angegebenen Pydantic-Modelltyp und speichert dieses intern.
        
        :param model: Ein Pydantic-Modell (Klasse), das den Typ der Nachrichten definiert.
        """
        mediator = Mediator(model=model)
        self.mediators[model.__name__] = mediator

    async def agentSends(self, message: BaseModel):
        """
        Empfängt eine konkrete Instanz eines Pydantic-Modells, ermittelt anhand des Modellnamens
        das entsprechende Mediator-Objekt und ruft dessen deliver_message-Funktion auf, um die Nachricht zu übermitteln.
        
        :param message: Eine Instanz eines Pydantic-Modells.
        :raises ValueError: Falls für den Modellnamen kein Mediator-Objekt gefunden wird.
        """
        model_name = message.__class__.__name__
        mediator = self.mediators.get(model_name)
        if mediator is None:
            raise ValueError(f"Kein Mediator gefunden für Modell: {model_name}")
        await mediator.deliver_message(message)

    async def receiveFromAgent(self, model: Type[BaseModel]):
        """
        Sucht das Mediator-Objekt, welches für den angegebenen Pydantic-Modelltyp registriert wurde,
        und ruft register_listener() auf, um ein Future zu erhalten. Anschließend wartet die Funktion,
        bis dieses Future erfüllt ist, und gibt dann die zugestellte Nachricht zurück.
        
        :param model: Ein Pydantic-Modell (Klasse), dessen zugehöriger Mediator gesucht wird.
        :return: Eine Instanz des Pydantic-Modells, das bei Zustellung geliefert wurde.
        :raises ValueError: Falls für den Modelltyp kein Mediator-Objekt gefunden wird.
        """
        mediator = self.mediators.get(model.__name__)
        if mediator is None:
            raise ValueError(f"Kein Mediator gefunden für Modell: {model.__name__}")
        # Zuerst holen wir uns das Future, das durch register_listener zurückgegeben wird.
        listener_future = await mediator.register_listener()
        # Anschließend warten wir darauf, dass dieses Future erfüllt wird und erhalten so die Nachricht.
        return await listener_future