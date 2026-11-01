# Dependency lockfile status

Backend dependencies are exact-version pins in `backend/requirements.txt` and `backend/requirements-setup.txt`. This is not yet a fully hashed transitive lock. The temporary model-setup container separately obtains PyTorch from the official CPU wheel repository.

React dependencies are fixed in `frontend/package.json`, but **no `package-lock.json` can be generated and tested in this network-isolated artifact environment**. The Dockerfile and CI currently use `npm install`, not `npm ci`. On the first network-enabled runner:

```bash
cd frontend
npm install --package-lock-only
npm ci
npm run build
```

Commit the resulting package-lock.json, then replace Dockerfile and GitLab `npm install` calls with `npm ci`. Prefer internal approved npm mirrors and an image digest pin for later immutable releases.

The first `make model` resolves the HF source repository to a full immutable commit and records file SHA256 hashes. Copy immutable revisions into `.env` on server after initial model preparation. Future deployments should track original weight artifact hashes in release attestations as well.
