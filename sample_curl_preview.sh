curl -v -X POST "http://localhost:8000/v1/ai-content-agent/generate-preview" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "preview-gen-001",
    "content": "This months newsletter covers exciting updates including the launch of our new AI-powered analytics dashboard, team expansion announcements, and upcoming training sessions on the latest industry trends. We also feature employee spotlights and share insights from our recent customer success stories.",
    "user_prompt": "Make it catchy and encourage people to read more",
    "output_language": "en",
    "smtip_tid": "5d995f0f-d055-40e6-b6a1-b8b26cf217a2",
    "smtip_feature": "smart_answers",
    "model": "auto-route",
    "user_id": "test_user_preview_gen",
    "session_id": "preview_gen_session_001",
    "tags": ["preview-generation-test"]
  }'