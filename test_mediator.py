import asyncio
import pytest
from pydantic import BaseModel

from .mediator import Mediator


### Pydantic-Modelle nach dem neuen Schema

class TestModel1(BaseModel):
    __test__ = False  # Pytest wird diese Klasse nicht als Test sammeln.
    content: str

class TestModel2(BaseModel):
    __test__ = False  # Pytest wird diese Klasse nicht als Test sammeln.
    content: str


### Hilfsfunktionen zur Simulation von asynchronen Service-Funktionen

async def listener_service(mediator: Mediator) -> asyncio.Future:
    """
    Simuliert eine asynchrone Funktion, die als "Listener" agiert.
    Sie registriert den Listener am übergebenen Mediator und gibt
    das zugehörige Future zurück.
    """
    return await mediator.register_listener()

async def sender_service(mediator: Mediator, message):
    """
    Simuliert eine asynchrone Funktion, die eine Nachricht übermittelt.
    Sie verwendet den übergebenen Mediator, um eine Nachricht zu senden.
    """
    await mediator.deliver_message(message)


### Unittests mit pytest und pytest-asyncio

# Test: Erfolgreiche Lieferung einer Nachricht mit dem erwarteten Modell (TestModel1)
@pytest.mark.asyncio
async def test_successful_delivery():
    # Erstelle das Mediator-Objekt in einer asynchronen Umgebung
    mediator = Mediator(model=TestModel1)
    
    # Übergebe den Mediator an eine asynchrone Listener-Funktion
    listener_future = await listener_service(mediator)
    
    # Übergebe den Mediator an einen asynchronen Sender, der eine gültige Nachricht verschickt
    await sender_service(mediator, TestModel1(content="Hallo, Welt!"))
    
    # Der Listener erhält das Future, welches nun die zugestellte Nachricht enthalten muss
    result = await listener_future
    assert result == TestModel1(content="Hallo, Welt!")


# Test: Asynchrone Kontextkommunikation zwischen separaten Funktionen
@pytest.mark.asyncio
async def test_async_context_communication():
    mediator = Mediator(model=TestModel1)
    
    async def listener_context(m: Mediator) -> TestModel1:
        # Registriere in einem separaten Kontext den Listener.
        fut = await listener_service(m)
        message = await fut
        return message

    async def sender_context(m: Mediator):
        # Sende die Nachricht mit einer kleinen Verzögerung, sodass der Listener Zeit zum Registrieren hat.
        await asyncio.sleep(0.1)
        await sender_service(m, TestModel1(content="Nachricht aus sender_context"))
    
    # Starte beide Kontexte als asynchrone Tasks.
    listener_task = asyncio.create_task(listener_context(mediator))
    sender_task = asyncio.create_task(sender_context(mediator))
    
    # Hole die vom Listener empfangene Nachricht und warte auf das Abschließen des Senders.
    received_message = await listener_task
    await sender_task
    
    # Überprüfe, ob die übermittelte Nachricht dem erwarteten Inhalt entspricht.
    assert received_message.content == "Nachricht aus sender_context"


# Test: Lieferung einer Nachricht mit falschem Modell soll einen Fehler werfen
@pytest.mark.asyncio
async def test_wrong_message_model():
    mediator = Mediator(model=TestModel1)
    
    # Registriere den Listener in einer separaten asynchronen Funktion
    await listener_service(mediator)
    
    # Versuche, eine Nachricht mit dem falschen Modell (TestModel2) über eine asynchrone Sender-Funktion zu liefern;
    # dabei sollte ein ValueError ausgelöst werden.
    with pytest.raises(ValueError):
        await sender_service(mediator, TestModel2(content="Falsches Modell"))


# Test: Es darf immer nur ein Listener zur gleichen Zeit registriert sein.
@pytest.mark.asyncio
async def test_single_listener():
    mediator = Mediator(model=TestModel1)
    
    # Registriere den ersten Listener über eine separate asynchrone Funktion.
    await listener_service(mediator)
    
    # Der Versuch, einen zweiten Listener in einem anderen asynchronen Kontext zu registrieren, soll einen ValueError verursachen.
    with pytest.raises(ValueError):
        await listener_service(mediator)


# Test: deliver_message wartet, bis ein Listener registriert wird – Nutzung separater asynchroner Funktionen
@pytest.mark.asyncio
async def test_delivery_waits_for_listener():
    mediator = Mediator(model=TestModel1)
    
    # Diese asynchrone Funktion simuliert den Sender-Kontext, der versucht, eine Nachricht zu senden,
    # bevor ein Listener registriert wird.
    async def delayed_sender():
        # Kleine Verzögerung, damit der Sender startet, bevor der Listener aktiv wird.
        await asyncio.sleep(0.1)
        await sender_service(mediator, TestModel1(content="Verzögerte Nachricht"))
    
    # Starte den Sender als asynchrone Aufgabe.
    sender_task = asyncio.create_task(delayed_sender())
    
    # Warte kurz, damit sich der Sender in die Warteschleife einpendeln kann.
    await asyncio.sleep(0.2)
    
    # Vor der Registrierung des Listeners sollte der Sender-Task noch nicht abgeschlossen sein.
    assert not sender_task.done(), "Sender sollte noch warten, bis der Listener registriert ist"
    
    # Registriere nun in einem separaten asynchronen Kontext den Listener.
    listener_future = await listener_service(mediator)
    
    # Warte, bis der Sender seine Arbeit beendet hat.
    await sender_task
    
    # Hole das Ergebnis vom Future und überprüfe, ob die Nachricht korrekt übermittelt wurde.
    result = await listener_future
    assert result.content == "Verzögerte Nachricht"