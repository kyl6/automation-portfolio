# AI review & customer message triage

Saves a store owner the first pass through product reviews and customer messages. Classifies complaint, shipping issue, refund request, praise or question; assigns high/medium/low priority and drafts a short reply. Kyle is an AI automation builder who builds with AI tools. Chat-only, no calls.

## Offline sample

```sh
python3 demo3-review-message-triage/triage.py
```

Run from the repository root. [18 fake messages](sample_messages.csv) use fictional Shopify, TikTok Shop and Amazon channel labels. No real customers or reviews are represented. Output goes to `output/triage.csv`; [saved sample output](sample_triage.csv) was generated in **rule-based mode**, not by an LLM. Every row records its mode and requires human review.

Rules prioritize refund requests, then shipping issues, complaints, questions and praise. Unknown text becomes a question; urgent/safety keywords raise priority. Rules cannot reliably interpret sarcasm, negation, multilingual messages or every mixed intent. These drafts need review; nothing sends messages, issues refunds or changes orders.

## Optional LLM mode

Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in your environment, then:

```sh
python3 demo3-review-message-triage/triage.py --llm --output output/triage_llm.csv
```

This sends message text to a paid API. Anthropic takes precedence when both keys are set. Defaults are `claude-haiku-4-5-20251001` and `gpt-4.1-mini`; override with `ANTHROPIC_MODEL` or `OPENAI_MODEL` for a model enabled on your account. Uses the [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages) or OpenAI Chat Completions with JSON output. Keys alone never activate LLM mode. Missing keys, network errors and invalid responses fail explicitly rather than silently switching modes. Replies are schema-checked, not fact-verified; review against store policy before sending. Live LLM requests were not run; API request/response handling is tested with offline mocks.

Custom input uses `--input messages.csv`; required columns are `id,channel,message`, with optional `data_label`. Output escapes spreadsheet formula prefixes. Store real data and keys outside the public sample folders.

## Loom script

- Show the 18 fake messages and describe the seller's sorting task.
- Run the default offline mode and point out the rule-based label.
- Show the five categories, priorities and short reply drafts.
- Explain optional AI mode and why every draft needs a person to check it.
- Close with chat-only scoping around the store's message types and reply policies.
