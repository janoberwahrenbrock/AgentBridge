import asyncio
import pytest
from pydantic import BaseModel
from agent_sends import AgentSends

# Definiere Pydantic-Modelle. Das Attribut __test__ = False verhindert, dass pytest diese
# Klassen fälschlicherweise als Testklassen sammelt.
class TestModel1(BaseModel):
    __test__ = False
    content: str

class TestModel2(BaseModel):
    __test__ = False
    content: str

###############################################################################
# Testfälle für die Klasse AgentSends
###############################################################################

@pytest.mark.asyncio
async def test_successful_message_flow():
    """
    Testet den typischen Nachrichtenfluss:
      - Ein AgentSends-Objekt wird erzeugt.
      - Für TestModel1 wird ein Mediator über add() erstellt.
      - In einem separaten asynchronen Kontext wird über receiveFromAgent ein Listener
        registriert (dies gibt ein Future zurück, auf das gewartet werden kann).
      - Anschließend sendet agentSends() eine Nachricht vom Typ TestModel1.
      - Das Future sollte nun erfüllt werden; der empfangene Inhalt wird mit der gesendeten Nachricht verglichen.
    """
    agentSends = AgentSends()
    agentSends.add(TestModel1)  # Erstellt und speichert einen Mediator für TestModel1
    
    # Listener registrieren – diese Funktion gibt ein Future zurück, auf das gewartet werden kann.
    listener_task = asyncio.create_task(agentSends.receiveFromAgent(TestModel1)) #startet den Coroutine und gibt sofort ein Task-Objekt zurück
    
    # Kurze Verzögerung, damit sich der Listener registrieren kann
    await asyncio.sleep(0.1)
    
    # Sende eine Nachricht vom Typ TestModel1 über die AgentSends-Schnittstelle.
    msg = TestModel1(content="Hallo, Agent!")
    await agentSends.agentSends(msg)
    
    # Warte, bis der Listener das Future erfüllt hat und prüfe das Ergebnis.
    received_message = await listener_task
    assert received_message == msg, f"Erhaltene Nachricht {received_message} entspricht nicht {msg}"


@pytest.mark.asyncio
async def test_agentSends_without_mediator():
    """
    Testet, dass versucht wird, eine Nachricht zu senden, ohne dass zuvor ein Mediator 
    für den entsprechenden Modelltyp hinzugefügt wurde. In diesem Fall sollte ein ValueError ausgelöst werden.
    """
    agent = AgentSends()
    msg = TestModel1(content="Ohne Mediator")
    
    with pytest.raises(ValueError) as exc:
        await agent.agentSends(msg)
    assert "Kein Mediator gefunden" in str(exc.value)


@pytest.mark.asyncio
async def test_receive_without_mediator():
    """
    Testet, dass versucht wird, einen Listener zu registrieren (receiveFromAgent) für einen
    Modelltyp, für den noch kein Mediator hinzugefügt wurde. Hier sollte ebenfalls ein ValueError
    ausgelöst werden.
    """
    agent = AgentSends()
    
    with pytest.raises(ValueError) as exc:
        await agent.receiveFromAgent(TestModel1)
    assert "Kein Mediator gefunden" in str(exc.value)


@pytest.mark.asyncio
async def test_multiple_models():
    """
    Testet, dass AgentSends mehrere unterschiedliche Mediatoren korrekt verwaltet:
      - Es werden Mediatoren für TestModel1 und TestModel2 hinzugefügt.
      - Für beide Modelle werden separat Listener registriert.
      - Anschließend werden Nachrichten für beide Modelle gesendet.
      - Überprüft wird, dass beide Listener jeweils die korrekte Nachricht erhalten.
    """
    agent = AgentSends()
    agent.add(TestModel1)
    agent.add(TestModel2)
    
    listener1_task = asyncio.create_task(agent.receiveFromAgent(TestModel1))
    listener2_task = asyncio.create_task(agent.receiveFromAgent(TestModel2))
    
    # Kurze Verzögerung, damit sich beide Listener registrieren können.
    await asyncio.sleep(0.1)
    
    msg1 = TestModel1(content="Message for Model1")
    msg2 = TestModel2(content="Message for Model2")
    
    await agent.agentSends(msg1)
    await agent.agentSends(msg2)
    
    received_msg1 = await listener1_task
    received_msg2 = await listener2_task
    
    assert received_msg1 == msg1, f"Erwartet {msg1}, erhalten {received_msg1}"
    assert received_msg2 == msg2, f"Erwartet {msg2}, erhalten {received_msg2}"


@pytest.mark.asyncio
async def test_order_of_operations():
    """
    Testet, dass receiveFromAgent korrekt wartet, bis eine Nachricht über agentSends geliefert wird,
    auch wenn zwischen Registrierung des Listeners und dem Senden der Nachricht eine Verzögerung liegt.
    """
    agent = AgentSends()
    agent.add(TestModel1)
    
    # Registriere Listener und starte diesen in einer asynchronen Task.
    listener_future = asyncio.create_task(agent.receiveFromAgent(TestModel1))
    
    # Warte etwas, sodass der Listener im Wartezustand ist.
    await asyncio.sleep(0.2)
    
    msg = TestModel1(content="Verzögerte Operation")
    await agent.agentSends(msg)
    
    received_message = await listener_future
    assert received_message == msg, f"Erhaltene Nachricht {received_message} entspricht nicht {msg}"
