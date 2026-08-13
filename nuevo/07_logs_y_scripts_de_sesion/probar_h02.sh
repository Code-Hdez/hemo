#!/bin/bash
cd backend || exit 125
APP_ENV=test DATABASE_URL="postgresql://x:x@localhost/x" \
SECRET_KEY="ci-test-secret-key-0123456789abcdef" \
python3 -m pytest tests/llm_chat/test_structured_send_chat_message.py::test_transition_claim_cannot_carry_a_number -q >/dev/null 2>&1
