#!/bin/bash

curl -v -X POST "http://localhost:8000/v1/ai-content-agent/summarize-content" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "content-sum-001",
    "content": "Artificial Intelligence and Machine Learning have revolutionized the technology landscape in recent years. Companies across various industries are leveraging AI to improve efficiency, enhance customer experiences, and drive innovation. From predictive analytics in healthcare to personalized recommendations in e-commerce, AI applications are becoming increasingly sophisticated. Machine learning algorithms can now process vast amounts of data to identify patterns and make intelligent decisions. Deep learning, a subset of machine learning, has enabled breakthroughs in computer vision, natural language processing, and speech recognition. As AI technology continues to advance, organizations must address ethical considerations, data privacy concerns, and the need for responsible AI development. The future of AI promises even more transformative possibilities, including autonomous systems, advanced robotics, and human-AI collaboration.",
    "mode": "concise",
    "company_name": "TechCorp",
    "industry": "Technology",
    "company_description": "A leading technology company focused on AI solutions and digital transformation.",
    "output_language": "en",
    "smtip_tid": "5d995f0f-d055-40e6-b6a1-b8b26cf217a2",
    "smtip_feature": "smart_answers",
    "model": "auto-route",
    "user_id": "test_user_content_sum",
    "session_id": "content_sum_session_001",
    "tags": ["content-summarization-test"]
  }'
