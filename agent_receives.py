from typing import Dict, Type
from pydantic import BaseModel
import asyncio
from mediator import Mediator

class AgentReceives:
    """
    Diese Klasse verwaltet mehrere Mediator-Objekte für unterschiedliche Pydantic-Modelle.
    
    - add(model: Type[BaseModel]):
      Erzeugt ein Mediator-Objekt für den angegebenen Pydantic-Modelltyp und speichert dieses intern
      unter dem Schlüssel model.__name__.
      
    - agentReceives(model: Type[BaseModel]):
      Sucht nach dem Mediator-Objekt, das für den angegebenen Modelltyp verwaltet wird, ruft dessen
      register_listener() auf, wartet bis das zugehörige Future erfüllt ist und gibt dann die zugestellte
      Nachricht (eine Instanz des entsprechenden Pydantic-Modells) zurück.
      
    - sendToAgent(message: BaseModel):
      Nimmt eine konkrete Instanz eines Pydantic-Modells entgegen, ermittelt anhand des Namens des Modells 
      das zugehörige Mediator-Objekt und ruft dessen deliver_message(message) auf, um die Nachricht zu übermitteln.
    """
    def __init__(self):
        # Internes Dictionary, in dem Mediator-Objekte gespeichert werden.
        # Der Schlüssel ist der Name des Modells (z.B. "MyModel") und der Wert ist ein Mediator-Objekt.
        self.mediators: Dict[str, Mediator] = {}

    def add(self, model: Type[BaseModel]):
        """
        Erzeugt ein Mediator-Objekt für den angegebenen Pydantic-Modelltyp und speichert es intern.
        
        :param model: Ein Pydantic-Modell (Klasse), das den Typ der Nachrichten definiert.
        """
        mediator = Mediator(model=model)
        self.mediators[model.__name__] = mediator

    async def agentReceives(self, model: Type[BaseModel]):
        """
        Sucht nach dem Mediator-Objekt, das für den angegebenen Pydantic-Modelltyp verwaltet wird,
        ruft dessen register_listener() auf, wartet bis das zugehörige Future erfüllt ist, und gibt dann
        die empfangene Nachricht zurück.
        
        :param model: Ein Pydantic-Modell (Klasse), dessen zugehöriger Mediator gesucht wird.
        :return: Eine Instanz des Pydantic-Modells, das beim Empfang geliefert wurde.
        :raises ValueError: Falls kein entsprechender Mediator gefunden wird.
        """
        mediator = self.mediators.get(model.__name__)
        if mediator is None:
            raise ValueError(f"Kein Mediator gefunden für Modell: {model.__name__}")
        # Holen des Futures, das beim Registrieren des Listeners entsteht.
        listener_future = await mediator.register_listener()
        # Warten, bis das Future erfüllt ist, und Rückgabe der zugestellten Nachricht.
        return await listener_future

    async def sendToAgent(self, message: BaseModel):
        """
        Nimmt eine konkrete Instanz eines Pydantic-Modells entgegen, ermittelt anhand des Namens des Modells
        das zugehörige Mediator-Objekt und ruft dessen deliver_message(message) auf, um die Nachricht zu übermitteln.
        
        :param message: Eine Instanz eines Pydantic-Modells.
        :raises ValueError: Falls für den Modellnamen kein Mediator-Objekt gefunden wird.
        """
        model_name = message.__class__.__name__
        mediator = self.mediators.get(model_name)
        if mediator is None:
            raise ValueError(f"Kein Mediator gefunden für Modell: {model_name}")
        await mediator.deliver_message(message)
