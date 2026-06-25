# Default target
default: build

# === Config-derived names (so the family name can change freely) ===
# The folder and file names follow the config's "Family Name" with spaces turned
# into hyphens, e.g. Family Name "Moxy Static" -> folder/slug "Moxy-Static".
CONFIG      := premade-configs/config.moxy.yaml
VF_CONFIG   := premade-configs/config.moxy-vf.yaml
SOURCE_VF   := $(firstword $(wildcard font-data/Recursive_VF_*.ttf))
FAMILY      := $(shell grep '^Family Name:' $(CONFIG) | sed 's/.*"\([^"]*\)".*/\1/')
FAMILY_SLUG := $(shell echo '$(FAMILY)' | tr ' ' '-')
FONT_DIR    := fonts/$(FAMILY_SLUG)
VF_OUT      := $(shell grep '^Output Path:' $(VF_CONFIG) | sed 's/.*"\([^"]*\)".*/\1/')

help:		## List all available commands with descriptions
	@awk -F'##' '/^[a-zA-Z0-9_-]+:.*##/ {gsub(/:.*/, ":\t\t", $$1); printf "%s%s\n", $$1, $$2}' $(MAKEFILE_LIST) | \
		awk 'NR%2==1 {print "\033[0m" $$0} NR%2==0 {print "\033[2m" $$0}'
	@echo "\033[0m"

# === Setup Targets ===

setup:	## Set up Python environment and install dependencies
	@echo "🐍 Setting Python version with pyenv..."
	@pyenv local 3.11.8
	@echo "📦 Creating virtual environment..."
	@python -m venv venv
	@echo "📥 Installing dependencies..."
	@venv/bin/pip install -r requirements.txt
	@echo "✅ Setup complete! Virtual environment ready."

# === Build Targets ===

