curl -v -X POST "http://localhost:8000/v1/ai-content-agent/chat-summarise" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "chat-sum-001",
    "messages": [
      {
        "message_id": "msg-001",
        "sender_name": "Alice",
        "timestamp": "2026-03-18T10:00:00Z",
        "text": "Hey team, we need to discuss the Q2 roadmap"
      },
      {
        "message_id": "msg-002",
        "sender_name": "Bob",
        "timestamp": "2026-03-18T10:05:00Z",
        "text": "Agreed. I think we should prioritize the mobile app features",
        "replied_to": "msg-001"
      },
      {
        "message_id": "msg-003",
        "sender_name": "Carol",
        "timestamp": "2026-03-18T10:10:00Z",
        "text": "I can lead the mobile effort. Lets schedule a planning meeting for next week",
        "replied_to": "msg-002"
      }
    ],
    "language": "en",
    "smtip_tid": "5d995f0f-d055-40e6-b6a1-b8b26cf217a2",
    "smtip_feature": "smart_answers",
    "model": "auto-route",
    "user_id": "test_user_chat_summary",
    "session_id": "chat_summary_session_001",
    "tags": ["chat-summarisation-test"]
  }'