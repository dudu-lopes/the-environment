"""
Multi-agent communication example using the Environment.

This example demonstrates:
- Creating multiple agent identities
- Joining an environment with capabilities
- Discovering agents by capability
- Sending direct messages and broadcasts
- Receiving messages
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ment import create_identity, Message, Environment

# Create three agents with different capabilities
agent_a = create_identity("password-a")
agent_b = create_identity("password-b")
agent_c = create_identity("password-c")

print("=== Agent Identities ===")
print(f"Agent A: {agent_a.id}")
print(f"Agent B: {agent_b.id}")
print(f"Agent C: {agent_c.id}")
print()

# Create an environment
env = Environment(default_ttl_ms=60_000)

# Agents join the environment with their capabilities
presence_a = env.join(agent_a.id, capabilities=["code", "search"])
presence_b = env.join(agent_b.id, capabilities=["search"])
presence_c = env.join(agent_c.id, capabilities=["code", "analyze"])

print("=== Agent Capabilities ===")
print(f"Agent A: {presence_a.capabilities}")
print(f"Agent B: {presence_b.capabilities}")
print(f"Agent C: {presence_c.capabilities}")
print()

# Discover agents with specific capabilities
search_agents = env.discover("search")
print(f"=== Agents with 'search' capability ===")
for agent in search_agents:
    print(f"  - {agent.agent_id}: {agent.capabilities}")
print()

# Send a direct message from A to B
message_ab = env.send(agent_a.id, {"text": "Hello B!"}, target_id=agent_b.id)
print(f"=== Message sent from A to B ===")
print(f"Content: {message_ab.content}")
print(f"Target: {message_ab.target_id}")
print()

# Send a broadcast from A
broadcast = env.send(agent_a.id, {"text": "Hello everyone!"})
print(f"=== Broadcast from A ===")
print(f"Content: {broadcast.content}")
print(f"Target: {broadcast.target_id} (None = broadcast)")
print()

# Receive messages
print("=== Message Boxes ===")
messages_b = env.receive(agent_b.id)
messages_c = env.receive(agent_c.id)
print(f"Agent B received: {[m.content for m in messages_b]}")
print(f"Agent C received: {[m.content for m in messages_c]}")
print()

# Verify messages are cleared
messages_b_again = env.receive(agent_b.id)
print(f"Agent B receives again (should be empty): {messages_b_again}")
