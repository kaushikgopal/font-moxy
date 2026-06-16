# Default target
default: build

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

build:	## Build and install Moxy (static) code fonts on Mac
	@echo "❌ removing existing Moxy fonts on Mac..."
	@rm -rf ~/Library/Fonts/Moxy-* 2>/dev/null || true
	@echo "❌ removing existing Moxy fonts in project..."
	@rm -rf fonts/Moxy-Static* 2>/dev/null || true
	@echo "🔨 Building Moxy fonts..."
	@venv/bin/python scripts/instantiate-code-fonts.py premade-configs/config.moxy.yaml font-data/Recursive_VF_1.085.ttf
	@echo "✅ Installing Moxy fonts on Mac..."
	@cp fonts/Moxy-Static/*.ttf ~/Library/Fonts/

build-vf:	## Build the Moxy variable font (canonical; carries the lilx/ss13 revert toggles)
	@echo "🔨 Building Moxy variable font..."
	@venv/bin/python scripts/build-variable-font.py
	@echo "✅ Saved to fonts/Moxy-VF/ — install manually to use the toggles"
	@echo "   ghostty: font-family = Moxy   (pristine Recursive: font-feature = lilx, ss13)"

# === Package Targets ===

package: build ## Package the static fonts + create GitHub release for homebrew
	@VERSION=$$(grep "Version:" premade-configs/config.moxy.yaml | sed 's/.*"\([^"]*\)".*/\1/') && \
	FONT_VERSION=$$(ls font-data/Recursive_VF_*.ttf | sed 's/.*_VF_\([0-9.]*\)\.ttf/\1/') && \
	echo "📦 Starting package process..." && \
	echo "📋 Version: $$VERSION, Font Version: $$FONT_VERSION" && \
	echo "📄 Bundling attribution (Lilex OFL + LICENSE)..." && \
	cp OFL.txt font-data/Lilex-OFL.txt LICENSE fonts/Moxy-Static/ 2>/dev/null || true && \
	echo "🗜️  Creating zip file..." && \
	cd fonts && zip -r -X ../moxy-$$VERSION.zip Moxy-Static/ && cd .. && \
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
	echo "   Updating version, sha256, and url..." && \
	sed -i '' "s/version \".*\"/version \"$$VERSION\"/" ../homebrew-tools/Casks/font-moxy.rb && \
	sed -i '' "s/sha256 \".*\"/sha256 \"$$SHA\"/" ../homebrew-tools/Casks/font-moxy.rb && \
	sed -i '' "s|url \".*\"|url \"https://github.com/kaushikgopal/font-moxy/releases/download/v$$VERSION/moxy-$$VERSION.zip\"|" ../homebrew-tools/Casks/font-moxy.rb && \
	echo "   Updating font paths..." && \
	sed -i '' "s|font \"[^\"]*/Moxy-\([A-Za-z]*\)-[0-9.]*\.ttf\"|font \"Moxy-Static/Moxy-\1-$$FONT_VERSION.ttf\"|g" ../homebrew-tools/Casks/font-moxy.rb && \
	echo "   Asserting cask was updated..." && \
	grep -q "Moxy-Static/Moxy-Regular-$$FONT_VERSION.ttf" ../homebrew-tools/Casks/font-moxy.rb || { echo "❌ cask font paths did not update — check the sed pattern"; exit 1; } && \
	echo "   Committing and pushing homebrew-tools..." && \
	cd ../homebrew-tools && git add Casks/font-moxy.rb && \
	git commit -m "update: moxy $$VERSION" && \
	(git push origin main || git push origin master) && \
	echo "✅ Package complete! Release v$$VERSION created and homebrew formula updated." && \
	echo "   Release URL: https://github.com/kaushikgopal/font-moxy/releases/tag/v$$VERSION"
