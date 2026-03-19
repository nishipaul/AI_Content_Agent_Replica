curl -v -X POST "http://localhost:8000/v1/ai-content-agent/generate-title" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "title-gen-001",
    "content": "Our company announced record-breaking revenue growth in Q1 2026, driven by strong performance in cloud services and AI solutions. CEO Jane Smith highlighted the teams dedication and innovation as key factors in achieving these results.",
    "user_prompt": "Make it professional and engaging",
    "output_language": "en",
    "smtip_tid": "5d995f0f-d055-40e6-b6a1-b8b26cf217a2",
    "smtip_feature": "smart_answers",
    "model": "auto-route",
    "user_id": "test_user_title_gen",
    "session_id": "title_gen_session_001",
    "tags": ["title-generation-test"]
  }'