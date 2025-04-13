import asyncio
from typing import Optional, Type
from pydantic import BaseModel

class Mediator:
    """
    Dieser Mediator erlaubt es, dass sich genau ein Listener registrieren kann,
    um auf eine Nachricht (vom Typ des übergebenen Pydantic-Modells) zu warten.
    Sobald eine Nachricht übergeben wird, wird das Future des registrierten Listeners erfüllt und zurückgesetzt.
    Zusätzlich wird bei der Nachrichtenzustellung überprüft, ob diese vom richtigen Typ ist.
    """
    def __init__(self, model: Type[BaseModel]):
        """
        :param model: Ein Pydantic-Modell, das den erwarteten Typ der Nachrichten definiert.
        """
        self._model = model
        self._listener: Optional[asyncio.Future] = None
        self._listener_condition = asyncio.Condition()

    async def register_listener(self) -> asyncio.Future:
        """
        Registriert einen Listener, der auf eine Nachricht wartet.
        Es darf immer nur ein Listener zur gleichen Zeit registriert sein.
        
        :return: Ein Future, das mit einer Nachricht (Instanz des Pydantic-Modells) 
                erfüllt wird, sobald diese geliefert wird.
        :raises ValueError: Falls bereits ein Listener registriert ist.
        """
        # Betritt einen kritischen Bereich, in dem der Zugriff auf den internen Status 
        # (hier: self._listener) synchronisiert wird. Das Condition-Objekt verwendet intern 
        # einen Lock, der verhindert, dass mehrere Tasks gleichzeitig diesen Codeabschnitt ausführen.
        async with self._listener_condition:
            
            # Überprüfen, ob bereits ein Listener registriert wurde (also ob self._listener 
            # bereits gesetzt ist). Da nur ein Listener gleichzeitig existieren darf, wird bei 
            # Vorhandensein ein ValueError ausgelöst.
            if self._listener is not None:
                raise ValueError("Ein Listener ist bereits registriert!")
            
            # Erstellen eines neuen Future-Objekts mithilfe des aktuellen Event-Loops.
            # Ein Future ist ein Platzhalter für ein Ergebnis, das asynchron bereitgestellt 
            # wird. Es startet im "pending"-Zustand und kann später mit einem Ergebnis 
            # (oder einer Exception) vervollständigt werden.
            self._listener = asyncio.get_running_loop().create_future()
            
            # Mit notify_all() werden alle Tasks benachrichtigt, die derzeit in einem 
            # await self._listener_condition.wait() hängen. Dieser Aufruf signalisiert, 
            # dass sich der Zustand verändert hat – in diesem Fall wurde ein Listener registriert.
            # Obwohl alle wartenden Tasks aufgeweckt werden, betreten sie den kritischen 
            # Abschnitt nacheinander, da das Condition-Objekt einen Lock verwendet.
            self._listener_condition.notify_all()
            
            # Das erstellte Future wird zurückgegeben. Der Aufrufer dieser Methode erhält 
            # das Future und kann darauf mittels await warten, bis es durch einen anderen Task 
            # (über deliver_message) mit einem Ergebnis vervollständigt wird.
            return self._listener

    async def deliver_message(self, message):
        """
        Übermittelt die Nachricht an den registrierten Listener.
        Falls aktuell kein Listener registriert ist, wird gewartet,
        bis ein Listener verfügbar wird.
        Außerdem wird geprüft, ob die Nachricht eine Instanz des erwarteten Pydantic-Modells ist.
        
        :param message: Die Nachricht, die geliefert werden soll.
        :raises ValueError: Falls die Nachricht nicht vom Typ des übergebenen Pydantic-Modells ist.
        """
        # Zuerst wird überprüft, ob die übergebene Nachricht eine Instanz des erwarteten 
        # Pydantic-Modells (self._model) ist. Falls nicht, wird ein ValueError ausgelöst.
        if not isinstance(message, self._model):
            raise ValueError(f"Die Nachricht ist nicht vom erwarteten Typ {self._model.__name__}!")
        
        # Betreten des kritischen Abschnitts: Hier wird wieder das Condition-Objekt verwendet, 
        # um synchron auf den internen Zustand (self._listener) zuzugreifen.
        async with self._listener_condition:
            # Während keine Listener-Registrierung stattgefunden hat (d.h. self._listener noch None ist),
            # wartet der Task. Hierbei wird await self._listener_condition.wait() aufgerufen, welches:
            #   1. Den Task in einen wartenden Zustand versetzt, bis notify_all() ihn aufweckt.
            #   2. Gleichzeitig den Lock freigibt, damit andere Tasks (z. B. register_listener) 
            #      den kritischen Abschnitt betreten und den Zustand verändern können.
            while self._listener is None:
                await self._listener_condition.wait()
            
            # Sobald der Task aus der Warteschleife fortgesetzt wird – d.h. ein Listener registriert wurde –, 
            # wird überprüft, ob das Future noch nicht vervollständigt (done) ist.
            # Dies stellt sicher, dass das Ergebnis nicht mehrfach gesetzt wird.
            if not self._listener.done():
                # Das Future wird mit dem Wert der Nachricht vervollständigt.
                # Dadurch wird der Task, der auf das Future wartet (über await), aus seinem Warten geholt 
                # und erhält diese Nachricht als Ergebnis.
                self._listener.set_result(message)
            
            # Nachdem die Nachricht erfolgreich zugestellt wurde, wird self._listener zurückgesetzt (auf None)
            # um anzuzeigen, dass aktuell kein Listener mehr registriert ist.
            self._listener = None