build:	## Build and install the static code fonts on Mac
	@echo "❌ removing existing $(FAMILY_SLUG) fonts on Mac..."
	@rm -rf ~/Library/Fonts/$(FAMILY_SLUG)-* 2>/dev/null || true
	@echo "❌ removing existing fonts in project..."
	@rm -rf $(FONT_DIR) 2>/dev/null || true
	@echo "🔨 Building $(FAMILY) fonts..."
	@venv/bin/python scripts/instantiate-code-fonts.py $(CONFIG) $(SOURCE_VF)
	@echo "✅ Installing $(FAMILY) fonts on Mac..."
	@cp $(FONT_DIR)/*.ttf ~/Library/Fonts/

build-vf:	## Build the Moxy variable font (close to Recursive; moxy/lilx opt-in toggles)
	@echo "🔨 Building Moxy variable font..."
	@venv/bin/python scripts/build-variable-font.py $(VF_CONFIG) $(SOURCE_VF)
	@echo "✅ Saved to fonts/Moxy-VF/ — install manually to use the toggles"
	@echo "   ghostty: font-family = Moxy   (full Moxy: font-feature = moxy, lilx)"

install-vf:	## Build the Moxy variable font AND (re)install it to ~/Library/Fonts
	@echo "🔨 Building Moxy variable font..."
	@venv/bin/python scripts/build-variable-font.py $(VF_CONFIG) $(SOURCE_VF)
	@NAME=$$(basename "$(VF_OUT)"); \
		echo "❌ removing ALL previously installed Moxy VFs (any axis tag) ..."; \
		rm -f "$$HOME"/Library/Fonts/Moxy\[*\].ttf 2>/dev/null || true; \
		echo "✅ installing $$NAME to ~/Library/Fonts ..."; \
		cp "$(VF_OUT)" "$$HOME/Library/Fonts/$$NAME"
	@echo "   set font-family = Moxy in your terminal/editor, then reload it"

# === Branding ===

images-branding:	## Regenerate README images from images/branding/specimens.md (Cobalt2 theme)
	@echo "🖼  Rendering branding images from images/branding/specimens.md ..."
	@venv/bin/python -m pip install -q Pillow
	@venv/bin/python scripts/dev/render_specimens.py
	@echo "✅ Wrote README branding images (Cobalt2)"

# === Package Targets ===

package: build ## Package the static fonts + create GitHub release for homebrew
	@VERSION=$$(grep "Version:" premade-configs/config.moxy.yaml | sed 's/.*"\([^"]*\)".*/\1/') && \
	FONT_VERSION=$$(ls font-data/Recursive_VF_*.ttf | sed 's/.*_VF_\([0-9.]*\)\.ttf/\1/') && \
	echo "📦 Starting package process..." && \
	echo "📋 Version: $$VERSION, Font Version: $$FONT_VERSION" && \
	echo "📄 Bundling attribution (Lilex OFL + LICENSE)..." && \
	cp OFL.txt font-data/Lilex-OFL.txt LICENSE $(FONT_DIR)/ 2>/dev/null || true && \
	echo "🗜️  Creating zip file..." && \
	cd fonts && zip -r -X ../moxy-$$VERSION.zip $(FAMILY_SLUG)/ && cd .. && \
	echo "🔐 Calculating SHA256..." && \
	SHA=$$(shasum -a 256 moxy-$$VERSION.zip | awk '{print $$1}') && \
	echo "$$SHA" | pbcopy && \
	echo "   SHA256: $$SHA (copied to clipboard)" && \
	echo "📤 Committing and pushing changes to font-moxy..." && \
	git add -A && \
	(git commit -m "moxy $$VERSION" || true) && \
	(git push origin main || git push origin master) && \
	echo "🚀 Creating GitHub release..." && \
	gh release create v$$VERSION \
		--repo kaushikgopal/font-moxy \
		--title "Moxy $$VERSION" \
		--notes "Moxy $$VERSION" \
		moxy-$$VERSION.zip && \
	echo "🍺 Updating homebrew formula..." && \
	if [ ! -d "../homebrew-tools" ]; then \
		echo "   Cloning homebrew-tools repository..."; \
		cd .. && git clone https://github.com/kaushikgopal/homebrew-tools.git && cd font-moxy; \
	fi && \
	cd ../homebrew-tools && (git pull origin main || git pull origin master) && cd ../font-moxy && \
	echo "   Regenerating cask from the built fonts (family-name & style-count agnostic)..." && \
	{ \
		echo 'cask "font-moxy" do'; \
		echo "  version \"$$VERSION\""; \
		echo "  sha256 \"$$SHA\""; \
		echo "  url \"https://github.com/kaushikgopal/font-moxy/releases/download/v$$VERSION/moxy-$$VERSION.zip\""; \
		echo '  name "$(FAMILY)"'; \
		echo '  desc "Monospaced coding font built on Recursive, with glyphs borrowed from Lilex"'; \
		echo '  homepage "https://github.com/kaushikgopal/font-moxy"'; \
		for f in $(FONT_DIR)/*.ttf; do echo "  font \"$(FAMILY_SLUG)/$$(basename "$$f")\""; done; \
		echo 'end'; \
	} > ../homebrew-tools/Casks/font-moxy.rb && \
	echo "   Asserting cask was generated..." && \
	grep -q "$(FAMILY_SLUG)/$(FAMILY_SLUG)-Regular-$$FONT_VERSION.ttf" ../homebrew-tools/Casks/font-moxy.rb || { echo "❌ cask generation failed — no Regular font line"; exit 1; } && \
	echo "   Committing and pushing homebrew-tools..." && \
	cd ../homebrew-tools && git add Casks/font-moxy.rb && \
	git commit -m "update: moxy $$VERSION" && \
	(git push origin main || git push origin master) && \
	echo "✅ Package complete! Release v$$VERSION created and homebrew formula updated." && \
	echo "   Release URL: https://github.com/kaushikgopal/font-moxy/releases/tag/v$$VERSION"
