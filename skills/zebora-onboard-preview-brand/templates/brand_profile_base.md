Brand profile: {{TARGET}}

Target brand:
{{TARGET}}

Market:
{{MARKET}}

About {{TARGET}} in this category:
{{ABOUT}}

Canonical target brand output:
Only {{TARGET}} reporting entities may use brand = "{{TARGET}}".
Competitor entities must use their own canonical provider label, never {{TARGET}}.
For competitor rows, target_brand must be false and competitor_type must not be "target".
For target rows, target_brand=true and competitor_type="target" is correct.

Brand naming (one target entity):
{{TARGET_ALIASES}} ALL map to ONE reporting entity:
  brand = "{{TARGET}}", entity = "{{TARGET}}"
Preserve source_text exactly. Do not create a separate entity per {{TARGET}} product or plan.

Do-not-default rule (critical):
Do NOT attribute a provider or product to {{TARGET}} merely because {{TARGET}} is mentioned in the same
response, row or table. Every other provider must use its own brand with target_brand=false and
competitor_type != "target".
