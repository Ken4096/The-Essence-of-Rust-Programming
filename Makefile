# 《从本质学 Rust 编程》的构建入口。

WEB_DIR   ?= web
SEO_FLAGS ?=
MSG       ?= 重新构建并更新 SEO 产物


ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif

SEO := $(PYTHON) tools/seo/postprocess.py --web-dir $(WEB_DIR) --git-lastmod

.PHONY: build verify push clean


build: clean
	mdbook build
	$(SEO) $(SEO_FLAGS)

verify:
	$(PYTHON) tools/seo/verify.py --web-dir $(WEB_DIR) --git-lastmod

push: build verify
	git add -A
	git diff --cached --quiet || git commit -m "$(MSG)"
	git push

clean:
	mdbook clean
