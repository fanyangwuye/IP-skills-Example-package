# PoYo Provider Notes

Current confirmed endpoints:

- Submit generation task: `POST /api/generate/submit`
- Query task status: `GET /api/generate/status/{task_id}`
- Upload local file: `POST /api/common/upload/stream`

Confirmed models:

- `gpt-image-2`
- `gpt-image-2-edit`

Important constraints:

- Generated result URLs expire after 24 hours
- Uploaded image URLs expire after 72 hours
- Image uploads are limited to 5 requests per minute per API key

Implementation notes:

- Always download finished outputs immediately
- Treat provider URLs as temporary transport URLs, not persistent assets
- Keep provider-specific request fields inside the provider adapter

