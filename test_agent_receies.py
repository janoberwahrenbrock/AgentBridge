import asyncio
import pytest
from pydantic import BaseModel

from .agent_receives import AgentReceives


# Definiere Pydantic-Modelle.
# Mit __test__ = False wird verhindert, dass pytest diese Klassen fälschlicherweise als Testklassen sammelt.
class TestModel1(BaseModel):
    __test__ = False
    content: str

class TestModel2(BaseModel):
    __test__ = False
    content: str

###############################################################################
# Testfälle für die Klasse AgentReceives
###############################################################################


@pytest.mark.asyncio
async def test_successful_message_flow():
    """
    Testet den typischen Nachrichtenfluss:
      - Ein AgentReceives-Objekt wird erzeugt.
      - Für TestModel1 wird ein Mediator über add() erstellt.
      - In einem separaten asynchronen Kontext registriert agentReceives() einen Listener,
        der auf eine Nachricht wartet.
      - Anschließend sendet sendToAgent() eine Nachricht vom Typ TestModel1.
      - Der Listener wartet, bis das Future erfüllt wird, und gibt dann den tatsächlichen
        Nachrichteninhalt zurück, der mit der gesendeten Nachricht verglichen wird.
    """
    agentReceives = AgentReceives()
    agentReceives.add(TestModel1)  # Erstellt und speichert einen Mediator für TestModel1

    # Listener registrieren – this startet den Coroutine und gibt ein Task-Objekt zurück.
    listener_task = asyncio.create_task(agentReceives.agentReceives(TestModel1))
    
    # Kurze Verzögerung, damit sich der Listener registrieren kann.
    await asyncio.sleep(0.1)
    
    # Sende eine Nachricht vom Typ TestModel1 über die AgentReceives-Schnittstelle.
    msg = TestModel1(content="Hallo, Agent!")
    await agentReceives.sendToAgent(msg)
    
    # Warte, bis der Listener das Future erfüllt hat und hole den tatsächlichen Nachrichteninhalt.
    received_message = await listener_task
    assert received_message == msg, f"Erhaltene Nachricht {received_message} entspricht nicht {msg}"


@pytest.mark.asyncio
async def test_sendToAgent_without_mediator():
    """
    Testet, dass versucht wird, eine Nachricht zu senden, ohne dass zuvor ein Mediator
    für den entsprechenden Modelltyp hinzugefügt wurde. In diesem Fall soll ein ValueError ausgelöst werden.
    """
    agent = AgentReceives()
    msg = TestModel1(content="Ohne Mediator")
    
    with pytest.raises(ValueError) as exc:
        await agent.sendToAgent(msg)
    assert "Kein Mediator gefunden" in str(exc.value)


@pytest.mark.asyncio
async def test_agentReceives_without_mediator():
    """
    Testet, dass versucht wird, einen Listener zu registrieren (agentReceives) für einen
    Modelltyp, für den noch kein Mediator hinzugefügt wurde. Hier sollte ein ValueError ausgelöst werden.
    """
    agent = AgentReceives()
    
    with pytest.raises(ValueError) as exc:
        await agent.agentReceives(TestModel1)
    assert "Kein Mediator gefunden" in str(exc.value)


@pytest.mark.asyncio
async def test_multiple_models():
    """
    Testet, dass AgentReceives mehrere unterschiedliche Mediatoren korrekt verwaltet:
      - Es werden Mediatoren für TestModel1 und TestModel2 hinzugefügt.
      - Für beide Modelle werden separat Listener registriert.
      - Anschließend werden Nachrichten für beide Modelle gesendet.
      - Überprüft wird, dass beide Listener jeweils die korrekte Nachricht erhalten.
    """
    agent = AgentReceives()
    agent.add(TestModel1)
    agent.add(TestModel2)
    
    listener1_task = asyncio.create_task(agent.agentReceives(TestModel1))
    listener2_task = asyncio.create_task(agent.agentReceives(TestModel2))
    
    # Kurze Verzögerung, damit sich beide Listener registrieren können.
    await asyncio.sleep(0.1)
    
    msg1 = TestModel1(content="Message for Model1")
    msg2 = TestModel2(content="Message for Model2")
    
    await agent.sendToAgent(msg1)
    await agent.sendToAgent(msg2)
    
    received_msg1 = await listener1_task
    received_msg2 = await listener2_task
    
    assert received_msg1 == msg1, f"Erwartet {msg1}, erhalten {received_msg1}"
    assert received_msg2 == msg2, f"Erwartet {msg2}, erhalten {received_msg2}"


@pytest.mark.asyncio
async def test_order_of_operations():
    """
    Testet, dass agentReceives korrekt wartet, bis eine Nachricht über sendToAgent geliefert wird,
    auch wenn zwischen Registrierung des Listeners und dem Senden der Nachricht eine Verzögerung liegt.
    """
    agent = AgentReceives()
    agent.add(TestModel1)
    
    # Registriere den Listener in einer asynchronen Task.
    listener_task = asyncio.create_task(agent.agentReceives(TestModel1))
    
    # Warte etwas, sodass der Listener im Wartezustand ist.
    await asyncio.sleep(0.2)
    
    msg = TestModel1(content="Verzögerte Operation")
    await agent.sendToAgent(msg)
    
    received_message = await listener_task
    assert received_message == msg, f"Erhaltene Nachricht {received_message} entspricht nicht {msg}"
