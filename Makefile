# Local Kubernetes deployment for the chatbot platform (kind + kustomize).
#
# Quick start:
#   make deploy-local      # bootstrap cluster, build+load images, deploy everything
#   echo "127.0.0.1 chatbot.local" | sudo tee -a /etc/hosts
#   open http://chatbot.local
#   make kind-down         # tear it all down

CLUSTER      ?= chatbot
NAMESPACE    ?= chatbot
KIND_CONFIG  ?= k8s/local/kind-config.yaml
INGRESS_HOST ?= chatbot.local
# Browser-reachable API base, baked into the frontend at build time (ingress host).
FRONTEND_API_URL ?= http://$(INGRESS_HOST)

# Logical image tags — must match the image: fields in k8s/*/deployment.yaml.
IMAGES = chatbot/api chatbot/ingestion chatbot/presidio chatbot/frontend

.PHONY: help deploy-local kind-up ingress-install images-build images-load \
        secrets deploy status logs kind-down

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

deploy-local: kind-up ingress-install images-build images-load secrets deploy ## Full local bring-up
	@echo "Deployed. Add '127.0.0.1 $(INGRESS_HOST)' to /etc/hosts, then open http://$(INGRESS_HOST)"

kind-up: ## Create the kind cluster (idempotent)
	@kind get clusters | grep -qx $(CLUSTER) || \
		kind create cluster --name $(CLUSTER) --config $(KIND_CONFIG)

ingress-install: ## Install nginx ingress controller and wait for it
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
	kubectl wait --namespace ingress-nginx \
		--for=condition=ready pod \
		--selector=app.kubernetes.io/component=controller \
		--timeout=180s

images-build: ## Build all four service images with the logical local tags
	docker build -t chatbot/api:latest        -f services/api/Dockerfile .
	docker build -t chatbot/ingestion:latest  -f services/ingestion/Dockerfile .
	docker build -t chatbot/presidio:latest   services/presidio
	docker build -t chatbot/frontend:latest   --build-arg NEXT_PUBLIC_API_URL=$(FRONTEND_API_URL) frontend

images-load: ## Load built images into the kind cluster (no registry needed)
	$(foreach img,$(IMAGES),kind load docker-image $(img):latest --name $(CLUSTER);)

secrets: ## Create k8s/secrets/*.env from examples if missing
	@for f in postgres llm-api-keys; do \
		if [ ! -f k8s/secrets/$$f.env ]; then \
			cp k8s/secrets/$$f.env.example k8s/secrets/$$f.env; \
			echo "Created k8s/secrets/$$f.env — fill in real values before deploy."; \
		fi; \
	done

deploy: ## Apply all manifests via kustomize
	kubectl apply -k k8s/

status: ## Show workloads in the chatbot namespace
	kubectl -n $(NAMESPACE) get pods,svc,ingress

logs: ## Tail API + ingestion logs
	kubectl -n $(NAMESPACE) logs -l app=api --tail=50 -f & \
	kubectl -n $(NAMESPACE) logs -l app=ingestion --tail=50 -f

kind-down: ## Delete the kind cluster
	kind delete cluster --name $(CLUSTER)
