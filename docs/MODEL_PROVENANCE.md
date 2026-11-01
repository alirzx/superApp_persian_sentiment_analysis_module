# Pretrained models, trust, revisions and attribution

## Sentiment
HF: https://huggingface.co/m3hrdadfi/albert-fa-base-v2-sentiment-multi
- Architecture: ALBERT Persian / sequence classification, `AlbertForSequenceClassification`.
- Original labels from config: `0=Negative`, `1=Neutral`, `2=Positive`.
- Task: Persian sentiment (reviews including Digikala, SnappFood and SentiPers).
- Model card reports F1 70.72 for a combined three-class sentiment dataset; not evaluated on SuperApp inputs.
- File `pytorch_model.bin` approximately 72.3 MB; storage size is **not RAM or latency**.
- Declared license: Apache-2.0; verify terms and dataset usage independently before commercial distribution.

## Topics
HF: https://huggingface.co/m3hrdadfi/albert-fa-base-v2-clf-persiannews
- Architecture: ALBERT Persian / sequence classification.
- Original labels by index: `اجتماعی`, `اقتصادی`, `بین الملل`, `سیاسی`, `علمی فناوری`, `فرهنگی هنری`, `ورزشی`, `پزشکی`.
- Task: eight-class Persian news categorization, not arbitrary topic/intent classification.
- Model card reports an F1 of 97.01 on its Persian news test set; not evaluated on SuperApp inputs.
- File `pytorch_model.bin` approximately 72.4 MB.
- Declared license: Apache-2.0; independent review required before commercial deployment.

## Model acquisition

`models.json` contains repository IDs, approved original label orders, and maximum sequence lengths. The pinned source commit is acquired from `HfApi.model_info` at the first **explicit** `make model` operation, and recorded in each model's persistent SHA256 manifest. The source is never loaded into the API container. The model-setup container downloads only named required files, not arbitrary remote source scripts or repository code.

**Known supply-chain boundary:** Upstream publishes PyTorch `.bin` checkpoints (pickle). The one-shot setup container loads them inside an isolated build step to export ONNX. Using `trust_remote_code=False` prevents custom HF model code execution but does not make loading pickle untrusted weights safe by itself. The publisher's identity/artifact should be independently checked, and conversion should occur in restricted infrastructure with no secrets. Add a verified original `.bin` digest and full HF source revision to the deployment approval checklist.

Export uses opset 17, dynamic batch and token axes. Numerical comparison is checked against PyTorch on two Persian examples, followed by a shorter sequence run. ONNX artifacts, tokenizer files and model configs are hashed. The API verifies each hash and enforces the expected `id2label` ordering before readiness.

`MODEL_SENTIMENT_REVISION` and `MODEL_TOPICS_REVISION` should be set to the exact 40-character SHAs on the production server. The model prep does not automatically overwrite an already valid cache. Force an upgrade only with `make model-refresh` and rerun tests/benchmarks.

No project model weights are committed to Git. No model artifact is bundled in the downloadable source ZIP. Commercial release still requires approval of model weights, training data, dependencies and any local restrictions.
